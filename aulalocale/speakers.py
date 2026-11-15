"""Persistent speaker jobs and version-checked manual speaker labels."""
from contextlib import closing
from pathlib import Path
from threading import RLock
from uuid import UUID,uuid4
import json
import sys
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
import imageio_ffmpeg


class SpeakerInput(BaseModel):
    num_speakers:int=Field(default=0,ge=0,le=12)


class SpeakerEdit(BaseModel):
    base_version:int=Field(ge=0)
    labels:dict[str,str]
    assignments:dict[str,str]=Field(default_factory=dict)


def dominant_speaker(start,end,segments):
    overlap={}
    for part in segments:
        amount=max(0,min(end,part['end'])-max(start,part['start']))
        overlap[part['speaker']]=overlap.get(part['speaker'],0)+amount
    active=[(value,key) for key,value in overlap.items() if value>0];active.sort(reverse=True)
    if not active or active[0][0]<max(.01,end-start)*.2:return None
    if len(active)>1 and active[1][0]>=active[0][0]*.6:return 'overlap'
    return active[0][1]


class SpeakerService:
    def __init__(self,root,connect,worker,models):self.root,self.connect,self.worker,self.models=root,connect,worker,models;self.lock=RLock()
    def result(self,identifier):
        directory=self.root/'speakers';original=directory/(str(identifier)+'.json');edits=directory/(str(identifier)+'.edits.json')
        if not original.is_file():return None
        record=json.loads(original.read_text())
        if edits.is_file():
            manual=json.loads(edits.read_text());record['labels']=manual['labels'];record['version']=manual['version']
            for segment in record['segments']:segment['speaker']=manual['assignments'].get(segment['id'],segment['speaker'])
        return {**record,'job_id':str(identifier)}
    def latest(self,lesson_id):
        with closing(self.connect()) as c:row=c.execute("SELECT id FROM study_jobs WHERE lesson_id=? AND kind='speakers' AND status='completed' ORDER BY created_at DESC,id DESC LIMIT 1",(str(lesson_id),)).fetchone()
        record=self.result(row['id']) if row else None
        if record:
            from .study import latest_transcript
            with closing(self.connect()) as c:transcript=latest_transcript(c,lesson_id)
            if transcript:
                record['transcript_revision_id']=transcript['id']
                record['transcript_speakers']={s['id']:dominant_speaker(s['start'],s['end'],record['segments']) for s in transcript['segments']}
        return record
    def execute(self,job,temp,engine):
        self.models.require('speaker-segmentation');self.models.require('speaker-embedding')
        with closing(self.connect()) as c:lesson=c.execute('SELECT * FROM lessons WHERE id=?',(job['lesson_id'],)).fetchone()
        source=self.root/'originals'/lesson['storage_name'];wav=temp/'speakers.wav';output=temp/'speakers.json';progress=temp/'progress.txt'
        engine.process([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-nostdin','-i',str(source),'-ac','1','-ar','16000','-c:a','pcm_s16le',str(wav)],job['id'])
        command=[sys.executable,'--internal-speakers'] if getattr(sys,'frozen',False) else [sys.executable,'-m','aulalocale.ai_speakers']
        command+=['--input',str(wav),'--output',str(output),'--segmentation',str(self.models.require('speaker-segmentation')),'--embedding',str(self.models.require('speaker-embedding')),'--num-speakers',str(json.loads(job['payload'])['num_speakers']),'--progress',str(progress)]
        engine.process(command,job['id'],progress_path=progress)
        data=json.loads(output.read_text())
        if not data['segments']:raise ValueError('Nessun parlato distinguibile. Controlla la registrazione.')
        data.update({'lesson_id':job['lesson_id'],'models':['speaker-segmentation','speaker-embedding'],'source':'original'})
        directory=self.root/'speakers';directory.mkdir(exist_ok=True)
        with self.worker.lock:
            if engine.cancelled(job['id']):raise InterruptedError()
            partial=directory/(job['id']+'.json.part');partial.write_text(json.dumps(data));partial.replace(directory/(job['id']+'.json'))


def speakers_router(service,engine,authenticate):
    from .study import timestamp
    router=APIRouter(prefix='/api/v1',dependencies=[Depends(authenticate)])
    @router.get('/lessons/{lesson_id}/speakers')
    def get(lesson_id:UUID):return service.latest(lesson_id)
    @router.post('/lessons/{lesson_id}/speakers',status_code=202)
    def start(lesson_id:UUID,options:SpeakerInput):
        with service.lock,service.worker.lock:
            current=service.latest(lesson_id)
            if current and current['version']:raise HTTPException(409,'L’analisi contiene correzioni manuali e resta protetta')
            service.models.require('speaker-segmentation');service.models.require('speaker-embedding')
            with closing(service.connect()) as c,c:
                lesson=c.execute('SELECT * FROM lessons WHERE id=?',(str(lesson_id),)).fetchone()
                if not lesson:raise HTTPException(404,'Lezione non trovata')
                existing=c.execute("SELECT id FROM study_jobs WHERE lesson_id=? AND kind='speakers' AND status IN ('queued','running')",(str(lesson_id),)).fetchone()
                if existing:return engine.get(existing['id'])
                identifier=str(uuid4());now=timestamp()
                c.execute("INSERT INTO study_jobs VALUES (?,?,?,?,?,0,NULL,?,?,?)",(identifier,'speakers',str(lesson_id),lesson['subject_id'],'queued',json.dumps(options.model_dump()),now,now))
            service.worker.wake.set();return engine.get(identifier)
    @router.put('/lessons/{lesson_id}/speakers')
    def edit(lesson_id:UUID,options:SpeakerEdit):
        with service.lock,service.worker.lock:
            current=service.latest(lesson_id)
            if not current:raise HTTPException(404,'Analisi non disponibile')
            with closing(service.connect()) as c:
                if c.execute("SELECT 1 FROM study_jobs WHERE lesson_id=? AND kind='speakers' AND status IN ('queued','running')",(str(lesson_id),)).fetchone():raise HTTPException(409,'Attendi la fine dell’analisi prima di correggere i parlanti')
            if current['version']!=options.base_version:raise HTTPException(409,'L’analisi è cambiata: ricarica prima di salvare')
            if set(options.labels)!=set(current['labels']) or any(not v.strip() or len(v)>80 for v in options.labels.values()):raise HTTPException(422,'Nomi dei parlanti non validi')
            valid={s['id'] for s in current['segments']}
            if not set(options.assignments).issubset(valid) or any(v not in current['labels'] for v in options.assignments.values()):raise HTTPException(422,'Assegnazioni dei parlanti non valide')
            directory=service.root/'speakers';path=directory/(current['job_id']+'.edits.json')
            previous=json.loads(path.read_text()) if path.exists() else {'assignments':{}}
            data={'version':current['version']+1,'labels':{k:v.strip() for k,v in options.labels.items()},'assignments':{**previous['assignments'],**options.assignments}}
            partial=path.with_suffix('.part');partial.write_text(json.dumps(data));partial.replace(path)
            return service.result(current['job_id'])
    return router

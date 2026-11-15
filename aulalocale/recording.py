"""Crash-recoverable PCM microphone drafts, sent only by explicit client recording."""
from contextlib import closing
from datetime import date,datetime,timezone
from io import BytesIO
from pathlib import Path
from threading import RLock
from uuid import UUID,uuid4
import hashlib
import json
import os
import wave
from fastapi import APIRouter,Body,Depends,HTTPException
from pydantic import BaseModel,Field,field_validator
from starlette.datastructures import UploadFile
from .lessons import store_lesson,MAX_UPLOAD_BYTES


class RecordingInput(BaseModel):
    subject_id:UUID
    title:str=Field(min_length=1,max_length=200)
    teacher:str=Field(default='',max_length=200)
    lecture_date:date | None=None
    @field_validator('title')
    @classmethod
    def strip(cls,value):
        if not value.strip():raise ValueError('Titolo mancante')
        return value.strip()


def recording_router(root,connect,authenticate):
    router=APIRouter(prefix='/api/v1/recordings',dependencies=[Depends(authenticate)])
    directory=root/'recordings';lock=RLock()
    def paths(identifier):return directory/(str(identifier)+'.json'),directory/(str(identifier)+'.pcm')
    def save(info):
        metadata,_=paths(info['id']);temporary=metadata.with_suffix('.json.part')
        temporary.write_text(json.dumps(info));temporary.replace(metadata)
    def read(identifier):
        metadata,pcm=paths(identifier)
        if not metadata.is_file():raise HTTPException(404,'Registrazione non trovata')
        info=json.loads(metadata.read_text())
        if not info.get('lesson_id') and pcm.is_file() and pcm.stat().st_size>info['bytes']:
            # Recover a last append completed before the metadata rename.
            with pcm.open('rb') as f:f.seek(info['bytes']);tail=f.read()
            if len(tail)%2 or len(tail)>128000:raise HTTPException(409,'Bozza audio incoerente: conservata per il recupero manuale')
            info.update(bytes=pcm.stat().st_size,last_sequence=info['last_sequence']+1,last_sha256=hashlib.sha256(tail).hexdigest());save(info)
        return info
    def public(info):return {**info,'duration_seconds':info['bytes']/32000,'sample_rate':16000,'channels':1}
    @router.get('')
    def list_recordings():
        with lock:
            return [public(read(p.stem)) for p in sorted(directory.glob('*.json')) if not json.loads(p.read_text()).get('lesson_id')]
    @router.post('',status_code=201)
    def start(options:RecordingInput):
        with lock:
            with closing(connect()) as c:
                if not c.execute('SELECT 1 FROM subjects WHERE id=?',(str(options.subject_id),)).fetchone():raise HTTPException(404,'Materia non trovata')
            if list_recordings():raise HTTPException(409,'Salva prima la registrazione rimasta in sospeso')
            directory.mkdir(exist_ok=True)
            info={**options.model_dump(mode='json'),'id':str(uuid4()),'bytes':0,'last_sequence':-1,'last_sha256':None,'lesson_id':None,'created_at':datetime.now(timezone.utc).isoformat()}
            _,pcm=paths(info['id']);pcm.touch(exist_ok=False);save(info);return public(info)
    @router.post('/{identifier}/chunks')
    def append(identifier:UUID,sequence:int,body:bytes=Body(media_type='application/octet-stream',max_length=128000)):
        if not body or len(body)%2 or sequence<0:raise HTTPException(422,'Blocco PCM non valido')
        with lock:
            info=read(identifier)
            if info.get('lesson_id'):raise HTTPException(409,'Registrazione già salvata')
            digest=hashlib.sha256(body).hexdigest()
            if sequence==info['last_sequence'] and digest==info['last_sha256']:return public(info)
            if sequence!=info['last_sequence']+1:raise HTTPException(409,'Sequenza dei blocchi non valida')
            if info['bytes']+len(body)+44>MAX_UPLOAD_BYTES:raise HTTPException(413,'Limite di registrazione raggiunto: salva la lezione')
            _,pcm=paths(identifier)
            with pcm.open('ab') as target:target.write(body);target.flush();os.fsync(target.fileno())
            info.update(bytes=info['bytes']+len(body),last_sequence=sequence,last_sha256=digest);save(info);return public(info)
    @router.delete('/{identifier}',status_code=204)
    def close_empty(identifier:UUID):
        with lock:
            info=read(identifier)
            if info['bytes'] or info.get('lesson_id'):raise HTTPException(409,'Una registrazione con audio deve essere salvata, non cancellata')
            metadata,pcm=paths(identifier);metadata.unlink();pcm.unlink(missing_ok=True)
    @router.post('/{identifier}/finish')
    def finish(identifier:UUID):
        with lock:
            info=read(identifier)
            if info.get('lesson_id'):
                with closing(connect()) as c:return dict(c.execute('SELECT * FROM lessons WHERE id=?',(info['lesson_id'],)).fetchone())
            if not info['bytes']:raise HTTPException(409,'La registrazione non contiene ancora audio')
            _,pcm=paths(identifier);wav=directory/(str(identifier)+'.wav.part')
            try:
                with wave.open(str(wav),'wb') as target,pcm.open('rb') as source:
                    target.setparams((1,2,16000,0,'NONE','not compressed'))
                    for data in iter(lambda:source.read(1024*1024),b''):target.writeframesraw(data)
                with wav.open('rb') as source:
                    upload=UploadFile(source,filename='Registrazione-'+info['created_at'][:10]+'.wav',size=wav.stat().st_size)
                    try:lesson=store_lesson(root,connect,info['subject_id'],upload,info['title'],info['teacher'],date.fromisoformat(info['lecture_date']) if info['lecture_date'] else None)
                    except HTTPException as e:
                        if e.status_code!=409 or not isinstance(e.detail,dict) or 'lesson_id' not in e.detail:raise
                        with closing(connect()) as c:lesson=dict(c.execute('SELECT * FROM lessons WHERE id=? AND subject_id=?',(e.detail['lesson_id'],info['subject_id'])).fetchone())
                info['lesson_id']=str(lesson['id']);save(info);pcm.unlink(missing_ok=True);return lesson
            finally:wav.unlink(missing_ok=True)
    return router

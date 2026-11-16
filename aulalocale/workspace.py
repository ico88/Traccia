"""Archive-scoped study workspace extensions; no cloud or separate user identity."""
from contextlib import closing
from datetime import datetime,timezone
from typing import Literal
from uuid import UUID,uuid4
import json,re,sqlite3
from fastapi import APIRouter,Depends,HTTPException,Query
from pydantic import BaseModel,ConfigDict,Field
from .study import latest_transcript,latest_notes,timestamp
from .models import runtime_path


def migrate_workspace(c):
    c.execute('CREATE TABLE IF NOT EXISTS archive_identity(id TEXT PRIMARY KEY,singleton INTEGER NOT NULL UNIQUE CHECK(singleton=1))')
    if not c.execute('SELECT 1 FROM archive_identity').fetchone():c.execute('INSERT INTO archive_identity VALUES (?,1)',(str(uuid4()),))
    c.execute('''CREATE TABLE IF NOT EXISTS note_templates(id TEXT PRIMARY KEY,archive_id TEXT NOT NULL REFERENCES archive_identity(id) ON DELETE RESTRICT,
      name TEXT NOT NULL,prompt TEXT NOT NULL,revision INTEGER NOT NULL CHECK(revision>0),created_at TEXT NOT NULL,updated_at TEXT NOT NULL,UNIQUE(archive_id,name))''')
    c.execute('''CREATE TABLE IF NOT EXISTS subject_preferences(id TEXT PRIMARY KEY,archive_id TEXT NOT NULL REFERENCES archive_identity(id) ON DELETE RESTRICT,
      subject_id TEXT NOT NULL UNIQUE REFERENCES subjects(id) ON DELETE RESTRICT,settings TEXT NOT NULL CHECK(json_valid(settings)),revision INTEGER NOT NULL CHECK(revision>0),created_at TEXT NOT NULL,updated_at TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS lecture_annotations(id TEXT PRIMARY KEY,archive_id TEXT NOT NULL REFERENCES archive_identity(id) ON DELETE RESTRICT,
      lesson_id TEXT NOT NULL REFERENCES lessons(id) ON DELETE RESTRICT,kind TEXT NOT NULL CHECK(kind IN ('highlight','text','image')),
      start REAL NOT NULL CHECK(start>=0),body TEXT NOT NULL,material_id TEXT REFERENCES materials(id) ON DELETE RESTRICT,
      revision INTEGER NOT NULL CHECK(revision>0),created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
      CHECK((kind='image' AND material_id IS NOT NULL) OR (kind!='image' AND material_id IS NULL)))''')
    for name,col in [('note_templates','archive_id'),('subject_preferences','archive_id'),('lecture_annotations','archive_id'),('lecture_annotations','material_id')]:c.execute(f'CREATE INDEX IF NOT EXISTS workspace_{name}_{col} ON {name}({col})')
    c.execute('CREATE INDEX IF NOT EXISTS workspace_annotations_time ON lecture_annotations(lesson_id,start,id)')
    c.execute('CREATE INDEX IF NOT EXISTS workspace_templates_name ON note_templates(archive_id,name)')

class Strict(BaseModel):model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
class Settings(Strict):
    language:Literal['it','en','auto']='it'
    summary_language:Literal['it','en']='en'
    template_id:UUID|None=None
    glossary:list[str]=Field(default_factory=list,max_length=100)
class Preferences(Strict):
    base_revision:int=Field(ge=0)
    settings:Settings
class TemplateInput(Strict):
    name:str=Field(min_length=1,max_length=120)
    prompt:str=Field(min_length=1,max_length=4000)
    base_revision:int|None=Field(default=None,ge=1)
class Annotation(Strict):
    id:UUID=Field(default_factory=uuid4)
    kind:Literal['highlight','text','image']='text'
    start:float=Field(ge=0)
    body:str=Field(default='',max_length=12000)
    material_id:UUID|None=None
class PipelineInput(Strict):
    language:Literal['it','en','auto']='it'
    summary_language:Literal['it','en']='en'
    base_revision:UUID|None=None
    request_id:UUID=Field(default_factory=uuid4)

DEFAULT_TEMPLATES=[('Lecture essentials','Organizza in definizioni, esempi presenti nella fonte e punti da rivedere.'),('Concept comparison','Confronta soltanto concetti esplicitamente presenti nelle fonti, segnalando differenze e limiti.'),('Exam review','Evidenzia definizioni e collegamenti espliciti utili al ripasso; non inventare domande o risposte mancanti.')]
def preferences(c,sid):
    row=c.execute('SELECT * FROM subject_preferences WHERE subject_id=?',(str(sid),)).fetchone()
    return {'revision':row['revision'] if row else 0,'settings':json.loads(row['settings']) if row else Settings().model_dump(mode='json')}
def template_snapshot(c,identifier):
    if not identifier:return None
    row=c.execute('SELECT id,name,prompt,revision FROM note_templates WHERE id=?',(str(identifier),)).fetchone()
    if not row:raise HTTPException(409,'Selected template is unavailable')
    return dict(row)
def seed_templates(c):
    aid=c.execute('SELECT id FROM archive_identity').fetchone()[0]
    # Seed once only when the archive has never initialized built-in templates.
    if c.execute("SELECT 1 FROM note_templates WHERE name IN ('Lecture essentials','Concept comparison','Exam review')").fetchone():return
    if c.execute('SELECT 1 FROM note_templates').fetchone():return
    for name,prompt in DEFAULT_TEMPLATES:c.execute('INSERT INTO note_templates VALUES (?,?,?,?,1,?,?)',(str(uuid4()),aid,name,prompt,timestamp(),timestamp()))

def workspace_router(engine,authenticate):
    cfn=engine.connect;router=APIRouter(prefix='/api/v1',dependencies=[Depends(authenticate)])
    def owner(c):return c.execute('SELECT id FROM archive_identity WHERE singleton=1').fetchone()[0]
    def subject(c,sid):
        if not c.execute('SELECT 1 FROM subjects WHERE id=?',(str(sid),)).fetchone():raise HTTPException(404,'Subject not found')
    def lesson(c,lid):
        row=c.execute('SELECT * FROM lessons WHERE id=?',(str(lid),)).fetchone()
        if not row:raise HTTPException(404,'Lesson not found')
        return row
    @router.get('/subjects/{subject_id}/preferences')
    def get_preferences(subject_id:UUID):
        with closing(cfn()) as c:subject(c,subject_id);return preferences(c,subject_id)
    @router.put('/subjects/{subject_id}/preferences')
    def put_preferences(subject_id:UUID,options:Preferences):
        if any(not term.strip() or len(term)>100 for term in options.settings.glossary):raise HTTPException(422,'Glossary terms must contain 1–100 characters')
        with engine.worker.lock,closing(cfn()) as c,c:
            subject(c,subject_id);old=preferences(c,subject_id)
            if options.base_revision!=old['revision']:raise HTTPException(409,'Settings changed; reload before saving')
            template_snapshot(c,options.settings.template_id)
            settings=options.settings.model_dump(mode='json');settings['glossary']=list(dict.fromkeys(x.strip() for x in settings['glossary']))
            if old['revision']:c.execute('UPDATE subject_preferences SET settings=?,revision=revision+1,updated_at=? WHERE subject_id=?',(json.dumps(settings),timestamp(),str(subject_id)))
            else:c.execute('INSERT INTO subject_preferences VALUES (?,?,?,?,1,?,?)',(str(uuid4()),owner(c),str(subject_id),json.dumps(settings),timestamp(),timestamp()))
            return preferences(c,subject_id)
    @router.get('/templates')
    def templates():
        with closing(cfn()) as c:return [dict(r) for r in c.execute('SELECT id,name,prompt,revision FROM note_templates ORDER BY name,id')]
    @router.post('/templates',status_code=201)
    def create_template(options:TemplateInput):
        if not options.name.strip() or not options.prompt.strip():raise HTTPException(422,'Name and prompt cannot be blank')
        with engine.worker.lock,closing(cfn()) as c,c:
            identifier=str(uuid4())
            try:c.execute('INSERT INTO note_templates VALUES (?,?,?,?,1,?,?)',(identifier,owner(c),options.name.strip(),options.prompt.strip(),timestamp(),timestamp()))
            except sqlite3.IntegrityError:raise HTTPException(409,'A template with this name already exists')
            return dict(c.execute('SELECT id,name,prompt,revision FROM note_templates WHERE id=?',(identifier,)).fetchone())
    @router.put('/templates/{identifier}')
    def edit_template(identifier:UUID,options:TemplateInput):
        if not options.name.strip() or not options.prompt.strip():raise HTTPException(422,'Name and prompt cannot be blank')
        with engine.worker.lock,closing(cfn()) as c,c:
            old=c.execute('SELECT * FROM note_templates WHERE id=?',(str(identifier),)).fetchone()
            if not old:raise HTTPException(404,'Template not found')
            if options.base_revision!=old['revision']:raise HTTPException(409,'Template changed; reload before saving')
            try:c.execute('UPDATE note_templates SET name=?,prompt=?,revision=revision+1,updated_at=? WHERE id=?',(options.name.strip(),options.prompt.strip(),timestamp(),str(identifier)))
            except sqlite3.IntegrityError:raise HTTPException(409,'A template with this name already exists')
            return dict(c.execute('SELECT id,name,prompt,revision FROM note_templates WHERE id=?',(str(identifier),)).fetchone())
    @router.get('/lessons/{lesson_id}/annotations')
    def annotations(lesson_id:UUID):
        with closing(cfn()) as c:lesson(c,lesson_id);return [dict(r) for r in c.execute('SELECT * FROM lecture_annotations WHERE lesson_id=? ORDER BY start,id',(str(lesson_id),))]
    @router.post('/lessons/{lesson_id}/annotations',status_code=201)
    def add_annotation(lesson_id:UUID,options:Annotation):
        if options.kind=='text' and not options.body.strip():raise HTTPException(422,'Write a note first')
        if (options.kind=='image')!=(options.material_id is not None):raise HTTPException(422,'Only image annotations require a material')
        with engine.worker.lock,closing(cfn()) as c,c:
            audio=lesson(c,lesson_id)
            if options.start>audio['duration_seconds']:raise HTTPException(422,'Timestamp is outside the lecture')
            if options.material_id and not c.execute('SELECT 1 FROM materials WHERE id=? AND subject_id=?',(str(options.material_id),audio['subject_id'])).fetchone():raise HTTPException(404,'Image not found in this subject')
            old=c.execute('SELECT * FROM lecture_annotations WHERE id=?',(str(options.id),)).fetchone()
            fields=(str(lesson_id),options.kind,options.start,options.body,str(options.material_id) if options.material_id else None)
            if old:
                if tuple(old[k] for k in ['lesson_id','kind','start','body','material_id'])!=fields:raise HTTPException(409,'Annotation request identifier already used')
                return dict(old)
            c.execute('INSERT INTO lecture_annotations VALUES (?,?,?,?,?,?,?,1,?,?)',(str(options.id),owner(c),*fields,timestamp(),timestamp()))
            return dict(c.execute('SELECT * FROM lecture_annotations WHERE id=?',(str(options.id),)).fetchone())
    @router.get('/subjects/{subject_id}/search')
    def search(subject_id:UUID,q:str=Query(min_length=2,max_length=200),lesson_id:UUID|None=None,limit:int=Query(20,ge=1,le=50),offset:int=Query(0,ge=0)):
        with closing(cfn()) as c:
            subject(c,subject_id)
            if lesson_id and lesson(c,lesson_id)['subject_id']!=str(subject_id):raise HTTPException(404,'Lesson not in this subject')
            tokens=set(re.findall(r'\w+',q.casefold()));matches=[]
            for row in c.execute('SELECT id,title FROM lessons WHERE subject_id=? ORDER BY created_at,id',(str(subject_id),)):
                if lesson_id and row['id']!=str(lesson_id):continue
                transcript=latest_transcript(c,row['id'])
                if not transcript:continue
                for s in transcript['segments']:
                    score=sum(token in s['text'].casefold() for token in tokens)
                    if score:matches.append({'lesson_id':row['id'],'lesson_title':row['title'],'revision_id':transcript['id'],'segment_id':s['id'],'start':s['start'],'end':s['end'],'text':s['text'],'score':score})
            matches.sort(key=lambda r:(-r['score'],r['lesson_id'],r['start']));return {'total':len(matches),'items':matches[offset:offset+limit],'method':'literal-token search; no AI answer'}
    @router.post('/lessons/{lesson_id}/processing-runs',status_code=202)
    def pipeline(lesson_id:UUID,options:PipelineInput):
        engine.models.require('whisper-turbo');engine.models.require('qwen3-4b')
        if not runtime_path('whisper-cli') or not runtime_path('llama-cli'):raise HTTPException(409,'Install local transcription and notes runtimes first')
        with engine.worker.lock,closing(cfn()) as c,c:
            audio=lesson(c,lesson_id);payload=options.model_dump(mode='json');old=latest_transcript(c,lesson_id)
            # The request UUID is the job ID: exact retries survive restart and do not create effects twice.
            existing=c.execute('SELECT * FROM study_jobs WHERE id=?',(str(options.request_id),)).fetchone()
            if existing:
                previous=json.loads(existing['payload'])
                if existing['lesson_id']!=str(lesson_id) or existing['kind']!='pipeline' or previous['request']!=payload:raise HTTPException(409,'Request identifier already used')
                return engine.get(existing['id'])
            if old and (old['metadata'].get('manual') or old['id']!=payload['base_revision']):raise HTTPException(409,'Transcript changed or has protected manual corrections')
            if not old and payload['base_revision']:raise HTTPException(409,'Transcript revision unavailable')
            if c.execute("SELECT 1 FROM study_jobs WHERE subject_id=? AND status IN ('queued','running','interrupted')",(audio['subject_id'],)).fetchone():raise HTTPException(409,'Wait for the current subject job before starting a complete workflow')
            settings=preferences(c,audio['subject_id'])['settings'];template=template_snapshot(c,settings.get('template_id'))
            data={'request':payload,'stage':'transcription','template':template,'glossary':settings['glossary']}
            c.execute('INSERT INTO study_jobs VALUES (?,?,?,?,?,0,NULL,?,?,?)',(str(options.request_id),'pipeline',str(lesson_id),audio['subject_id'],'queued',json.dumps(data),timestamp(),timestamp()))
        engine.worker.wake.set();return engine.get(str(options.request_id))
    return router

def execute_pipeline(engine,job,temp):
    payload=json.loads(job['payload']);options=payload['request'];identifier=job['id']
    with closing(engine.connect()) as c:
        transcript=latest_transcript(c,job['lesson_id'])
        completed_note=any(any(ch.get('generation',{}).get('pipeline_job')==identifier for ch in json.loads(row['chapters'])) for row in c.execute('SELECT chapters FROM notes WHERE subject_id=?',(job['subject_id'],)))
    if completed_note:return
    if not transcript or transcript['metadata'].get('pipeline_job')!=identifier:
        engine.transcribe({**job,'payload':json.dumps({'language':options['language'],'base_revision':options['base_revision'],'pipeline_job':identifier,'glossary':payload.get('glossary',[])})},temp)
    if engine.cancelled(identifier):raise InterruptedError()
    with engine.worker.lock,closing(engine.connect()) as c,c:
        payload['stage']='notes';c.execute('UPDATE study_jobs SET payload=?,status=\'running\',progress=0 WHERE id=? AND status!=\'cancelled\'',(json.dumps(payload),identifier))
        transcripts=[t for row in c.execute('SELECT id FROM lessons WHERE subject_id=? ORDER BY created_at,id',(job['subject_id'],)) if (t:=latest_transcript(c,row['id']))]
        previous=latest_notes(c,job['subject_id'])
    engine.generate_notes({**job,'payload':json.dumps({'base_revision':previous['id'] if previous else None,'transcripts':transcripts,'language':options['summary_language'],'template':payload.get('template'),'pipeline_job':identifier})},temp)

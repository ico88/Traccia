from contextlib import closing
from pathlib import Path
import io
import json
import sqlite3
import sys
import time
import wave
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from aulalocale.app import create_app
from aulalocale.models import ModelManager
from aulalocale.study import StudyEngine
import aulalocale.study as study

TOKEN='study-test-token-'*3
AUTH={'Authorization':f'Bearer {TOKEN}'}


def wait(client,identifier):
    deadline=time.monotonic()+5
    while time.monotonic()<deadline:
        job=client.get('/api/v1/study-jobs/'+identifier,headers=AUTH).json()
        if job['status'] not in ('queued','running'):return job
        time.sleep(.01)
    pytest.fail('Study job did not finish')


def seeded(tmp_path):
    sid,lid,rid,seg=map(str,[uuid4(),uuid4(),uuid4(),uuid4()])
    with TestClient(create_app(tmp_path,TOKEN)):pass
    segment={'id':seg,'start':0,'end':1,'text':'Il recettore lega il farmaco.'}
    with sqlite3.connect(tmp_path/'aulalocale.sqlite3') as c:
        c.execute('INSERT INTO subjects VALUES (?,?,?,?)',(sid,'Materia','','2026-01-01'))
        c.execute('INSERT INTO lessons VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(lid,sid,'Lezione','',None,'x.wav','test',100,1,16000,1,'audio/wav','2026-01-01','x.wav'))
        c.execute('INSERT INTO transcripts VALUES (?,?,?,?,?,?)',(rid,lid,1,json.dumps([segment]),json.dumps({'manual':False}),'2026-01-01'))
    return sid,lid,rid,segment


def test_transcript_revisions_and_conflicts(tmp_path):
    sid,lid,rid,segment=seeded(tmp_path)
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        route=f'/api/v1/lessons/{lid}/transcript'
        assert client.get(route).status_code==401
        payload={'base_revision':rid,'segments':[{'id':segment['id'],'text':'Testo corretto'}]}
        response=client.put(route,headers=AUTH,json=payload)
        assert response.status_code==200
        current=response.json()
        assert current['revision']==2 and current['id']!=rid
        assert current['segments'][0]['start']==0
        assert current['segments'][0]['text']=='Testo corretto'
        assert client.put(route,headers=AUTH,json=payload).status_code==409
        payload['base_revision']=current['id'];payload['segments']=[]
        assert client.put(route,headers=AUTH,json=payload).status_code==422
        assert client.post(f'/api/v1/lessons/{lid}/transcribe',headers=AUTH,json={}).status_code==409
    with sqlite3.connect(tmp_path/'aulalocale.sqlite3') as c:
        assert c.execute('SELECT count(*) FROM transcripts').fetchone()[0]==2


def enable_fake_llm(monkeypatch,tmp_path,invalid=False):
    monkeypatch.setattr(ModelManager,'require',lambda self,key:tmp_path/'model')
    monkeypatch.setattr(study,'runtime_path',lambda name:sys.executable)
    monkeypatch.setattr(StudyEngine,'llm',lambda self,prompt,temp,identifier,citation_count=None:{'chapters':[{'title':'Recettori','text':'Sintesi basata sulla lezione.','citations':[900 if invalid else 1]}]})


def test_notes_proposal_accept_edit_incremental_and_export(tmp_path,monkeypatch):
    sid,lid,rid,segment=seeded(tmp_path);enable_fake_llm(monkeypatch,tmp_path)
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        route=f'/api/v1/subjects/{sid}/notes'
        response=client.post(route+'/generate',headers=AUTH)
        assert response.status_code==202,response.text
        assert wait(client,response.json()['id'])['status']=='completed'
        data=client.get(route,headers=AUTH).json()
        assert data['current'] is None
        proposal=data['proposals'][0]
        assert proposal['chapters'][0]['sources'][0]['segment_id']==segment['id']
        accepted=client.post(route+'/'+proposal['id']+'/accept',headers=AUTH)
        assert accepted.status_code==200
        chapter=proposal['chapters'][0]
        edited=client.put(route,headers=AUTH,json={'base_revision':proposal['id'],'chapter_id':chapter['id'],'title':'Il mio titolo','text':'La mia correzione'})
        assert edited.status_code==200,edited.text
        assert edited.json()['chapters'][0]['manual']
        assert client.put(route,headers=AUTH,json={'base_revision':proposal['id'],'chapter_id':chapter['id'],'title':'Stale','text':'Not saved'}).status_code==409
        job=client.post(route+'/generate',headers=AUTH).json()
        assert wait(client,job['id'])['status']=='completed'
        proposal=client.get(route,headers=AUTH).json()['proposals'][0]
        assert any(c['text']=='La mia correzione' for c in proposal['chapters'])
        assert client.post(route+'/'+proposal['id']+'/accept',headers=AUTH).status_code==200
        exported=client.get(route+'/export',headers=AUTH)
        assert 'La mia correzione' in exported.text
        assert segment['id'] in exported.text
        assert client.get(route+'/export').status_code==401


def test_stale_sources_block_acceptance(tmp_path,monkeypatch):
    sid,lid,rid,segment=seeded(tmp_path);enable_fake_llm(monkeypatch,tmp_path)
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        route=f'/api/v1/subjects/{sid}/notes'
        job=client.post(route+'/generate',headers=AUTH).json();assert wait(client,job['id'])['status']=='completed'
        proposal=client.get(route,headers=AUTH).json()['proposals'][0]
        client.put(f'/api/v1/lessons/{lid}/transcript',headers=AUTH,json={'base_revision':rid,'segments':[{'id':segment['id'],'text':'Fonte aggiornata'}]})
        assert client.get(route,headers=AUTH).json()['proposals'][0]['blocking_stale']
        assert client.post(route+'/'+proposal['id']+'/accept',headers=AUTH).status_code==409


def test_invalid_model_citations_not_saved(tmp_path,monkeypatch):
    sid,lid,rid,segment=seeded(tmp_path);enable_fake_llm(monkeypatch,tmp_path,invalid=True)
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        route=f'/api/v1/subjects/{sid}/notes'
        job=client.post(route+'/generate',headers=AUTH).json()
        assert wait(client,job['id'])['status']=='failed'
        assert client.get(route,headers=AUTH).json()['proposals']==[]


def test_models_download_is_explicit(tmp_path):
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        assert client.get('/api/v1/models').status_code==401
        result=client.get('/api/v1/models',headers=AUTH).json()
        assert len(result['models'])==3
        assert all(m['status']=='not_installed' for m in result['models'])
        assert not (tmp_path/'models').exists()
        assert client.post('/api/v1/models/unknown/download',headers=AUTH).status_code==404


def test_missing_model_prevents_job(tmp_path):
    sid,lid,rid,segment=seeded(tmp_path)
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        assert client.post(f'/api/v1/subjects/{sid}/notes/generate',headers=AUTH).status_code==409


def test_retranscribe_adds_revision_without_erasing_previous(tmp_path,monkeypatch):
    sid,lid,rid,segment=seeded(tmp_path)
    originals=tmp_path/'originals';originals.mkdir()
    with wave.open(str(originals/'x.wav'),'wb') as audio:
        audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(16000);audio.writeframes(b'\0\0'*16000)
    monkeypatch.setattr(ModelManager,'require',lambda self,key:tmp_path/'model')
    monkeypatch.setattr(study,'runtime_path',lambda name:sys.executable)
    process=StudyEngine.process
    def controlled(self,command,identifier):
        if '-oj' in command:
            output=Path(command[command.index('-of')+1]).with_suffix('.json')
            output.write_text(json.dumps({'transcription':[{'text':'Nuova trascrizione','offsets':{'from':0,'to':1000}}]}))
        else:process(self,command,identifier)
    monkeypatch.setattr(StudyEngine,'process',controlled)
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        response=client.post(f'/api/v1/lessons/{lid}/transcribe',headers=AUTH,json={'base_revision':rid})
        assert response.status_code==202,response.text
        assert wait(client,response.json()['id'])['status']=='completed'
        current=client.get(f'/api/v1/lessons/{lid}/transcript',headers=AUTH).json()
        assert current['revision']==2 and current['segments'][0]['text']=='Nuova trascrizione'
        old=client.get(f'/api/v1/transcripts/{rid}',headers=AUTH).json()
        assert old['segments'][0]['text']==segment['text']
        assert len(client.get(f'/api/v1/lessons/{lid}/transcript/revisions',headers=AUTH).json())==2


def test_transcription_uses_lossless_enhanced_source(tmp_path,monkeypatch):
    sid,lid,rid,segment=seeded(tmp_path)
    aid=str(uuid4());directory=tmp_path/'enhanced';directory.mkdir(exist_ok=True)
    with wave.open(str(directory/(aid+'.wav')),'wb') as audio:
        audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(16000);audio.writeframes(b'\0\0'*16000)
    (directory/(aid+'.mp3')).write_bytes(b'invalid mp3: WAV must be preferred')
    with sqlite3.connect(tmp_path/'aulalocale.sqlite3') as c:
        c.execute('INSERT INTO audio_jobs VALUES (?,?,?, ?,100,NULL,?,?,?,?)',(aid,lid,'gtcrn-balanced','completed','2026-01-01','2026-01-01','GTCRN','gtcrn-recipe'))
    monkeypatch.setattr(ModelManager,'require',lambda self,key:tmp_path/'model')
    monkeypatch.setattr(study,'runtime_path',lambda name:sys.executable)
    process=StudyEngine.process
    def controlled(self,command,identifier):
        if '-oj' in command:
            output=Path(command[command.index('-of')+1]).with_suffix('.json')
            output.write_text(json.dumps({'transcription':[{'text':'Da audio IA','offsets':{'from':0,'to':1000}}]}))
        else:process(self,command,identifier)
    monkeypatch.setattr(StudyEngine,'process',controlled)
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        response=client.post(f'/api/v1/lessons/{lid}/transcribe',headers=AUTH,json={'base_revision':rid,'audio_job_id':aid})
        assert response.status_code==202,response.text
        assert wait(client,response.json()['id'])['status']=='completed'
        metadata=client.get(f'/api/v1/lessons/{lid}/transcript',headers=AUTH).json()['metadata']
        assert metadata['source']=='enhanced' and metadata['audio_job_id']==aid
        assert metadata['source_recipe']=='gtcrn-recipe'

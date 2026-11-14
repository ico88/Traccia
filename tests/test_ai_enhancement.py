from pathlib import Path
import io
import json
import os
import sqlite3
import time
import wave
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from aulalocale.app import create_app
from aulalocale.models import ModelManager
from aulalocale.ai_denoise import enhance

TOKEN='ai-audio-test-token-'*3
AUTH={'Authorization':f'Bearer {TOKEN}'}


def audio():
    buffer=io.BytesIO()
    with wave.open(buffer,'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(16000)
        wav.writeframes(b'\x10\x00'*16000)
    return buffer.getvalue()


def test_ai_requires_explicit_model_installation(tmp_path):
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        sid=client.post('/api/v1/subjects',headers=AUTH,json={'title':'Test'}).json()['id']
        lid=client.post(f'/api/v1/subjects/{sid}/lessons',headers=AUTH,data={'title':'Test'},files={'file':('x.wav',audio())}).json()['id']
        url=f'/api/v1/lessons/{lid}/enhancements'
        assert client.post(url,headers=AUTH,json={'method':'gtcrn'}).status_code==409
        assert client.get(url,headers=AUTH).json()==[]
        assert client.post(url,headers=AUTH,json={'method':'unknown'}).status_code==422


def test_transcription_refuses_foreign_or_unready_audio(tmp_path):
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        sid=client.post('/api/v1/subjects',headers=AUTH,json={'title':'Test'}).json()['id']
        lid=client.post(f'/api/v1/subjects/{sid}/lessons',headers=AUTH,data={'title':'Test'},files={'file':('x.wav',audio())}).json()['id']
        assert client.post(f'/api/v1/lessons/{lid}/transcribe',headers=AUTH,json={'audio_job_id':str(uuid4())}).status_code==409


@pytest.mark.skipif(not os.environ.get('AULALOCALE_GTCRN_TEST_MODEL'),reason='Requires explicitly supplied local GTCRN model')
def test_neural_worker_preserves_length_and_input(tmp_path):
    source=tmp_path/'source.wav';source.write_bytes(audio());target=tmp_path/'filtered.wav'
    enhance(source,target,Path(os.environ['AULALOCALE_GTCRN_TEST_MODEL']),.7)
    assert source.read_bytes()==audio()
    with wave.open(str(source),'rb') as before,wave.open(str(target),'rb') as after:
        assert before.getnframes()==after.getnframes()
        assert (after.getnchannels(),after.getsampwidth(),after.getframerate())==(1,2,16000)


@pytest.mark.skipif(not os.environ.get('AULALOCALE_GTCRN_TEST_MODEL'),reason='Requires explicitly supplied local GTCRN model')
def test_ai_api_result_source_and_backup(tmp_path,monkeypatch):
    model=Path(os.environ['AULALOCALE_GTCRN_TEST_MODEL'])
    original=ModelManager.require
    monkeypatch.setattr(ModelManager,'require',lambda self,key:model if key=='gtcrn' else original(self,key))
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        sid=client.post('/api/v1/subjects',headers=AUTH,json={'title':'Test'}).json()['id']
        lid=client.post(f'/api/v1/subjects/{sid}/lessons',headers=AUTH,data={'title':'Test'},files={'file':('x.wav',audio())}).json()['id']
        url=f'/api/v1/lessons/{lid}/enhancements'
        response=client.post(url,headers=AUTH,json={'method':'gtcrn','preset':'balanced'})
        assert response.status_code==202,response.text
        job=response.json();assert job['method']=='gtcrn' and job['preset']=='balanced'
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            state=client.get('/api/v1/audio-jobs/'+job['id'],headers=AUTH).json()
            if state['status'] not in ('queued','running'):break
            time.sleep(.05)
        assert state['status']=='completed',state
        assert 'sherpa-onnx' in state['engine']
        assert (tmp_path/'enhanced'/(job['id']+'.wav')).is_file()
        assert client.get(f'/api/v1/lessons/{lid}/audio',headers=AUTH).content==audio()
        assert client.get('/api/v1/audio-jobs/'+job['id']+'/audio',headers=AUTH).status_code==200
        assert client.post(url,headers=AUTH,json={'method':'gtcrn'}).json()['id']==job['id']
        import zipfile
        with zipfile.ZipFile(io.BytesIO(client.get('/api/v1/backup',headers=AUTH).content)) as backup:
            assert 'enhanced/'+job['id']+'.wav' in backup.namelist()

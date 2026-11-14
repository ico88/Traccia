import io,wave
from uuid import uuid4
from fastapi.testclient import TestClient
from aulalocale.app import create_app
TOKEN='recording-test-token-2026-'*2
AUTH={'Authorization':'Bearer '+TOKEN}
PCM={'Content-Type':'application/octet-stream',**AUTH}


def start(client):
    subject=client.post('/api/v1/subjects',headers=AUTH,json={'title':'Registrazioni'}).json()['id']
    r=client.post('/api/v1/recordings',headers=AUTH,json={'subject_id':subject,'title':'Lezione registrata'})
    assert r.status_code==201,r.text
    return r.json()['id'],subject


def test_recording_chunk_order_recovery_import_and_idempotency(tmp_path):
    data=b'\x10\x00'*16000
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        assert client.get('/api/v1/recordings').status_code==401
        identifier,sid=start(client);route='/api/v1/recordings/'+identifier
        assert client.post(route+'/chunks?sequence=1',headers=PCM,content=data).status_code==409
        assert client.post(route+'/chunks?sequence=0',headers=PCM,content=data).status_code==200
        assert client.post(route+'/chunks?sequence=0',headers=PCM,content=data).json()['duration_seconds']==1
        assert client.post(route+'/chunks?sequence=0',headers=PCM,content=b'\0\0').status_code==409
        assert client.delete(route,headers=AUTH).status_code==409
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        drafts=client.get('/api/v1/recordings',headers=AUTH).json();assert len(drafts)==1 and drafts[0]['duration_seconds']==1
        result=client.post(route+'/finish',headers=AUTH);assert result.status_code==200,result.text
        lesson=result.json();assert lesson['subject_id']==sid and lesson['duration_seconds']==1
        assert client.post(route+'/finish',headers=AUTH).json()['id']==lesson['id']
        audio=client.get('/api/v1/lessons/'+lesson['id']+'/audio',headers=AUTH).content
        with wave.open(io.BytesIO(audio)) as w:assert w.readframes(16000)==data
        assert client.get('/api/v1/recordings',headers=AUTH).json()==[]
        assert client.post(route+'/chunks?sequence=1',headers=PCM,content=data).status_code==409


def test_empty_recording_and_invalid_pcm(tmp_path):
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        identifier,sid=start(client);route='/api/v1/recordings/'+identifier
        assert client.post(route+'/finish',headers=AUTH).status_code==409
        assert client.post(route+'/chunks?sequence=0',headers=PCM,content=b'x').status_code==422
        assert client.post(route+'/chunks?sequence=0',headers=PCM,content=b'\0'*128002).status_code==422
        assert client.post('/api/v1/recordings',headers=AUTH,json={'subject_id':sid,'title':'Altra'}).status_code==409
        assert client.delete(route,headers=AUTH).status_code==204
        assert client.get('/api/v1/recordings',headers=AUTH).json()==[]


def test_last_pcm_write_is_recovered_after_metadata_interruption(tmp_path):
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        identifier,_=start(client)
        (tmp_path/'recordings'/(identifier+'.pcm')).write_bytes(b'\0\0'*3200)
        draft=client.get('/api/v1/recordings',headers=AUTH).json()[0]
        assert draft['last_sequence']==0 and draft['duration_seconds']==.2
        assert client.post('/api/v1/recordings/'+identifier+'/finish',headers=AUTH).status_code==200

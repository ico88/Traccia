from contextlib import closing
import hashlib
import io
import math
import sqlite3
import struct
import time
import wave
from threading import Event
from uuid import uuid4

import mutagen
import pytest
from fastapi.testclient import TestClient
from aulalocale.app import create_app
from aulalocale.enhancement import AudioWorker

TOKEN = 'enhancement-test-token-' * 3
AUTH = {'Authorization':f'Bearer {TOKEN}'}


def signal():
    result = io.BytesIO()
    with wave.open(result,'wb') as stream:
        stream.setparams((1,2,16000,0,'NONE','not compressed'))
        stream.writeframes(b''.join(struct.pack('<h',int(1200*math.sin(i*2*math.pi*220/16000))) for i in range(16000)))
    return result.getvalue()


def lesson(client):
    sid=client.post('/api/v1/subjects',headers=AUTH,json={'title':'Test'}).json()['id']
    response=client.post(f'/api/v1/subjects/{sid}/lessons',headers=AUTH,data={'title':'Synthetic'},files={'file':('test.wav',signal())})
    assert response.status_code==201
    return response.json()['id']


def create(client,lid,preset='balanced'):
    response=client.post(f'/api/v1/lessons/{lid}/enhancements',headers=AUTH,json={'preset':preset})
    assert response.status_code==202, response.text
    return response.json()


def wait(client,jid):
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        record=client.get(f'/api/v1/audio-jobs/{jid}',headers=AUTH).json()
        if record['status'] not in ('queued','running'):
            return record
        time.sleep(.02)
    pytest.fail('Worker did not finish in 10s')


@pytest.mark.parametrize('preset',['light','balanced','strong'])
def test_process_and_playback_preserves_original(tmp_path,preset):
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        lid=lesson(client)
        job=create(client,lid,preset)
        result=wait(client,job['id'])
        assert result['status']=='completed',result
        assert result['progress']==100
        assert 'ffmpeg version' in result['engine']
        assert result['filter']
        assert create(client,lid,preset)['id']==job['id']
        assert client.get(f'/api/v1/lessons/{lid}/audio',headers=AUTH).content==signal()
        url=f"/api/v1/audio-jobs/{job['id']}/audio"
        assert client.get(url).status_code==401
        content=client.get(url,headers=AUTH).content
        assert content!=signal()
        assert client.get(url,headers={**AUTH,'Range':'bytes=0-15'}).content==content[:16]
        info=mutagen.File(io.BytesIO(content)).info
        assert abs(info.length-1)<.2
    assert not list((tmp_path/'enhanced').glob('*.part.mp3'))


def test_cancel_queued_and_retry(tmp_path,monkeypatch):
    gate, entered=Event(),Event()
    original=AudioWorker.execute
    def gated(self,job):
        entered.set()
        gate.wait(5)
        original(self,job)
    monkeypatch.setattr(AudioWorker,'execute',gated)
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        lid=lesson(client); job=create(client,lid)
        assert entered.wait(2)
        assert create(client,lid)['id']==job['id']
        response=client.post(f"/api/v1/audio-jobs/{job['id']}/cancel",headers=AUTH)
        assert response.json()['status']=='cancelled'
        assert client.get(f"/api/v1/audio-jobs/{job['id']}/audio",headers=AUTH).status_code==409
        gate.set()
        retry=create(client,lid)
        assert retry['id']!=job['id']
        assert wait(client,retry['id'])['status']=='completed'
    assert len(list((tmp_path/'enhanced').glob('*.mp3')))==1


def test_missing_original_fails_without_derivative(tmp_path):
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        lid=lesson(client)
        for path in (tmp_path/'originals').iterdir(): path.unlink()
        job=create(client,lid)
        result=wait(client,job['id'])
        assert result['status']=='failed'
        assert result['error']=='Original audio is missing'
    assert not list((tmp_path/'enhanced').iterdir())


def test_recovery_after_interruption(tmp_path):
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        lid=lesson(client); job=create(client,lid)
        assert wait(client,job['id'])['status']=='completed'
    # Simulate an abrupt termination with a persisted running job and partial output.
    with sqlite3.connect(tmp_path/'aulalocale.sqlite3') as connection:
        connection.execute("UPDATE audio_jobs SET status='running',progress=12 WHERE id=?",(job['id'],))
    (tmp_path/'enhanced'/(job['id']+'.part.mp3')).write_bytes(b'incomplete')
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        result=wait(client,job['id'])
        assert result['status']=='completed'
        assert create(client,lid)['id']==job['id']
    assert not list((tmp_path/'enhanced').glob('*.part.mp3'))


def test_auth_unknown_ids_and_invalid_preset(tmp_path):
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        lid=lesson(client)
        path=f'/api/v1/lessons/{lid}/enhancements'
        assert client.post(path,json={'preset':'balanced'}).status_code==401
        assert client.post(path,headers=AUTH,json={'preset':'custom-shell-input'}).status_code==422
        assert client.post(f'/api/v1/lessons/{uuid4()}/enhancements',headers=AUTH,json={}).status_code==404
        assert client.get(f'/api/v1/audio-jobs/{uuid4()}',headers=AUTH).status_code==404
        assert client.get(path,headers=AUTH).json()==[]


def test_cancel_running_process_cleans_partial(tmp_path,monkeypatch):
    from aulalocale.enhancement import PRESETS
    monkeypatch.setitem(PRESETS,'balanced',PRESETS['balanced']+',arealtime')
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        lid=lesson(client); job=create(client,lid)
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            current=client.get(f"/api/v1/audio-jobs/{job['id']}",headers=AUTH).json()
            if current['status']=='running': break
            time.sleep(.01)
        assert current['status']=='running'
        time.sleep(.1)
        result=client.post(f"/api/v1/audio-jobs/{job['id']}/cancel",headers=AUTH).json()
        assert result['status']=='cancelled'
    assert not list((tmp_path/'enhanced').iterdir())


def test_archive_refuses_second_worker(tmp_path):
    with TestClient(create_app(tmp_path,TOKEN)):
        with pytest.raises(RuntimeError,match='another worker'):
            with TestClient(create_app(tmp_path,TOKEN)):
                pass


def test_interval_preview_is_distinct_bounded_and_preserves_original(tmp_path):
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        lid=lesson(client)
        full=create(client,lid);assert wait(client,full['id'])['status']=='completed'
        options={'method':'traditional','preset':'balanced','preview_start':.1,'preview_end':.7,'gain_db':3}
        response=client.post(f'/api/v1/lessons/{lid}/enhancements',headers=AUTH,json=options)
        assert response.status_code==202,response.text
        job=response.json();assert job['id']!=full['id'] and job['gain_db']==3 and job['preview']=={'start':.1,'end':.7}
        assert wait(client,job['id'])['status']=='completed'
        assert client.post(f'/api/v1/lessons/{lid}/transcribe',headers=AUTH,json={'audio_job_id':job['id']}).status_code==422
        assert client.post(f'/api/v1/lessons/{lid}/enhancements',headers=AUTH,json=options).json()['id']==job['id']
        options['preview_end']=2
        assert client.post(f'/api/v1/lessons/{lid}/enhancements',headers=AUTH,json=options).status_code==422
        options['preview_end']=.7;options['method']='voxlock'
        assert client.post(f'/api/v1/lessons/{lid}/enhancements',headers=AUTH,json=options).status_code in (409,422)
        with sqlite3.connect(tmp_path/'aulalocale.sqlite3') as c:filename,expected=c.execute('SELECT storage_name,sha256 FROM lessons WHERE id=?',(lid,)).fetchone()
        assert hashlib.sha256((tmp_path/'originals'/filename).read_bytes()).hexdigest()==expected
        assert mutagen.File(tmp_path/'enhanced'/(job['id']+'.mp3')).info.length<.9


def test_second_instance_does_not_migrate_an_open_archive(tmp_path):
    with TestClient(create_app(tmp_path,TOKEN)):
        with sqlite3.connect(tmp_path/'aulalocale.sqlite3') as c:c.execute('PRAGMA user_version=5')
        with pytest.raises(RuntimeError,match='another worker'):
            with TestClient(create_app(tmp_path,TOKEN)):pass
        with sqlite3.connect(tmp_path/'aulalocale.sqlite3') as c:
            assert c.execute('PRAGMA user_version').fetchone()[0]==5
            c.execute('PRAGMA user_version=6')

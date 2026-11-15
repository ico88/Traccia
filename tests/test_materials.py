from pathlib import Path
import io
import json
import sqlite3
import zipfile
from PIL import Image
import pytest
from fastapi.testclient import TestClient
from aulalocale.app import create_app
from aulalocale.restore import restore

TOKEN='materials-test-token-'*3
AUTH={'Authorization':f'Bearer {TOKEN}'}


def png():
    result=io.BytesIO();Image.new('RGB',(20,10),'green').save(result,format='PNG');return result.getvalue()


def test_image_validation_and_backup_roundtrip(tmp_path):
    root=tmp_path/'source'
    with TestClient(create_app(root,TOKEN)) as client:
        sid=client.post('/api/v1/subjects',headers=AUTH,json={'title':'Materia'}).json()['id']
        route=f'/api/v1/subjects/{sid}/materials'
        assert client.post(route,files={'file':('x.png',png())}).status_code==401
        assert client.post(route,headers=AUTH,files={'file':('bad.png',b'<script>bad</script>')}).status_code==422
        result=client.post(route,headers=AUTH,data={'caption':'Uno schema'},files={'file':('../../x.png',png())})
        assert result.status_code==201,result.text
        image=result.json();assert image['width']==20
        assert client.get(route,headers=AUTH).json()==[image]
        assert client.get(f"/api/v1/materials/{image['id']}/image",headers=AUTH).headers['content-type']=='image/png'
        assert client.get('/api/v1/backup').status_code==401
        backup=client.get('/api/v1/backup',headers=AUTH)
        assert backup.status_code==200
        archive=tmp_path/'backup.zip';archive.write_bytes(backup.content)
    restored=tmp_path/'restored';restore(archive,restored)
    with TestClient(create_app(restored,TOKEN)) as client:
        assert client.get('/api/v1/subjects',headers=AUTH).json()[0]['title']=='Materia'
        assert client.get(f'/api/v1/subjects/{sid}/materials',headers=AUTH).json()[0]['caption']=='Uno schema'
    with pytest.raises(ValueError,match='exists'):restore(archive,restored)
    assert not list((root/'exports').iterdir())


def test_restore_rejects_unsafe_paths(tmp_path):
    path=tmp_path/'bad.zip'
    with zipfile.ZipFile(path,'w') as z:
        z.writestr('manifest.json',json.dumps({'schema':5,'files':{'aulalocale.sqlite3':'x','../escape':'x'}}))
        z.writestr('aulalocale.sqlite3','not a database');z.writestr('../escape','bad')
    with pytest.raises(ValueError):restore(path,tmp_path/'target')
    assert not (tmp_path/'escape').exists()
    assert not (tmp_path/'target').exists()


def test_outline_uses_accepted_revision(tmp_path):
    from uuid import uuid4
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        sid=client.post('/api/v1/subjects',headers=AUTH,json={'title':'Materia'}).json()['id']
        rid=str(uuid4())
        chapters=[{'id':str(uuid4()),'title':'Primo argomento','text':'Testo','sources':[],'manual':True}]
        with sqlite3.connect(tmp_path/'aulalocale.sqlite3') as c:
            c.execute('INSERT INTO notes VALUES (?,?,NULL,?,1,?)',(rid,sid,json.dumps(chapters),'2026-01-01'))
        url=f'/api/v1/subjects/{sid}/materials/outline'
        assert client.post(url,headers=AUTH,json={'base_revision':str(uuid4())}).status_code==409
        response=client.post(url,headers=AUTH,json={'base_revision':rid})
        assert response.status_code==201,response.text
        record=response.json()
        assert 'Mappa dei capitoli' in record['caption']
        data=client.get(f"/api/v1/materials/{record['id']}/image",headers=AUTH).content
        with Image.open(io.BytesIO(data)) as image:
            assert image.width==1400
            assert image.info['source_revision']==rid


def test_source_map_records_exact_revision_and_source_anchors(tmp_path):
    from uuid import uuid4
    from test_study import seeded
    sid,lid,rid,segment=seeded(tmp_path);revision=str(uuid4());chapters=[{'id':str(uuid4()),'title':'A sourced chapter','text':'Example','manual':True,'sources':[{'lesson_id':lid,'revision_id':rid,'segment_id':segment['id'],'start':0}]}]
    with sqlite3.connect(tmp_path/'aulalocale.sqlite3') as c:c.execute('INSERT INTO notes VALUES (?,?,?,?,1,?)',(revision,sid,None,json.dumps(chapters),'2026-01-01'))
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        route=f'/api/v1/subjects/{sid}/materials/source-map'
        assert client.post(route,headers=AUTH,json={'base_revision':str(uuid4())}).status_code==409
        response=client.post(route,headers=AUTH,json={'base_revision':revision});assert response.status_code==201,response.text
        raw=client.get('/api/v1/materials/'+response.json()['id']+'/image',headers=AUTH).content
        with Image.open(io.BytesIO(raw)) as image:
            assert image.info['source_revision']==revision
            assert json.loads(image.info['source_anchors'])[0]['sources']==chapters[0]['sources']
            assert 'no new scientific facts' in image.info['meaning']


def test_legacy_schema_five_backup_restores_and_upgrades_without_overwrite(tmp_path):
    import hashlib
    root=tmp_path/'legacy'
    with TestClient(create_app(root,TOKEN)):pass
    db=root/'aulalocale.sqlite3'
    with sqlite3.connect(db) as c:c.execute('PRAGMA user_version=5')
    archive=tmp_path/'legacy.zip';raw=db.read_bytes()
    with zipfile.ZipFile(archive,'w') as z:
        z.writestr('aulalocale.sqlite3',raw);z.writestr('manifest.json',json.dumps({'schema':5,'files':{'aulalocale.sqlite3':hashlib.sha256(raw).hexdigest()}}))
    restored=tmp_path/'restored';restore(archive,restored)
    with sqlite3.connect(restored/'aulalocale.sqlite3') as c:assert c.execute('PRAGMA user_version').fetchone()[0]==5
    with TestClient(create_app(restored,TOKEN)) as client:assert client.get('/health').status_code==200
    with sqlite3.connect(restored/'aulalocale.sqlite3') as c:assert c.execute('PRAGMA user_version').fetchone()[0]==7
    assert db.read_bytes()==raw


def test_restore_does_not_execute_queued_backup_jobs(tmp_path):
    from uuid import uuid4
    root=tmp_path/'source';job=str(uuid4())
    with TestClient(create_app(root,TOKEN)) as client:
        sid=client.post('/api/v1/subjects',headers=AUTH,json={'title':'Private'}).json()['id']
        # The unknown job is deliberately never executable by the running worker.
        with sqlite3.connect(root/'aulalocale.sqlite3') as c:c.execute('INSERT INTO study_jobs VALUES (?,?,?,?,?,0,NULL,?,?,?)',(job,'restored-unknown',None,sid,'interrupted','{}','2026-01-01','2026-01-01'))
        response=client.get('/api/v1/backup',headers=AUTH);assert response.status_code==200
        backup=tmp_path/'pending.zip';backup.write_bytes(response.content)
    target=tmp_path/'restored';restore(backup,target)
    with sqlite3.connect(target/'aulalocale.sqlite3') as c:
        row=c.execute('SELECT status,error FROM study_jobs WHERE id=?',(job,)).fetchone();assert row[0]=='cancelled' and 'explicitly' in row[1]

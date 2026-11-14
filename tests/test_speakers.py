from uuid import uuid4
import json,sqlite3
from fastapi.testclient import TestClient
from aulalocale.app import create_app
from aulalocale.speakers import dominant_speaker
from test_study import seeded,TOKEN,AUTH


def test_speaker_overlap_is_not_forced_to_one_voice():
    turns=[{'speaker':'S01','start':0,'end':4},{'speaker':'S02','start':2,'end':4}]
    assert dominant_speaker(0,1,turns)=='S01'
    assert dominant_speaker(2,4,turns)=='overlap'
    assert dominant_speaker(5,6,turns) is None


def test_manual_labels_and_turn_assignments_are_checked_and_persist(tmp_path):
    sid,lid,_,_=seeded(tmp_path);job=str(uuid4());directory=tmp_path/'speakers';directory.mkdir()
    result={'lesson_id':lid,'version':0,'labels':{'S01':'Parlante 1','S02':'Parlante 2'},'segments':[{'id':'0','start':0,'end':1,'speaker':'S01'}]}
    (directory/(job+'.json')).write_text(json.dumps(result))
    with sqlite3.connect(tmp_path/'aulalocale.sqlite3') as c:c.execute("INSERT INTO study_jobs VALUES (?,?,?,?,?,100,NULL,?,?,?)",(job,'speakers',lid,sid,'completed','{}','2026-01-01','2026-01-01'))
    import hashlib
    (tmp_path/'originals').mkdir(exist_ok=True)
    original=tmp_path/'originals'/(lid+'.wav');original.write_bytes(b'preserved-original')
    with sqlite3.connect(tmp_path/'aulalocale.sqlite3') as c:c.execute('UPDATE lessons SET storage_name=?,sha256=? WHERE id=?',(original.name,hashlib.sha256(original.read_bytes()).hexdigest(),lid))
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        route=f'/api/v1/lessons/{lid}/speakers'
        assert client.get(route).status_code==401
        payload={'base_version':0,'labels':{'S01':'Docente','S02':'Studente'},'assignments':{'0':'S02'}}
        response=client.put(route,headers=AUTH,json=payload);assert response.status_code==200,response.text
        assert response.json()['labels']['S01']=='Docente' and response.json()['segments'][0]['speaker']=='S02'
        assert client.put(route,headers=AUTH,json=payload).status_code==409
        assert client.post(route,headers=AUTH,json={}).status_code==409
        payload['base_version']=1;payload['assignments']={'missing':'S01'}
        assert client.put(route,headers=AUTH,json=payload).status_code==422
        assert json.loads((directory/(job+'.json')).read_text())==result

        backup=client.get('/api/v1/backup',headers=AUTH);assert backup.status_code==200,backup.text
        archive=tmp_path/'backup.zip';archive.write_bytes(backup.content)
    from aulalocale.restore import restore
    restored=tmp_path/'restored';restore(archive,restored)
    with TestClient(create_app(restored,TOKEN)) as client:
        recovered=client.get(route,headers=AUTH).json()
        assert recovered['labels']=={'S01':'Docente','S02':'Studente'}
        assert recovered['segments'][0]['speaker']=='S02' and recovered['version']==1
    assert (restored/'originals'/original.name).read_bytes()==b'preserved-original'

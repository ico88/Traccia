import io,json,sqlite3,sys,time
from pathlib import Path
from uuid import uuid4
from fastapi.testclient import TestClient
from aulalocale.app import create_app
from aulalocale.study import StudyEngine
from aulalocale.models import ModelManager
from test_study import seeded,TOKEN,AUTH,wait


def test_preferences_templates_auth_and_optimistic_updates(tmp_path):
    sid,lid,rid,seg=seeded(tmp_path)
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        route=f'/api/v1/subjects/{sid}/preferences'
        assert client.get(route).status_code==401
        original=client.get(route,headers=AUTH).json();assert original['revision']==0
        templates=client.get('/api/v1/templates',headers=AUTH).json();assert len(templates)==3
        data={'base_revision':0,'settings':{'language':'it','summary_language':'en','template_id':templates[0]['id'],'glossary':['recettori','recettori']}}
        saved=client.put(route,headers=AUTH,json=data);assert saved.status_code==200,saved.text
        assert saved.json()['settings']['glossary']==['recettori']
        assert client.put(route,headers=AUTH,json=data).status_code==409
        data['base_revision']=1;data['settings']['template_id']=str(uuid4());assert client.put(route,headers=AUTH,json=data).status_code==409
        assert client.get(route.replace(sid,str(uuid4())),headers=AUTH).status_code==404
        created=client.post('/api/v1/templates',headers=AUTH,json={'name':'My template','prompt':'Use source definitions.'}).json()
        update={'name':'Revised template','prompt':'Only source definitions.','base_revision':1}
        assert client.put('/api/v1/templates/'+created['id'],headers=AUTH,json=update).status_code==200
        assert client.put('/api/v1/templates/'+created['id'],headers=AUTH,json=update).status_code==409
        assert client.post('/api/v1/templates',headers=AUTH,json={'name':' ','prompt':'x'}).status_code==422


def test_annotations_validate_time_subject_and_retry_identity(tmp_path):
    sid,lid,rid,seg=seeded(tmp_path)
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        route=f'/api/v1/lessons/{lid}/annotations';data={'id':str(uuid4()),'kind':'text','start':.5,'body':'My own words'}
        assert client.post(route,json=data).status_code==401
        added=client.post(route,headers=AUTH,json=data);assert added.status_code==201,added.text
        assert client.post(route,headers=AUTH,json=data).json()['id']==data['id']
        data['body']='different';assert client.post(route,headers=AUTH,json=data).status_code==409
        data['id']=str(uuid4());data['start']=2;assert client.post(route,headers=AUTH,json=data).status_code==422
        data['start']=float('inf')
        assert client.post(route,headers=AUTH,content=json.dumps(data)).status_code==422
        assert client.post(route,headers=AUTH,json={'kind':'image','start':0,'material_id':str(uuid4())}).status_code==404
        assert len(client.get(route,headers=AUTH).json())==1


def test_source_search_uses_current_revision_and_scope(tmp_path):
    sid,lid,rid,seg=seeded(tmp_path)
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        route=f'/api/v1/subjects/{sid}/search'
        assert client.get(route,params={'q':'recettore'}).status_code==401
        found=client.get(route,headers=AUTH,params={'q':'recettore'}).json();assert found['items'][0]['revision_id']==rid
        payload={'base_revision':rid,'segments':[{'id':seg['id'],'text':'Trasportatore corretto'}]}
        revised=client.put(f'/api/v1/lessons/{lid}/transcript',headers=AUTH,json=payload).json()
        assert client.get(route,headers=AUTH,params={'q':'recettore'}).json()['total']==0
        assert client.get(route,headers=AUTH,params={'q':'Trasportatore'}).json()['items'][0]['revision_id']==revised['id']
        assert client.get(route,headers=AUTH,params={'q':'abc','lesson_id':str(uuid4())}).status_code==404


def test_pipeline_checkpoint_recovery_does_not_duplicate_transcript_or_notes(tmp_path,monkeypatch):
    sid,lid,rid,seg=seeded(tmp_path);calls={'transcribe':0,'notes':0}
    monkeypatch.setattr(ModelManager,'require',lambda self,key:tmp_path/'model')
    monkeypatch.setattr('aulalocale.workspace.runtime_path',lambda name:sys.executable)
    def transcribe(self,job,temp):
        calls['transcribe']+=1
        with sqlite3.connect(tmp_path/'aulalocale.sqlite3') as c:c.execute('INSERT INTO transcripts VALUES (?,?,?,?,?,?)',(str(uuid4()),lid,2,json.dumps([seg]),json.dumps({'pipeline_job':job['id'],'manual':False}),'2026-01-01'))
        self.update(job['id'],'completed',100)
        assert self.get(job['id'])['status']=='running' # inner completion cannot end the entire workflow
        raise InterruptedError()
    def notes(self,job,temp):
        calls['notes']+=1
        chapters=[{'id':str(uuid4()),'title':'Source note','text':'Source text','manual':False,'sources':[],'generation':{'pipeline_job':job['id']}}]
        with sqlite3.connect(tmp_path/'aulalocale.sqlite3') as c:c.execute('INSERT INTO notes VALUES (?,?,?,?,0,?)',(str(uuid4()),sid,None,json.dumps(chapters),'2026-01-01'))
        raise InterruptedError()
    monkeypatch.setattr(StudyEngine,'transcribe',transcribe);monkeypatch.setattr(StudyEngine,'generate_notes',notes)
    identifier=str(uuid4());data={'request_id':identifier,'base_revision':rid,'language':'it','summary_language':'en'}
    route=f'/api/v1/lessons/{lid}/processing-runs'
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        result=client.post(route,headers=AUTH,json=data);assert result.status_code==202,result.text
        assert wait(client,identifier)['status']=='interrupted'
        assert client.post(route,headers=AUTH,json=data).json()['id']==identifier
        assert client.post(route,headers=AUTH,json={**data,'language':'en'}).status_code==409
    with TestClient(create_app(tmp_path,TOKEN)) as client:assert wait(client,identifier)['status']=='interrupted'
    with TestClient(create_app(tmp_path,TOKEN)) as client:assert wait(client,identifier)['status']=='completed'
    assert calls=={'transcribe':1,'notes':1}
    with sqlite3.connect(tmp_path/'aulalocale.sqlite3') as c:
        assert c.execute('SELECT count(*) FROM transcripts').fetchone()[0]==2
        assert c.execute('SELECT count(*) FROM notes').fetchone()[0]==1


def test_workspace_metadata_survives_backup_restore(tmp_path):
    from aulalocale.restore import restore
    root=tmp_path/'archive'
    with TestClient(create_app(root,TOKEN)) as client:
        sid=client.post('/api/v1/subjects',headers=AUTH,json={'title':'My course'}).json()['id']
        response=client.put(f'/api/v1/subjects/{sid}/preferences',headers=AUTH,json={'base_revision':0,'settings':{'glossary':['adrenergico']}});assert response.status_code==200
        backup=client.get('/api/v1/backup',headers=AUTH);assert backup.status_code==200
        path=tmp_path/'backup.zip';path.write_bytes(backup.content)
    destination=tmp_path/'restored';restore(path,destination)
    with TestClient(create_app(destination,TOKEN)) as client:
        result=client.get(f'/api/v1/subjects/{sid}/preferences',headers=AUTH).json();assert result['settings']['glossary']==['adrenergico']
        assert len(client.get('/api/v1/templates',headers=AUTH).json())==3


def test_mp4_audio_container_is_validated_and_playable(tmp_path):
    import subprocess,imageio_ffmpeg
    from test_ai_enhancement import audio
    source=tmp_path/'source.wav';source.write_bytes(audio());target=tmp_path/'sample.mp4'
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-y','-i',str(source),'-c:a','aac','-f','ipod',str(target)],check=True)
    with TestClient(create_app(tmp_path/'archive',TOKEN)) as client:
        sid=client.post('/api/v1/subjects',headers=AUTH,json={'title':'Test'}).json()['id']
        result=client.post(f'/api/v1/subjects/{sid}/lessons',headers=AUTH,data={'title':'MP4 audio'},files={'file':('sample.mp4',target.read_bytes(),'video/mp4')})
        assert result.status_code==201,result.text
        lesson=result.json();assert lesson['media_type']=='video/mp4'
        response=client.get(f"/api/v1/lessons/{lesson['id']}/audio",headers={**AUTH,'Range':'bytes=0-15'})
        assert response.status_code==206;assert len(response.content)==16


def test_actual_schema_six_backup_upgrades_without_changing_source(tmp_path):
    import hashlib,zipfile
    from aulalocale.restore import restore
    root=tmp_path/'legacy'
    with TestClient(create_app(root,TOKEN)):pass
    db=root/'aulalocale.sqlite3'
    with sqlite3.connect(db) as c:
        for table in ['study_questions','lecture_annotations','subject_preferences','note_templates','archive_identity']:c.execute('DROP TABLE '+table)
        c.execute('PRAGMA user_version=6')
    raw=db.read_bytes();path=tmp_path/'schema6.zip'
    with zipfile.ZipFile(path,'w') as z:
        z.writestr('aulalocale.sqlite3',raw)
        z.writestr('manifest.json',json.dumps({'schema':6,'files':{'aulalocale.sqlite3':hashlib.sha256(raw).hexdigest()}}))
    destination=tmp_path/'new';restore(path,destination)
    with TestClient(create_app(destination,TOKEN)) as client:
        assert len(client.get('/api/v1/templates',headers=AUTH).json())==3
    with sqlite3.connect(destination/'aulalocale.sqlite3') as c:assert c.execute('PRAGMA user_version').fetchone()[0]==7
    assert db.read_bytes()==raw


def test_changing_template_prepares_new_proposal_and_preserves_manual_chapter(tmp_path,monkeypatch):
    from test_study import enable_fake_llm
    sid,lid,rid,seg=seeded(tmp_path);enable_fake_llm(monkeypatch,tmp_path)
    manual={'id':str(uuid4()),'title':'My explanation','text':'Protected student wording','manual':True,'sources':[{'lesson_id':lid,'revision_id':rid,'segment_id':seg['id'],'start':0}],'generation':{'covered_revisions':{lid:rid}}}
    automatic={**manual,'id':str(uuid4()),'manual':False,'title':'Automatic chapter','text':'Previous summary'}
    with sqlite3.connect(tmp_path/'aulalocale.sqlite3') as c:c.execute('INSERT INTO notes VALUES (?,?,?,?,1,?)',(str(uuid4()),sid,None,json.dumps([manual,automatic]),'2026-01-01'))
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        template=client.get('/api/v1/templates',headers=AUTH).json()[0]
        route=f'/api/v1/subjects/{sid}/notes'
        job=client.post(route+'/generate',params={'template_id':template['id']},headers=AUTH);assert job.status_code==202,job.text
        assert wait(client,job.json()['id'])['status']=='completed'
        notes=client.get(route,headers=AUTH).json();assert notes['current']['chapters']==[manual,automatic]
        proposal=notes['proposals'][0];assert manual in proposal['chapters']
        assert all(ch['id']!=automatic['id'] for ch in proposal['chapters'])
        assert any(ch['generation'].get('template',{}).get('id')==template['id'] for ch in proposal['chapters'] if not ch['manual'])


def test_course_note_status_includes_pipeline_jobs_and_failures(tmp_path):
    sid,lid,rid,seg=seeded(tmp_path);identifier=str(uuid4())
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        with sqlite3.connect(tmp_path/'aulalocale.sqlite3') as c:c.execute('INSERT INTO study_jobs VALUES (?,?,?,?,?,0,NULL,?,?,?)',(identifier,'pipeline',lid,sid,'interrupted',json.dumps({'stage':'notes'}),'2026-01-01','2026-01-01'))
        route=f'/api/v1/subjects/{sid}/notes'
        jobs=client.get(route,headers=AUTH).json()['jobs'];assert jobs[0]['id']==identifier and jobs[0]['kind']=='pipeline'
        with sqlite3.connect(tmp_path/'aulalocale.sqlite3') as c:c.execute("UPDATE study_jobs SET status='failed',error='Pipeline stopped' WHERE id=?",(identifier,))
        assert client.get(route,headers=AUTH).json()['jobs'][0]['error']=='Pipeline stopped'

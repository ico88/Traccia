import json,sqlite3,sys
from uuid import uuid4
from fastapi.testclient import TestClient
from aulalocale.app import create_app
from aulalocale.study import StudyEngine
from aulalocale.evidence import validate_checks
from aulalocale.note_consolidation import candidates
from test_study import seeded,enable_fake_llm,wait,TOKEN,AUTH

def test_fabricated_quotes_and_changed_doses_are_not_supported():
    sources=[{'text':'The dose is 5 mg daily.'}]
    base={'claim':1,'status':'supported','source':1,'quote':'The dose is 5 mg daily.','reason':'Matches'}
    assert validate_checks(['The dose is 5 mg daily.'],sources,{'checks':[base]})[0]['status']=='supported'
    assert validate_checks(['The dose is 50 mg daily.'],sources,{'checks':[base]})[0]['status']=='uncertain'
    base['quote']='The dose is 50 mg daily.'
    assert validate_checks(['The dose is 50 mg daily.'],sources,{'checks':[base]})[0]['quote_matched'] is False

def test_local_evidence_job_preserves_the_note_and_checks_subject(tmp_path,monkeypatch):
    sid,lid,rid,segment=seeded(tmp_path);enable_fake_llm(monkeypatch,tmp_path);note,chapter=str(uuid4()),str(uuid4())
    monkeypatch.setattr('aulalocale.evidence.runtime_path',lambda name:sys.executable)
    chapters=[{'id':chapter,'title':'Recettori','text':'Il recettore lega il farmaco.','manual':True,'sources':[{'lesson_id':lid,'revision_id':rid,'segment_id':segment['id'],'start':0}]}]
    with sqlite3.connect(tmp_path/'aulalocale.sqlite3') as c:c.execute('INSERT INTO notes VALUES (?,?,?,?,1,?)',(note,sid,None,json.dumps(chapters),'2026-01-01'))
    monkeypatch.setattr(StudyEngine,'llm',lambda *a,**kw:{'checks':[{'claim':1,'status':'supported','source':1,'quote':segment['text'],'reason':'Explicitly stated.'}]})
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        route=f'/api/v1/subjects/{sid}/notes/{note}/chapters/{chapter}/evidence-check'
        assert client.post(route).status_code==401
        job=client.post(route,headers=AUTH);assert job.status_code==202,job.text
        identifier=job.json()['id'];assert wait(client,identifier)['status']=='completed'
        result=client.get('/api/v1/study-jobs/'+identifier+'/evidence',headers=AUTH).json();assert result['checks'][0]['quote_matched']
        assert client.post(route,headers=AUTH).json()['id']==identifier
        assert client.get(f'/api/v1/subjects/{sid}/notes',headers=AUTH).json()['current']['chapters']==chapters
        assert client.post(route.replace(sid,str(uuid4())),headers=AUTH).status_code==404

def test_topic_retrieval_prioritizes_rare_specific_terms_and_excludes_manual():
    chapters=[{'title':'Introduction','text':'General course study notes and basic concepts.','manual':False},{'title':'Adrenergic receptors','text':'Selective beta antagonists influence adrenergic signaling.','manual':False},{'title':'Adrenergic receptors','text':'Private correction','manual':True}]
    assert candidates(chapters,{'title':'Beta antagonists','text':'Selective adrenergic antagonists.'})[0][0]==1
    assert all(not chapter['manual'] for _,chapter in candidates(chapters,{'title':'x','text':'y'}))

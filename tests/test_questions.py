import json,sqlite3,sys
from uuid import uuid4
from fastapi.testclient import TestClient
from aulalocale.app import create_app
from aulalocale.study import StudyEngine
from aulalocale.models import ModelManager
from aulalocale.questions import validate_answer
from test_study import seeded,TOKEN,AUTH,wait


def test_answer_requires_verbatim_quotes_and_complete_quantities():
    source={'lesson_id':'l','revision_id':'r','segment_id':'s','start':0,'end':1,'text':'The dose is 15 mg daily.'}
    data={'sufficient':True,'answer':'The dose is 5 mg daily.','citations':[{'source':1,'quote':source['text']}]}
    assert validate_answer(data,[source],'en')['state']=='abstained'
    data['answer']=source['text'];assert validate_answer(data,[source],'en')['state']=='answered'
    data['citations'][0]['quote']='A fabricated supporting quotation.'
    assert validate_answer(data,[source],'en')['state']=='abstained'
    data['sufficient']=False;assert validate_answer(data,[source],'en')['state']=='abstained'


def fake_answers(monkeypatch,tmp_path):
    monkeypatch.setattr(ModelManager,'require',lambda self,key:tmp_path/'model')
    monkeypatch.setattr('aulalocale.questions.runtime_path',lambda name:sys.executable)
    def answer(self,prompt,temp,identifier,citation_count=None,mode=None):
        if mode!='question':return {'chapters':[{'title':'Full lecture summary','text':'Il recettore lega il farmaco.','citations':[1]}]}
        data=json.loads(prompt.split('DATA:\n',1)[1]);text=data['sources'][0]['text']
        return {'sufficient':True,'answer':text,'citations':[{'source':1,'quote':text}]}
    monkeypatch.setattr(StudyEngine,'llm',answer)


def test_local_question_save_is_a_version_guarded_idempotent_proposal(tmp_path,monkeypatch):
    sid,lid,rid,seg=seeded(tmp_path);fake_answers(monkeypatch,tmp_path)
    manual={'id':str(uuid4()),'title':'Student chapter','text':'Keep this wording','manual':True,'sources':[]}
    base=str(uuid4())
    with sqlite3.connect(tmp_path/'aulalocale.sqlite3') as c:c.execute('INSERT INTO notes VALUES (?,?,?,?,1,?)',(base,sid,None,json.dumps([manual]),'2026-01-01'))
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        route=f'/api/v1/subjects/{sid}/questions';payload={'question':'Cosa dice sul recettore?','request_id':str(uuid4()),'lesson_id':lid,'language':'it'}
        assert client.post(route,json=payload).status_code==401
        result=client.post(route,headers=AUTH,json=payload);assert result.status_code==202,result.text
        identifier=result.json()['id'];assert wait(client,identifier)['status']=='completed'
        answer=client.get('/api/v1/questions/'+identifier,headers=AUTH).json();assert answer['result']['state']=='answered'
        assert answer['result']['citations'][0]['revision_id']==rid
        assert client.post(route,headers=AUTH,json=payload).json()['id']==identifier
        assert client.post(route,headers=AUTH,json={**payload,'question':'Different question'}).status_code==409
        assert client.post(route,headers=AUTH,json={**payload,'request_id':str(uuid4()),'lesson_id':str(uuid4())}).status_code==404
        save='/api/v1/questions/'+identifier+'/save-note'
        assert client.post(save,headers=AUTH,json={'base_revision':None}).status_code==409
        proposal=client.post(save,headers=AUTH,json={'base_revision':base});assert proposal.status_code==201,proposal.text
        assert client.post(save,headers=AUTH,json={'base_revision':base}).json()['id']==proposal.json()['id']
        notes=client.get(f'/api/v1/subjects/{sid}/notes',headers=AUTH).json();assert notes['current']['id']==base
        assert manual in notes['proposals'][0]['chapters'];assert len(notes['proposals'])==1
        next_payload={**payload,'request_id':str(uuid4())};other=client.post(route,headers=AUTH,json=next_payload).json()['id'];assert wait(client,other)['status']=='completed'
        edited=client.put(f'/api/v1/lessons/{lid}/transcript',headers=AUTH,json={'base_revision':rid,'segments':[{'id':seg['id'],'text':'Il recettore corretto lega il farmaco.'}]});assert edited.status_code==200
        assert client.post('/api/v1/questions/'+other+'/save-note',headers=AUTH,json={'base_revision':base}).status_code==409


def test_no_evidence_abstains_without_a_model_and_survives_backup(tmp_path):
    from aulalocale.restore import restore
    root=tmp_path/'archive'
    with TestClient(create_app(root,TOKEN)) as client:
        sid=client.post('/api/v1/subjects',headers=AUTH,json={'title':'Empty course'}).json()['id']
        response=client.post(f'/api/v1/subjects/{sid}/questions',headers=AUTH,json={'question':'No source exists here.'});assert response.status_code==202,response.text
        identifier=response.json()['id'];assert wait(client,identifier)['status']=='completed'
        result=client.get('/api/v1/questions/'+identifier,headers=AUTH).json();assert result['result']['state']=='abstained'
        path=tmp_path/'backup.zip';path.write_bytes(client.get('/api/v1/backup',headers=AUTH).content)
    destination=tmp_path/'restored';restore(path,destination)
    with TestClient(create_app(destination,TOKEN)) as client:
        result=client.get('/api/v1/questions/'+identifier,headers=AUTH).json();assert result['result']['state']=='abstained'
        assert len(client.get(f'/api/v1/subjects/{sid}/questions',headers=AUTH).json())==1


def test_accepted_answer_does_not_mark_entire_lecture_as_summarized(tmp_path,monkeypatch):
    sid,lid,rid,seg=seeded(tmp_path);fake_answers(monkeypatch,tmp_path)
    monkeypatch.setattr('aulalocale.study.runtime_path',lambda name:sys.executable)
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        identifier=client.post(f'/api/v1/subjects/{sid}/questions',headers=AUTH,json={'question':'Il recettore?','lesson_id':lid}).json()['id']
        assert wait(client,identifier)['status']=='completed'
        proposal=client.post('/api/v1/questions/'+identifier+'/save-note',headers=AUTH,json={'base_revision':None}).json()['id']
        route=f'/api/v1/subjects/{sid}/notes';notes=client.get(route,headers=AUTH).json()
        chapter=notes['proposals'][0]['chapters'][0]
        assert chapter['generation']['cited_revisions']=={lid:rid}
        assert not chapter['generation'].get('covered_revisions')
        accepted=client.post(route+'/'+proposal+'/accept',headers=AUTH,json={'reviewed_chapter_ids':[chapter['id']]});assert accepted.status_code==200,accepted.text
        generated=client.post(route+'/generate',headers=AUTH);assert generated.status_code==202,generated.text
        assert wait(client,generated.json()['id'])['status']=='completed'

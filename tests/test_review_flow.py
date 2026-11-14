import json
from uuid import uuid4
from fastapi.testclient import TestClient
from aulalocale.app import create_app
from aulalocale.study import StudyEngine
from test_study import seeded,enable_fake_llm,wait,TOKEN,AUTH


def test_reviewed_passages_are_versioned_and_edits_invalidate_review(tmp_path):
    sid,lid,rid,segment=seeded(tmp_path)
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        route=f'/api/v1/lessons/{lid}/transcript'
        payload={'base_revision':rid,'segments':[{'id':segment['id'],'text':segment['text']}],'reviewed_segment_ids':[segment['id']]}
        record=client.put(route,headers=AUTH,json=payload).json()
        assert record['metadata']['reviewed_segment_ids']==[segment['id']]
        assert record['metadata']['manual'] and record['metadata']['reviewed_at']
        assert client.get(f'/api/v1/transcripts/{rid}',headers=AUTH).json()['metadata'].get('reviewed_segment_ids',[])==[]
        payload['base_revision']=record['id'];payload['segments'][0]['text']='Nuova modifica da controllare';payload.pop('reviewed_segment_ids')
        response=client.put(route,headers=AUTH,json=payload)
        assert response.status_code==200
        assert response.json()['metadata']['reviewed_segment_ids']==[]
        assert client.put(route,headers=AUTH,json=payload).status_code==409
        assert client.post(f'/api/v1/lessons/{lid}/transcribe',headers=AUTH,json={'base_revision':response.json()['id']}).status_code==409


def test_review_rejects_unknown_or_duplicate_ids_without_new_revision(tmp_path):
    sid,lid,rid,segment=seeded(tmp_path)
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        route=f'/api/v1/lessons/{lid}/transcript'
        for ids in [[str(uuid4())],[segment['id'],segment['id']]]:
            response=client.put(route,headers=AUTH,json={'base_revision':rid,'segments':[segment],'reviewed_segment_ids':ids})
            assert response.status_code==422
        assert client.get(route,headers=AUTH).json()['id']==rid


def test_notes_require_explicit_review_of_every_new_chapter(tmp_path,monkeypatch):
    sid,lid,rid,segment=seeded(tmp_path);enable_fake_llm(monkeypatch,tmp_path)
    monkeypatch.setattr(StudyEngine,'llm',lambda *args,**kwargs:{'chapters':[{'title':'Prima sezione','text':'Prima sintesi.','citations':[1]},{'title':'Seconda sezione','text':'Seconda sintesi.','citations':[1]}]})
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        route=f'/api/v1/subjects/{sid}/notes'
        job=client.post(route+'/generate',headers=AUTH).json();assert wait(client,job['id'])['status']=='completed'
        proposal=client.get(route,headers=AUTH).json()['proposals'][0];url=route+'/'+proposal['id']+'/accept'
        assert client.post(url,headers=AUTH,json={'reviewed_chapter_ids':[]}).status_code==422
        assert client.post(url,headers=AUTH,json={'reviewed_chapter_ids':[str(uuid4())]}).status_code==422
        assert client.get(route,headers=AUTH).json()['current'] is None
        ids=[c['id'] for c in proposal['chapters']]
        assert client.post(url,headers=AUTH,json={'reviewed_chapter_ids':ids[:1]}).status_code==422
        response=client.post(url,headers=AUTH,json={'reviewed_chapter_ids':ids})
        assert response.status_code==200,response.text
        assert all(c['reviewed_at'] for c in response.json()['chapters'])
        assert all(c['reviewed_at'] for c in client.get(route,headers=AUTH).json()['current']['chapters'])

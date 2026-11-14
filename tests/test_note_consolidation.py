from copy import deepcopy
import json
import sqlite3
from uuid import uuid4
from fastapi.testclient import TestClient
from aulalocale.app import create_app
from aulalocale.study import StudyEngine
from aulalocale.note_consolidation import plan,consolidate,changes,ref_key
from test_study import seeded,enable_fake_llm,wait,TOKEN,AUTH


def transcript(lid=None):
    return {'id':str(uuid4()),'lesson_id':lid or str(uuid4()),'segments':[{'id':str(uuid4()),'text':'Dato della fonte.','start':0,'end':1}]}


def chapter(t,manual=False):
    return {'id':str(uuid4()),'title':'La prova scritta','text':'La prova dura sessanta minuti.','manual':manual,'sources':[{'lesson_id':t['lesson_id'],'revision_id':t['id'],'segment_id':t['segments'][0]['id'],'start':0}],'generation':{'covered_revisions':{t['lesson_id']:t['id']}}}


def test_changed_sources_rebuild_connected_sections_and_preserve_manual():
    a,b,c=transcript(),transcript(),transcript();first=chapter(a);first['sources']+=chapter(b)['sources'];second=chapter(b);second['sources']+=chapter(c)['sources'];manual=chapter(a,True)
    known={t['lesson_id']:t['id'] for t in [a,b,c]}
    for item in [first,second,manual]:item['generation']['covered_revisions']=known
    newer={**a,'id':str(uuid4())}
    kept,selected,_=plan([first,second,manual],[newer,b,c])
    assert kept==[manual]
    assert {t['lesson_id'] for t in selected}==set(known)
    assert plan([first,second,manual],[a,b,c])[1]==[]


def test_consolidation_keeps_identity_sources_and_conflicts_separate():
    a,b=transcript(),transcript();old,new=chapter(a),chapter(b);sources={ref_key(c['sources'][0]):t['segments'][0]['text'] for c,t in [(old,a),(new,b)]}
    def merge(mode,data,count):return {'target':1} if mode=='route' else {'action':'merge','title':'Prova scritta','text':'Sintesi delle due lezioni.','citations':[1,2]}
    result=[deepcopy(old)];consolidate(result,deepcopy(new),merge,sources)
    assert len(result)==1 and result[0]['id']==old['id'] and len(result[0]['sources'])==2
    assert changes([old],result)['chapters'][0]['kind']=='updated'
    result=[deepcopy(old)]
    consolidate(result,deepcopy(new),lambda mode,data,count:{'target':1} if mode=='route' else {'action':'conflict'},sources)
    assert result[0]==old and result[1]['possible_conflict_with']==old['id']


def test_new_lesson_updates_chapter_without_resummarizing_old_lesson(tmp_path,monkeypatch):
    sid,lid,rid,segment=seeded(tmp_path);enable_fake_llm(monkeypatch,tmp_path)
    summaries=[]
    def fake(self,prompt,temp,identifier,citation_count=None,mode=None):
        if mode=='route':return {'target':1}
        if mode=='merge':return {'action':'merge','title':'Recettori','text':'Contenuti delle due lezioni integrati.','citations':[1,2]}
        summaries.append(prompt)
        return {'chapters':[{'title':'Recettori','text':'Sintesi della lezione.','citations':[1]}]}
    monkeypatch.setattr(StudyEngine,'llm',fake)
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        route=f'/api/v1/subjects/{sid}/notes'
        def generate():
            response=client.post(route+'/generate',headers=AUTH);assert response.status_code==202,response.text
            assert wait(client,response.json()['id'])['status']=='completed'
            return client.get(route,headers=AUTH).json()['proposals'][0]
        proposal=generate();cid=proposal['chapters'][0]['id']
        assert client.post(route+'/'+proposal['id']+'/accept',headers=AUTH,json={'reviewed_chapter_ids':[cid]}).status_code==200
        assert client.post(route+'/generate',headers=AUTH).status_code==409
        lid2,rid2,seg2=map(str,[uuid4(),uuid4(),uuid4()])
        with sqlite3.connect(tmp_path/'aulalocale.sqlite3') as c:
            row=c.execute('SELECT * FROM lessons WHERE id=?',(lid,)).fetchone();values=list(row);values[0]=lid2;values[2]='Seconda lezione';values[5]='y.wav';values[6]='different';values[13]='y.wav'
            c.execute('INSERT INTO lessons VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',values)
            c.execute('INSERT INTO transcripts VALUES (?,?,?,?,?,?)',(rid2,lid2,1,json.dumps([{'id':seg2,'start':0,'end':1,'text':'Nuova informazione sui recettori.'}]),'{}','2026-02-01'))
        proposal=generate()
        assert len(summaries)==2 # First lesson once, new lesson once.
        assert len(proposal['chapters'])==1 and proposal['chapters'][0]['id']==cid
        assert len(proposal['chapters'][0]['sources'])==2
        assert proposal['changes']['chapters'][0]['kind']=='updated'
        assert proposal['changes']['chapters'][0]['previous']['text']=='Sintesi della lezione.'
        assert client.post(route+'/'+proposal['id']+'/accept',headers=AUTH,json={'reviewed_chapter_ids':[cid]}).status_code==200


def test_merge_cannot_drop_one_source_and_manual_chapter_is_never_routed():
    import pytest
    a,b=transcript(),transcript();old,new=chapter(a),chapter(b);sources={ref_key(c['sources'][0]):t['segments'][0]['text'] for c,t in [(old,a),(new,b)]}
    existing=[deepcopy(old)]
    with pytest.raises(ValueError,match='entrambe'):
        consolidate(existing,new,lambda mode,data,count:{'target':1} if mode=='route' else {'action':'merge','title':'Sintesi','text':'Manca una fonte.','citations':[1]},sources)
    assert existing==[old]
    manual=chapter(a,True);existing=[manual]
    consolidate(existing,new,lambda *args:pytest.fail('Manual chapter must not be routed or rewritten'),sources)
    assert existing==[manual,new]


def test_corrected_source_requires_review_of_replaced_sections(tmp_path,monkeypatch):
    sid,lid,rid,segment=seeded(tmp_path);enable_fake_llm(monkeypatch,tmp_path)
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        route=f'/api/v1/subjects/{sid}/notes'
        def generate():
            job=client.post(route+'/generate',headers=AUTH).json();assert wait(client,job['id'])['status']=='completed'
            return client.get(route,headers=AUTH).json()['proposals'][0]
        old=generate();old_id=old['chapters'][0]['id']
        assert client.post(route+'/'+old['id']+'/accept',headers=AUTH,json={'reviewed_chapter_ids':[old_id]}).status_code==200
        client.put(f'/api/v1/lessons/{lid}/transcript',headers=AUTH,json={'base_revision':rid,'segments':[{'id':segment['id'],'text':'Testo della fonte corretto.'}]})
        proposal=generate();assert proposal['changes']['removed']==[{'chapter_id':old_id,'title':old['chapters'][0]['title']}]
        payload={'reviewed_chapter_ids':[c['id'] for c in proposal['chapters']]}
        url=route+'/'+proposal['id']+'/accept'
        assert client.post(url,headers=AUTH,json=payload).status_code==422
        payload['reviewed_removed_chapter_ids']=[old_id]
        assert client.post(url,headers=AUTH,json=payload).status_code==200


def test_possible_conflict_remains_visible_in_exports(tmp_path):
    import io,zipfile
    sid,lid,rid,segment=seeded(tmp_path);first=chapter({'id':rid,'lesson_id':lid,'segments':[segment]});second={**deepcopy(first),'id':str(uuid4()),'title':'Durata diversa','possible_conflict_with':first['id']}
    with sqlite3.connect(tmp_path/'aulalocale.sqlite3') as c:c.execute('INSERT INTO notes VALUES (?,?,NULL,?,1,?)',(str(uuid4()),sid,json.dumps([first,second]),'2026-03-01'))
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        assert 'Possibile contrasto' in client.get(f'/api/v1/subjects/{sid}/notes/export',headers=AUTH).text
        result=client.get(f'/api/v1/subjects/{sid}/study-export',headers=AUTH)
        with zipfile.ZipFile(io.BytesIO(result.content)) as z:assert 'Possibile contrasto' in z.read('dispensa.md').decode()


def test_old_metadata_on_manual_chapter_does_not_requeue_covered_revision():
    old=transcript();new={**old,'id':str(uuid4())};manual=chapter(old,True);automatic=chapter(new)
    assert plan([automatic,manual],[new])[1]==[]

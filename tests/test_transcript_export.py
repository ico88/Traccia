import json,sqlite3
from uuid import uuid4
from fastapi.testclient import TestClient
from aulalocale.app import create_app
from test_study import seeded,TOKEN,AUTH


def test_export_is_authenticated_revision_scoped_and_respects_timing(tmp_path):
    sid,lid,rid,segment=seeded(tmp_path)
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        url=f'/api/v1/lessons/{lid}/transcript/export'
        assert client.get(url).status_code==401
        text=client.get(url,headers=AUTH,params={'timestamps':False});assert text.status_code==200
        assert '[00:00:00]' not in text.text;assert segment['text'] in text.text
        srt=client.get(url,headers=AUTH,params={'format':'srt','timestamps':False});assert '00:00:00,000 --> 00:00:01,000' in srt.text
        assert 'attachment;' in srt.headers['Content-Disposition']
        assert client.get(url,headers=AUTH,params={'revision_id':str(uuid4())}).status_code==404
        changed=client.put(f'/api/v1/lessons/{lid}/transcript',headers=AUTH,json={'base_revision':rid,'segments':[{'id':segment['id'],'text':'New <script>text</script>'}]}).json()
        old=client.get(url,headers=AUTH,params={'revision_id':rid});assert segment['text'] in old.text
        md=client.get(url,headers=AUTH,params={'format':'md'});assert '&lt;script&gt;' in md.text and '<script>' not in md.text
        assert client.get(url,headers=AUTH,params={'format':'unknown'}).status_code==422


def test_export_uses_manual_speaker_labels_when_available(tmp_path):
    sid,lid,rid,segment=seeded(tmp_path);identifier=str(uuid4());folder=tmp_path/'speakers';folder.mkdir()
    data={'version':1,'labels':{'speaker_0':'Lecturer'},'segments':[{'id':str(uuid4()),'speaker':'speaker_0','start':0,'end':1}]}
    (folder/(identifier+'.json')).write_text(json.dumps(data))
    with sqlite3.connect(tmp_path/'aulalocale.sqlite3') as c:c.execute('INSERT INTO study_jobs VALUES (?,?,?,?,?,100,NULL,?,?,?)',(identifier,'speakers',lid,sid,'completed','{}','2026-01-01','2026-01-01'))
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        url=f'/api/v1/lessons/{lid}/transcript/export'
        assert 'Lecturer:' in client.get(url,headers=AUTH,params={'speakers':True}).text
        assert 'Lecturer:' not in client.get(url,headers=AUTH,params={'speakers':False}).text

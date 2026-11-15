import io,hashlib
from PIL import Image
from fastapi.testclient import TestClient
from aulalocale.app import create_app
from test_study import TOKEN,AUTH

def test_pdf_figures_have_page_provenance_and_survive_backup(tmp_path):
    data=io.BytesIO();Image.new('RGB',(80,60),'orange').save(data,format='PDF');raw=data.getvalue()
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        sid=client.post('/api/v1/subjects',headers=AUTH,json={'title':'Slides'}).json()['id'];route=f'/api/v1/subjects/{sid}/materials/pdf'
        assert client.post(route,files={'file':('slides.pdf',raw)}).status_code==401
        assert client.post(route,headers=AUTH,files={'file':('x.pdf',b'not a PDF')}).status_code==422
        r=client.post(route,headers=AUTH,files={'file':('../../slides.pdf',raw)});assert r.status_code==201,r.text
        result=r.json();assert result['page_count']==1 and len(result['materials'])==1 and not result['original_pdf_stored']
        identifier=result['materials'][0]['id'];image=client.get(f'/api/v1/materials/{identifier}/image',headers=AUTH)
        with Image.open(io.BytesIO(image.content)) as png:
            assert png.info['source_pdf_sha256']==hashlib.sha256(raw).hexdigest()
            assert png.info['source_pdf_page']=='1'
        assert not list(tmp_path.glob('pdf-*'))
        backup=client.get('/api/v1/backup',headers=AUTH);assert backup.status_code==200
        archive=tmp_path/'backup.zip';archive.write_bytes(backup.content)
    from aulalocale.restore import restore
    target=tmp_path/'restored';restore(archive,target)
    with Image.open(target/'materials'/(identifier+'.png')) as png:assert png.info['source_pdf_page']=='1'

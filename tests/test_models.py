import hashlib
import io
from pathlib import Path
import pytest
import aulalocale.models as models


class Download(io.BytesIO):
    status=200
    headers={}


def tiny_catalog(monkeypatch,content):
    monkeypatch.setattr(models,'CATALOG',{'tiny':{'name':'Tiny','task':'notes','repo':'test/model','revision':'fixed','file':'tiny.gguf','bytes':len(content),'sha256':hashlib.sha256(content).hexdigest(),'license':'test'}})


def test_download_verifies_and_detects_modified_model(tmp_path,monkeypatch):
    content=b'model-test'*100;tiny_catalog(monkeypatch,content)
    monkeypatch.setattr(models,'urlopen',lambda *a,**k:Download(content))
    manager=models.ModelManager(tmp_path)
    manager.download('tiny')
    assert manager.status()[0]['status']=='installed'
    assert manager.require('tiny').read_bytes()==content
    manager.path('tiny').write_bytes(b'corrupt')
    assert not manager.installed('tiny')
    manager.close()


def test_bad_checksum_never_published(tmp_path,monkeypatch):
    tiny_catalog(monkeypatch,b'expected')
    monkeypatch.setattr(models,'urlopen',lambda *a,**k:Download(b'badbytes'))
    manager=models.ModelManager(tmp_path);manager.download('tiny')
    assert manager.status()[0]['status']=='failed'
    assert not manager.path('tiny').exists()
    manager.close()


def test_resume_uses_range_and_keeps_correct_bytes(tmp_path,monkeypatch):
    content=b'123456789';tiny_catalog(monkeypatch,content)
    manager=models.ModelManager(tmp_path);manager.directory.mkdir()
    manager.path('tiny').with_suffix('.gguf.part').write_bytes(content[:3])
    class Resume(Download):
        status=206;headers={'Content-Range':'bytes 3-8/9'}
    def get(request,**kwargs):
        assert request.get_header('Range')=='bytes=3-'
        return Resume(content[3:])
    monkeypatch.setattr(models,'urlopen',get)
    manager.download('tiny');assert manager.require('tiny').read_bytes()==content
    manager.close()

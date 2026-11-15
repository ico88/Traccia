from pathlib import Path
from uuid import uuid4
import sqlite3,json
import pytest
from fastapi.testclient import TestClient
from aulalocale.app import create_app
from aulalocale.archive_health import inspect,quarantine,restore
from test_study import TOKEN,AUTH

def test_orphans_are_reversibly_quarantined_without_touching_originals(tmp_path):
    with TestClient(create_app(tmp_path,TOKEN)) as client:
        assert client.get('/api/v1/archive-health').status_code==401
        assert client.get('/api/v1/archive-health',headers=AUTH).json()['missing']==[]
        with pytest.raises(RuntimeError):quarantine(tmp_path,lambda:sqlite3.connect(tmp_path/'aulalocale.sqlite3'))
    (tmp_path/'materials').mkdir(exist_ok=True);(tmp_path/'originals').mkdir(exist_ok=True)
    orphan=tmp_path/'materials'/(str(uuid4())+'.png');orphan.write_bytes(b'cached pixels')
    original=tmp_path/'originals'/(str(uuid4())+'.wav');original.write_bytes(b'original stays')
    unknown=tmp_path/'materials'/'unknown.txt';unknown.write_text('keep')
    connect=lambda:sqlite3.connect(tmp_path/'aulalocale.sqlite3')
    report=inspect(tmp_path,connect);assert len(report['orphan_derivatives'])==1 and len(report['unreferenced_originals'])==1
    manifest=quarantine(tmp_path,connect);assert not orphan.exists() and original.read_bytes()==b'original stays' and unknown.exists()
    restore(tmp_path,manifest);assert orphan.read_bytes()==b'cached pixels'
    restore(tmp_path,manifest) # repeat after interruption/recovery is safe
    assert original.read_bytes()==b'original stays'
    data=json.loads(manifest.read_text());data['entries'][0]['path']='../escape.png';manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError):restore(tmp_path,manifest)


def test_quarantine_does_not_follow_managed_directory_symlinks(tmp_path):
    root=tmp_path/'archive'
    with TestClient(create_app(root,TOKEN)):pass
    outside=tmp_path/'outside';outside.mkdir();file=outside/(str(uuid4())+'.png');file.write_bytes(b'keep outside')
    (root/'materials').symlink_to(outside,target_is_directory=True)
    with pytest.raises(ValueError):quarantine(root,lambda:sqlite3.connect(root/'aulalocale.sqlite3'))
    assert file.read_bytes()==b'keep outside'

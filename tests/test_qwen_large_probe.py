import importlib.util
from pathlib import Path
import pytest


def test_qwen_probe_rejects_changed_assets(monkeypatch,tmp_path):
    folder=Path(__file__).resolve().parents[1]/'scripts';monkeypatch.syspath_prepend(str(folder))
    spec=importlib.util.spec_from_file_location('qwen_large_probe',folder/'probe_qwen_large.py')
    probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)
    for name in probe.ASSETS['qwen']['files']:(tmp_path/name).write_bytes(b'changed')
    with pytest.raises(ValueError,match='checksum mismatch'):probe.verify_qwen(tmp_path)

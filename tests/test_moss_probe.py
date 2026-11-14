import importlib.util
from pathlib import Path
import pytest


def load_probe(monkeypatch):
    folder=Path(__file__).resolve().parents[1]/'scripts'
    monkeypatch.syspath_prepend(str(folder))
    spec=importlib.util.spec_from_file_location('moss_probe_tests',folder/'probe_moss.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def test_probe_flags_empty_and_out_of_range_segments(monkeypatch):
    probe=load_probe(monkeypatch)
    assert not probe.segment_checks([],45)['timestamps_in_range']
    assert not probe.segment_checks([{'start':0,'end':46,'speaker':'S01'}],45)['timestamps_in_range']
    result=probe.segment_checks([{'start':0,'end':4,'speaker':'S02'},{'start':4,'end':8,'speaker':'S01'}],45)
    assert result['timestamps_in_range']
    assert result['speakers']==['S01','S02']
    assert not result['speaker_accuracy_measured']


def test_probe_rejects_modified_assets_before_loading_code(tmp_path,monkeypatch):
    probe=load_probe(monkeypatch)
    (tmp_path/'configuration_moss_transcribe_diarize.py').write_text('untrusted')
    with pytest.raises(ValueError,match='checksum mismatch'):probe.verify_assets(tmp_path,tmp_path)

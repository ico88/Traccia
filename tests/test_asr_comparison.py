import importlib.util
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('comparison',Path(__file__).resolve().parents[1]/'scripts/compare_asr.py')
comparison=importlib.util.module_from_spec(spec);spec.loader.exec_module(comparison)


def test_reference_scoring_counts_substitutions_insertions_and_deletions():
    result=comparison.score('alfa beta gamma','alfa delta gamma extra')
    assert result['wer']==pytest.approx(2/3)
    assert comparison.score('alfa beta gamma','alfa gamma')['wer']==pytest.approx(1/3)
    assert comparison.score('alfa beta','')['wer']==1


def test_reference_normalization_preserves_accents_and_numbers():
    assert comparison.score('È un recettore, 5!', 'è un recettore 5')['wer']==0
    assert comparison.score('caffe\u0300','caffè')['cer']==0
    assert comparison.score('recettore 5','recettore 6')['wer']==.5
    with pytest.raises(ValueError):comparison.score('...','testo inventato')


def test_reviewed_fluid_loader_checksum_must_match(tmp_path):
    (tmp_path/'model.8bit.safetensors').write_bytes(b'wrong weights')
    with pytest.raises(ValueError,match='checksum mismatch'):comparison.verify_fluid(tmp_path)


def test_review_page_escapes_transcripts_and_uses_local_audio():
    spec=importlib.util.spec_from_file_location('render_comparison',Path(__file__).resolve().parents[1]/'scripts/render_asr_comparison.py')
    renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)
    case={'sample':'sample-1','condition':'original','start_seconds':120,'path':'/private/data/sample.wav'}
    page=renderer.render({'cases':[case],'results':[{'sample':'sample-1','condition':'original','engine':'model','wall_seconds':2,'text':'<script>bad()</script>','scores':None}]})
    assert '<script>' not in page
    assert '&lt;script&gt;' in page
    assert '/private/data/' not in page
    assert "src='sample.wav'" in page


def test_human_review_scores_are_weighted_and_unreviewed_text_is_excluded():
    from scripts.score_evaluation import score_report
    report={'results':[{'sample':'short','condition':'normalized','boundary_split':False,'text':'x'},{'sample':'long','condition':'normalized','boundary_split':False,'text':'b b b b b b b b b'},{'sample':'unreviewed','condition':'normalized','boundary_split':False,'text':'perfect'}]}
    review={'samples':[{'id':'short','reference':'a','reference_reviewed':True},{'id':'long','reference':'b b b b b b b b b','reference_reviewed':True},{'id':'unreviewed','reference':'perfect','reference_reviewed':False}]}
    scored=score_report(report,review);assert scored['human_reviewed_samples']==2
    assert scored['aggregate_scores']['normalized / whole']['wer']==.1
    assert scored['aggregate_scores']['normalized / whole']['cer']==.1
    assert scored['results'][2]['scores'] is None


def test_label_hidden_listening_ratings_are_mapped_to_actual_conditions():
    from scripts.score_evaluation import score_report
    report={'results':[{'sample':'clip','condition':'normalized','boundary_split':False,'text':''},{'sample':'clip','condition':'gtcrn-normalized','boundary_split':False,'text':''}]}
    review={'samples':[{'id':'clip','reference':'','reference_reviewed':False,'conditions':{'A':'gtcrn-normalized','B':'normalized'},'ratings':{'A':{'clarity':4,'naturalness':None},'B':{'clarity':2}}}]}
    scored=score_report(report,review);assert scored['human_reviewed_samples']==0
    assert scored['listening_ratings']['gtcrn-normalized']['clarity']['mean']==4
    assert scored['listening_ratings']['normalized']['clarity']['count']==1
    assert 'naturalness' not in scored['listening_ratings']['gtcrn-normalized']

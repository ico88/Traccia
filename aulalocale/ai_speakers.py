"""Local diarization worker. Automatic IDs refer only to one recording."""
import argparse
import json
from pathlib import Path
import wave


def analyze(source,segmentation,embedding,target,num_speakers=0,progress=None):
    import numpy as np
    import sherpa_onnx
    with wave.open(str(source),'rb') as wav:
        if (wav.getnchannels(),wav.getsampwidth(),wav.getframerate())!=(1,2,16000):raise ValueError('Expected PCM mono 16 kHz')
        samples=np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2').astype(np.float32)/32768
    config=sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(model=str(segmentation),window_shift_ratio=.1)),
        embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(embedding),num_threads=1,provider='cpu'),
        clustering=sherpa_onnx.FastClusteringConfig(num_clusters=num_speakers or -1,threshold=.5),min_duration_on=.3,min_duration_off=.5)
    if not config.validate():raise ValueError('Invalid diarization model configuration')
    model=sherpa_onnx.OfflineSpeakerDiarization(config)
    def callback(done,total):
        if progress:
            partial=progress.with_suffix('.part');partial.write_text(str(done/max(1,total)));partial.replace(progress)
        return 0
    result=model.process(samples,callback=callback).sort_by_start_time()
    import math
    segments=[];duration=len(samples)/16000
    ids={speaker:index+1 for index,speaker in enumerate(sorted({item.speaker for item in result}))}
    for index,item in enumerate(result):
        if not all(math.isfinite(v) for v in [item.start,item.end]) or not 0<=item.start<item.end<=duration+.2:raise ValueError('Invalid speaker timestamps')
        segments.append({'id':str(index),'start':round(item.start,3),'end':round(min(item.end,duration),3),'speaker':f'S{ids[item.speaker]:02}'})
    target.write_text(json.dumps({'segments':segments,'labels':{key:'Parlante '+key[1:] for key in sorted({s['speaker'] for s in segments})},'duration_seconds':duration,'version':0},ensure_ascii=False))


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['input','segmentation','embedding','output']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--num-speakers',type=int,default=0);p.add_argument('--progress',type=Path)
    a=p.parse_args(argv);analyze(a.input,a.segmentation,a.embedding,a.output,a.num_speakers,a.progress)


if __name__=='__main__':main()

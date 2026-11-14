"""Streaming GTCRN worker. Reads/writes local PCM WAV; stdout is progress only."""
import argparse
import sys
import wave
from pathlib import Path


def worker_command():
    if getattr(sys,'frozen',False):return [sys.executable,'--internal-denoise']
    return [sys.executable,'-m','aulalocale.ai_denoise']


def enhance(source:Path,target:Path,model:Path,strength:float,enroll_model:Path | None=None,voice_sample:Path | None=None):
    import numpy as np
    import sherpa_onnx
    options={'voxlock':sherpa_onnx.OfflineSpeechDenoiserVoxLockModelConfig(enroll_model=str(enroll_model),chunk_model=str(model),voice_sample=str(voice_sample))} if enroll_model else {'gtcrn':sherpa_onnx.OfflineSpeechDenoiserGtcrnModelConfig(model=str(model))}
    config=sherpa_onnx.OnlineSpeechDenoiserConfig(model=sherpa_onnx.OfflineSpeechDenoiserModelConfig(**options,num_threads=1,provider='cpu',debug=False))
    if not config.validate():raise ValueError('Invalid local denoiser configuration')
    denoiser=sherpa_onnx.OnlineSpeechDenoiser(config)
    if denoiser.sample_rate!=16000:raise ValueError('Unexpected denoiser sample rate')
    written=0
    with wave.open(str(source),'rb') as reader,wave.open(str(source),'rb') as dry,wave.open(str(target),'wb') as output:
        if (reader.getnchannels(),reader.getsampwidth(),reader.getframerate())!=(1,2,16000):
            raise ValueError('Expected 16 kHz mono signed 16-bit PCM')
        total=reader.getnframes();output.setparams((1,2,16000,0,'NONE','not compressed'))
        def write(samples):
            nonlocal written
            wet=np.asarray(samples,dtype=np.float32)
            if enroll_model:wet=wet[:max(0,total-written)]
            if not len(wet):return
            original=np.frombuffer(dry.readframes(len(wet)),dtype='<i2').astype(np.float32)/32768
            if len(original)!=len(wet):raise ValueError('Denoiser changed audio length')
            mixed=(1-strength)*original+strength*wet
            output.writeframesraw((np.clip(mixed,-1,32767/32768)*32768).round().astype('<i2').tobytes())
            written+=len(wet)
        previous=0
        while True:
            data=reader.readframes(denoiser.frame_shift_in_samples)
            if not data:break
            write(denoiser(np.frombuffer(data,dtype='<i2').astype(np.float32)/32768,16000).samples)
            if written-previous>=32000:
                print(f'out_time_us={written*1000000//16000}\nprogress=continue',flush=True);previous=written
        write(denoiser.flush().samples)
        if written!=total:raise ValueError('Denoiser changed audio length')
    print(f'out_time_us={written*1000000//16000}\nprogress=end',flush=True)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--model',type=Path,required=True);parser.add_argument('--strength',type=float,default=.7)
    parser.add_argument('--enroll-model',type=Path);parser.add_argument('--voice-sample',type=Path)
    args=parser.parse_args(argv)
    if bool(args.enroll_model)!=bool(args.voice_sample):parser.error('Supply both enrollment model and voice sample')
    if not 0<=args.strength<=1:parser.error('strength must be between 0 and 1')
    enhance(args.input,args.output,args.model,args.strength,args.enroll_model,args.voice_sample)
if __name__=='__main__':main()

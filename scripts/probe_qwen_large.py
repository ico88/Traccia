"""Offline Qwen3-ASR MLX / Whisper Large v3 experiment on existing private WAV cases."""
import argparse
from dataclasses import asdict
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time

from compare_asr import sha256

ASSETS=json.loads(Path(__file__).with_name('qwen-large-assets.json').read_text())


def verify_qwen(folder):
    for name,digest in ASSETS['qwen']['files'].items():
        if sha256(folder/name)!=digest:raise ValueError('Qwen asset checksum mismatch: '+name)


def qwen_worker(model_path,audio,output):
    verify_qwen(model_path)
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    import mlx.core as mx
    from mlx_audio.stt.utils import load_model
    started=time.monotonic();model=load_model(model_path.resolve(),strict=True);mx.eval(model.parameters())
    loading=time.monotonic()-started;started=time.monotonic()
    result=model.generate(str(audio.resolve()),language='Italian',max_tokens=1024,temperature=0,verbose=False)
    mx.synchronize()
    data=asdict(result)
    data.update({'load_seconds':loading,'inference_seconds':time.monotonic()-started,
        'runtime_versions':{name:version(name) for name in ['mlx-audio','mlx','mlx-metal','numpy']},
        'mlx_peak_bytes':mx.get_peak_memory(),'token_limit_reached':result.generation_tokens>=1024,
        'timestamp_kind':'chunk_bounds_only; forced aligner not loaded'})
    output.write_text(json.dumps(data,ensure_ascii=False,indent=2))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--comparison',type=Path)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--qwen-model',type=Path,required=True)
    p.add_argument('--qwen-python',type=Path)
    p.add_argument('--whisper-model',type=Path)
    p.add_argument('--whisper-bin',type=Path)
    p.add_argument('--engine',choices=['both','qwen','whisper'],default='both')
    p.add_argument('--internal-qwen',action='store_true',help=argparse.SUPPRESS)
    p.add_argument('--audio',type=Path,help=argparse.SUPPRESS)
    args=p.parse_args()
    if args.internal_qwen:qwen_worker(args.qwen_model,args.audio,args.output);return
    if not all([args.comparison,args.qwen_python,args.whisper_model,args.whisper_bin]):p.error('Supply all model/runtime paths and comparison')
    if args.output.exists():p.error('Choose a new output directory')
    verify_qwen(args.qwen_model)
    if sha256(args.whisper_model)!=ASSETS['whisper']['sha256']:raise ValueError('Whisper Large v3 checksum mismatch')
    comparison=json.loads(args.comparison.read_text())
    for case in comparison['cases']:
        if sha256(case['path'])!=case['sha256']:raise ValueError('Audio checksum mismatch')
    args.output.mkdir(parents=True)
    rows=[]
    report={'platform':platform.platform(),'assets':ASSETS,'duration_seconds':comparison['duration_seconds'],
        'source_sha256':comparison['source_sha256'],'cases':comparison['cases'],'results':rows,
        'settings':{'qwen_bits':8,'whisper_weights':'FP16 complete Large v3','language':'Italian','qwen_max_tokens':1024,'qwen_temperature':0,'whisper_threads':4,'context_prompt':None},
        'timing':'Fresh process per case; wall_seconds includes runtime startup, model loading and inference. Qwen worker also verifies local assets. Cache warming influences results. RSS and MLX memory are different measures.',
        'accuracy':'Unmeasured: human references not available. No winner inferred from fluency.'}
    for case in comparison['cases']:
        for engine in ['whisper-large-v3-fp16','qwen3-asr-1.7b-mlx-8bit']:
            if args.engine=='qwen' and not engine.startswith('qwen'):continue
            if args.engine=='whisper' and not engine.startswith('whisper'):continue
            prefix=args.output/(case['sample']+'-'+case['condition']+'-'+engine)
            if engine.startswith('qwen'):
                command=[str(args.qwen_python.absolute()),str(Path(__file__).resolve()),'--internal-qwen','--qwen-model',str(args.qwen_model.resolve()),'--audio',case['path'],'--output',str(prefix.with_suffix('.json').resolve())]
            else:
                command=[str(args.whisper_bin.resolve()),'-m',str(args.whisper_model.resolve()),'-f',case['path'],'-l','it','-t','4','-oj','-of',str(prefix.resolve()),'-np','-sns','-ml','180','-sow']
            if sys.platform=='darwin':command=['/usr/bin/time','-l']+command
            started=time.monotonic()
            with prefix.with_suffix('.log').open('w') as log:subprocess.run(command,stdout=log,stderr=log,check=True,timeout=300,env={**os.environ,'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'})
            elapsed=time.monotonic()-started
            data=json.loads(prefix.with_suffix('.json').read_text());qwen=engine.startswith('qwen')
            text=data['text'] if qwen else ' '.join(s['text'].strip() for s in data['transcription'])
            match=re.search(r'(\d+)\s+maximum resident set size',prefix.with_suffix('.log').read_text())
            row={**{k:v for k,v in case.items() if k not in ['path','sha256']},'engine':engine,'wall_seconds':elapsed,'text':text,'scores':None,
                'process_peak_rss_bytes':int(match.group(1)) if match else None}
            if qwen:row.update({k:data[k] for k in ['segments','load_seconds','inference_seconds','runtime_versions','mlx_peak_bytes','token_limit_reached','timestamp_kind']})
            else:row.update({'segments':data['transcription'],'timestamp_kind':'whisper_generated_segments; alignment accuracy not measured'})
            rows.append(row);(args.output/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
            print(case['sample'],case['condition'],engine,round(elapsed,2),'seconds',flush=True)
    print('Finished. No human accuracy reference; app/archive unchanged.')


if __name__=='__main__':main()

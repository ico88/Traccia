"""Offline MOSS experiment on the existing, private Fluid/Whisper WAV cases.

Run from the isolated MOSS environment. No model/code downloads or archive writes.
"""
import argparse
from dataclasses import asdict
import importlib.util
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import resource
import sys
import time

from compare_asr import sha256


def verify_assets(model,helpers):
    manifest=json.loads(Path(__file__).with_name('moss-assets.json').read_text())
    for root,key in [(model,'files'),(helpers,'helpers')]:
        for name,digest in manifest[key].items():
            if sha256(root/name)!=digest:raise ValueError('MOSS asset checksum mismatch: '+name)
    return manifest


def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module


def segment_checks(segments,duration):
    return {'segments':len(segments),'speakers':sorted({s['speaker'] for s in segments}),
            'timestamps_in_range':bool(segments) and all(0<=s['start']<=s['end']<=duration+.1 for s in segments),
            'last_complete_end_seconds':max((s['end'] for s in segments),default=None),'alignment_accuracy_measured':False,'speaker_accuracy_measured':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',type=Path,required=True)
    parser.add_argument('--helpers',type=Path,required=True,help='Pinned source package directory containing inference_utils.py')
    parser.add_argument('--comparison',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--device',choices=['mps','cpu'],default='mps')
    parser.add_argument('--condition',choices=['original','normalized','gtcrn-light-normalized'])
    parser.add_argument('--sample',help='Only one sample ID, for diagnostic controls')
    parser.add_argument('--max-new-tokens',type=int,default=2048)
    args=parser.parse_args()
    if args.output.exists():parser.error('Choose a new output directory')
    if args.max_new_tokens<1:parser.error('Invalid token limit')
    manifest=verify_assets(args.model,args.helpers)
    comparison=json.loads(args.comparison.read_text());cases=[c for c in comparison['cases'] if (not args.condition or c['condition']==args.condition) and (not args.sample or c['sample']==args.sample)]
    if not cases:parser.error('No matching WAV cases')
    for case in cases:
        if sha256(case['path'])!=case['sha256']:raise ValueError('Audio case checksum mismatch')
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    import torch
    from transformers import AutoModelForCausalLM,AutoProcessor
    if args.device=='mps' and not torch.backends.mps.is_available():raise RuntimeError('MPS not available; CPU fallback is never automatic')
    device=torch.device(args.device);dtype=torch.float32
    helpers=load_module('aulalocale_moss_helpers',args.helpers/'inference_utils.py')
    transcript_parser=load_module('aulalocale_moss_parser',args.helpers/'transcript_parser.py')
    started=time.monotonic()
    model=AutoModelForCausalLM.from_pretrained(str(args.model.resolve()),trust_remote_code=True,local_files_only=True,dtype=dtype,attn_implementation='sdpa').to(device).eval()
    processor=AutoProcessor.from_pretrained(str(args.model.resolve()),trust_remote_code=True,local_files_only=True)
    if args.device=='mps':torch.mps.synchronize()
    load_seconds=time.monotonic()-started
    args.output.mkdir(parents=True)
    report={'model':manifest['repository'],'model_revision':manifest['revision'],'helpers_revision':manifest['source_revision'],
        'runtime_versions':{name:version(name) for name in ['torch','transformers','numpy','librosa','safetensors']},
        'device':args.device,'dtype':'float32','platform':platform.platform(),'load_seconds':load_seconds,
        'max_new_tokens':args.max_new_tokens,'do_sample':False,'prompt':helpers.DEFAULT_PROMPT,
        'timing':'One model load shared across cases. Case timings include audio preprocessing and generation. Not directly comparable to fresh-process Fluid/Whisper wall times.',
        'accuracy':'No human references: transcription and speaker accuracy are unmeasured.',
        'source_sha256':comparison['source_sha256'],'duration_seconds':comparison['duration_seconds'],'cases':cases,'results':[]}
    for case in cases:
        started=time.monotonic()
        def progress(count):
            if count%64==0:print(case['sample'],case['condition'],'generated tokens',count,flush=True)
        result=helpers.generate_transcription(model,processor,helpers.build_transcription_messages(case['path']),
            max_new_tokens=args.max_new_tokens,do_sample=False,device=device,dtype=dtype,token_callback=progress)
        if args.device=='mps':torch.mps.synchronize()
        elapsed=time.monotonic()-started
        segments=[asdict(s) for s in transcript_parser.parse_transcript(result['text'])]
        row={**{k:v for k,v in case.items() if k not in ['path','sha256']},'engine':'moss-mps-fp32' if args.device=='mps' else 'moss-cpu-fp32',
            'case_seconds':elapsed,'raw_text':result['text'],'text':' '.join(s['text'] for s in segments),
            'generated_tokens':result['generated_tokens'],'token_limit_reached':result['generated_tokens']>=args.max_new_tokens,
            'prompt_tokens':result['prompt_len'],'segments':segments,'checks':segment_checks(segments,comparison['duration_seconds']),
            'scores':None,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
        if args.device=='mps':row.update({'mps_current_allocated_bytes':torch.mps.current_allocated_memory(),'mps_driver_allocated_bytes':torch.mps.driver_allocated_memory()})
        report['results'].append(row)
        (args.output/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
        print(case['sample'],case['condition'],'finished',round(elapsed,2),'seconds',len(segments),'segments',flush=True)
    print('Completed; speaker labels are anonymous, not lecturer identities.',flush=True)


if __name__=='__main__':main()

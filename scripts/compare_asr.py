"""Offline ASR experiment; writes private audio/text only to the explicit output directory.

Fluid's reviewed, hash-pinned loader is read from the supplied local model directory.
No weights or code are downloaded. Run --help using the normal AulaLocale environment.
"""
import argparse
from dataclasses import asdict
import hashlib
import importlib.util
from importlib.metadata import version
import platform
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time
import unicodedata

FLUID_REVISION='aeb1d4e43487586b15d86c0a1dd4511e1cf6b7a0'
FLUID_HASHES={
    'model.8bit.safetensors':'2a09ae3033356b3acd9b782da5183f80609806169e10629dcc38bca766a98ca7',
    'config.json':'c79978692bc5c24bcbfa07032fa4ba75de3846b6cd86ee630673158671312b69',
    'fluid_speech_mlx.py':'a895beec91f927837e48e1db8824dc1d226a29847e053cbf1f85118919a15559',
}


def sha256(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda:source.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()


def verify_fluid(folder):
    for name,expected in FLUID_HASHES.items():
        if sha256(folder/name)!=expected:raise ValueError('Fluid asset checksum mismatch: '+name)


def normalized(text):
    text=unicodedata.normalize('NFC',text).casefold()
    return ' '.join(''.join(c if c.isalnum() else ' ' for c in text).split())


def distance(a,b):
    previous=list(range(len(b)+1))
    for i,left in enumerate(a,1):
        current=[i]
        for j,right in enumerate(b,1):current.append(min(current[-1]+1,previous[j]+1,previous[j-1]+(left!=right)))
        previous=current
    return previous[-1]


def score(reference,hypothesis):
    reference=normalized(reference);hypothesis=normalized(hypothesis)
    if not reference:raise ValueError('Reference is empty')
    words=reference.split();characters=reference.replace(' ','')
    return {'wer':distance(words,hypothesis.split())/len(words),
            'cer':distance(characters,hypothesis.replace(' ',''))/len(characters),
            'reference_words':len(words)}


def fluid_worker(folder,audio,output,ffmpeg):
    verify_fluid(folder)
    # A local FFmpeg symlink satisfies the upstream audio reader without system installation.
    with tempfile.TemporaryDirectory(prefix='aulalocale-fluid-') as temporary:
        (Path(temporary)/'ffmpeg').symlink_to(ffmpeg)
        os.environ['PATH']=temporary+os.pathsep+os.environ.get('PATH','')
        os.environ['HF_HUB_OFFLINE']='1'
        import mlx.core as mx
        spec=importlib.util.spec_from_file_location('aulalocale_reviewed_fluid',folder/'fluid_speech_mlx.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        started=time.monotonic();model=module.load(str(folder),bits=8,clean_mode=False);mx.eval(model.parameters())
        loading=time.monotonic()-started;started=time.monotonic();result=model.transcribe(audio)
        output.write_text(json.dumps({'text':result.text,'sentences':asdict(result)['sentences'],
            'load_seconds':loading,'inference_seconds':time.monotonic()-started,
            'runtime_versions':{key:version(key) for key in ['mlx','mlx-metal','parakeet-mlx','numpy']},'mlx_peak_bytes':mx.get_peak_memory(),'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},ensure_ascii=False,indent=2))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--fluid-model',type=Path,required=True)
    parser.add_argument('--fluid-python',type=Path)
    parser.add_argument('--whisper-model',type=Path)
    parser.add_argument('--whisper-bin',type=Path)
    parser.add_argument('--gtcrn-model',type=Path)
    parser.add_argument('--starts',type=float,nargs='+',default=[120,2100,4200])
    parser.add_argument('--duration',type=float,default=45)
    parser.add_argument('--references',type=Path,help='JSON mapping sample-1 etc. to human-verified reference text')
    parser.add_argument('--internal-fluid',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--ffmpeg',type=Path,help=argparse.SUPPRESS)
    args=parser.parse_args(argv)
    folder=args.fluid_model.resolve()
    if args.internal_fluid:
        fluid_worker(folder,args.source,args.output,args.ffmpeg);return
    if not all([args.fluid_python,args.whisper_model,args.whisper_bin,args.gtcrn_model]):parser.error('Supply all local model and runtime paths')
    if args.duration<=0 or not all(x>=0 for x in args.starts):parser.error('Invalid time range')
    if args.output.exists():parser.error('Choose a new output directory; existing results are never overwritten')
    import imageio_ffmpeg
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from aulalocale.ai_denoise import enhance
    from aulalocale.models import CATALOG
    verify_fluid(folder)
    for path,key in [(args.whisper_model,'whisper-turbo'),(args.gtcrn_model,'gtcrn')]:
        if sha256(path)!=CATALOG[key]['sha256']:raise ValueError('Local model checksum mismatch: '+key)
    references=json.loads(args.references.read_text()) if args.references else {}
    args.output.mkdir(parents=True);ffmpeg=Path(imageio_ffmpeg.get_ffmpeg_exe()).resolve()
    cases=[];rows=[]
    for index,start in enumerate(args.starts,1):
        sample=f'sample-{index}';original=args.output/(sample+'-original.wav')
        subprocess.run([str(ffmpeg),'-v','error','-nostdin','-ss',str(start),'-i',str(args.source.resolve()),'-t',str(args.duration),'-ac','1','-ar','16000','-c:a','pcm_s16le',str(original)],check=True)
        neural=args.output/(sample+'-gtcrn-light.wav');enhance(original,neural,args.gtcrn_model.resolve(),.35)
        for condition,source in [('original',original),('normalized',original),('gtcrn-light-normalized',neural)]:
            prepared=args.output/(sample+'-'+condition+'-input.wav')
            command=[str(ffmpeg),'-v','error','-nostdin','-i',str(source)]
            if condition!='original':command+=['-af','loudnorm=I=-20:TP=-2:LRA=11']
            subprocess.run(command+['-ac','1','-ar','16000','-c:a','pcm_s16le',str(prepared)],check=True)
            cases.append({'sample':sample,'start_seconds':start,'condition':condition,'path':str(prepared.resolve()),'sha256':sha256(prepared)})
    report={'platform':platform.platform(),'machine':platform.machine(),'fluid_revision':FLUID_REVISION,'fluid_hashes':FLUID_HASHES,'source_sha256':sha256(args.source),
        'duration_seconds':args.duration,'settings':{'fluid_bits':8,'clean_mode':False,'fluid_dtype':'bfloat16','whisper_language':'it','whisper_threads':4,'whisper_prompt':None,'gtcrn_strength':.35},
        'timing':'Each case uses a fresh subprocess. wall_seconds includes imports/loading/inference; preparation excluded. MLX/process peak memory are different measures.',
        'accuracy':'Human references only; null scores are unmeasured, never model-estimated.',
        'cases':cases,'results':rows}
    for case in cases:
        for engine in ['whisper-turbo','fluid-mlx-8bit']:
            prefix=args.output/(case['sample']+'-'+case['condition']+'-'+engine)
            started=time.monotonic()
            if engine=='fluid-mlx-8bit':
                result_file=prefix.with_suffix('.json')
                command=[str(args.fluid_python.absolute()),str(Path(__file__).resolve()),'--internal-fluid','--source',case['path'],'--output',str(result_file.resolve()),'--fluid-model',str(folder),'--ffmpeg',str(ffmpeg)]
            else:
                command=[str(args.whisper_bin.resolve()),'-m',str(args.whisper_model.resolve()),'-f',case['path'],'-l','it','-t','4','-oj','-of',str(prefix.resolve()),'-np','-sns','-ml','180','-sow']
            with prefix.with_suffix('.log').open('w') as log:subprocess.run(command,stdout=log,stderr=log,check=True,env={**os.environ,'HF_HUB_OFFLINE':'1'},timeout=180)
            elapsed=time.monotonic()-started
            data=json.loads(prefix.with_suffix('.json').read_text())
            text=data['text'] if engine=='fluid-mlx-8bit' else ' '.join(part['text'].strip() for part in data['transcription'])
            row={**{k:v for k,v in case.items() if k not in ['path','sha256']},'engine':engine,'wall_seconds':elapsed,'text':text,
                'scores':score(references[case['sample']],text) if references.get(case['sample'],'').strip() else None}
            if engine=='fluid-mlx-8bit':row.update({k:data[k] for k in ['load_seconds','inference_seconds','mlx_peak_bytes','process_peak_rss_bytes','runtime_versions']})
            rows.append(row);(args.output/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
            print(case['sample'],case['condition'],engine,round(elapsed,2),'seconds',flush=True)
    (args.output/'references.template.json').write_text(json.dumps({case['sample']:'' for case in cases},indent=2))
    print('Completed. Accuracy remains unmeasured until human reference text is supplied.')


if __name__=='__main__':main()

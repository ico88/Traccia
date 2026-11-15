"""Small pinned model catalog. Downloads weights only; never uploads study data."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock, Event
from urllib.request import Request, urlopen
import hashlib
import json
import os
import shutil
import ssl
import tarfile

import certifi
from fastapi import APIRouter, Depends, HTTPException

CATALOG = {
    'whisper-turbo': {'name':'Whisper Large v3 Turbo · Q8', 'task':'transcription',
        'repo':'ggerganov/whisper.cpp', 'revision':'5359861c739e955e79d9a303bcbc70fb988958b1',
        'file':'ggml-large-v3-turbo-q8_0.bin', 'bytes':874188075,
        'sha256':'317eb69c11673c9de1e1f0d459b253999804ec71ac4c23c17ecf5fbe24e259a1', 'license':'MIT'},
    'qwen3-4b': {'name':'Qwen3 4B · Q4_K_M', 'task':'notes',
        'repo':'Qwen/Qwen3-4B-GGUF', 'revision':'bc640142c66e1fdd12af0bd68f40445458f3869b',
        'file':'Qwen3-4B-Q4_K_M.gguf', 'bytes':2497280256,
        'sha256':'7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5', 'license':'Apache-2.0'},
    'gtcrn': {'name':'GTCRN · pulizia voce IA', 'task':'enhancement',
        'repo':'Xiaobin-Rong/gtcrn', 'revision':'sherpa-speech-enhancement-models-e77603ac',
        'url':'https://github.com/k2-fsa/sherpa-onnx/releases/download/speech-enhancement-models/gtcrn_simple.onnx',
        'file':'gtcrn_simple.onnx','bytes':535638,
        'sha256':'e77603ac0c23dac3227dd2d7135b3a585cbee2679048aecfa886657d3ae1b534','license':'MIT'},

}

CATALOG.update({'speaker-segmentation': {'name': 'Analisi parlanti · segmentazione', 'task': 'speakers', 'repo': 'csukuangfj/sherpa-onnx-pyannote-segmentation-3-0', 'revision': '9403a6902bb58e3d5ae8c7e77c3422de279db2e0', 'file': 'speaker-segmentation.onnx', 'url': 'https://huggingface.co/csukuangfj/sherpa-onnx-pyannote-segmentation-3-0/resolve/9403a6902bb58e3d5ae8c7e77c3422de279db2e0/model.int8.onnx', 'bytes': 1540506, 'sha256': 'd582f4b4c6b48205de7e0643c57df0df5615a3c176189be3fc461e9d18827b5d', 'license': 'MIT', 'requires': ['speaker-embedding']}, 'speaker-embedding': {'name': 'Analisi parlanti · confronto delle voci', 'task': 'speakers', 'repo': 'modelscope/3D-Speaker', 'revision': 'sherpa-release-1a331345', 'url': 'https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx', 'file': 'speaker-embedding.onnx', 'bytes': 39593761, 'sha256': '1a331345f04805badbb495c775a6ddffcdd1a732567d5ec8b3d5749e3c7a5e4b', 'license': 'Apache-2.0'}, 'voxlock-enroll': {'name': 'Isolamento docente · campione vocale', 'task': 'enhancement', 'repo': 'arbazsiddiqui/voxlock', 'revision': 'sherpa-release-5d06048c', 'file': 'voxlock-enroll.onnx', 'bytes': 12476014, 'sha256': '5d06048c156bb8cd422d29848e6d38fb26a7b39f6f7fd92eccf2a6ed1ce003c6', 'license': 'Apache-2.0', 'archive': {'url': 'https://github.com/k2-fsa/sherpa-onnx/releases/download/speech-enhancement-models/sherpa-onnx-voxlock-int8.tar.bz2', 'bytes': 72508647, 'sha256': 'bcb947f9e8676d3e963f6048b0088505c84f0843bfdc88cb26dde3264d81570b', 'member': 'sherpa-onnx-voxlock-int8/enroll.onnx'}}, 'voxlock-chunk': {'name': 'Isolamento docente · modello principale', 'task': 'enhancement', 'repo': 'arbazsiddiqui/voxlock', 'revision': 'sherpa-release-df61a9d0', 'file': 'voxlock-chunk.onnx', 'bytes': 66608910, 'sha256': 'df61a9d0062b0adbcf1182302b1eb8b815f15ac47ea4923e8e164c1aff64121d', 'license': 'Apache-2.0', 'archive': {'url': 'https://github.com/k2-fsa/sherpa-onnx/releases/download/speech-enhancement-models/sherpa-onnx-voxlock-int8.tar.bz2', 'bytes': 72508647, 'sha256': 'bcb947f9e8676d3e963f6048b0088505c84f0843bfdc88cb26dde3264d81570b', 'member': 'sherpa-onnx-voxlock-int8/chunk_int8.onnx'}, 'requires': ['voxlock-enroll']}})


def runtime_path(name):
    variable = 'AULALOCALE_WHISPER_BIN' if name == 'whisper-cli' else 'AULALOCALE_LLAMA_BIN'
    configured = os.environ.get(variable)
    if configured:
        path = Path(configured).expanduser()
        return str(path.resolve()) if path.is_file() and os.access(path, os.X_OK) else None
    local = Path(__file__).resolve().parent.parent / 'runtimes' / name
    return str(local) if local.is_file() and os.access(local, os.X_OK) else shutil.which(name)


class ModelManager:
    def __init__(self, root):
        self.directory = root / 'models'
        self.lock = Lock()
        self.stop = Event()
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='model-download')
        self.states = {}

    def path(self, identifier):
        if identifier not in CATALOG: raise HTTPException(404,'Model not found')
        return self.directory / CATALOG[identifier]['file']

    def installed(self, identifier):
        path = self.path(identifier)
        marker = path.with_suffix(path.suffix+'.verified.json')
        if not path.is_file() or path.stat().st_size != CATALOG[identifier]['bytes'] or not marker.is_file():
            return False
        try:
            record=json.loads(marker.read_text())
            return record.get('sha256') == CATALOG[identifier]['sha256'] and record.get('mtime_ns') == path.stat().st_mtime_ns
        except (OSError,ValueError):
            return False

    def status(self):
        result=[]
        with self.lock:
            for identifier, model in CATALOG.items():
                installed=self.installed(identifier)
                state=self.states.get(identifier,{'status':'not_installed','downloaded':0,'error':None})
                result.append({'id':identifier,**model,**state, 'status':'installed' if installed else state['status'],
                               'downloaded':model['bytes'] if installed else state['downloaded']})
        return result

    def require(self, identifier):
        if not self.installed(identifier): raise HTTPException(409,'Install the required local model first')
        return self.path(identifier)

    def start(self, identifier):
        self.path(identifier)
        for dependency in CATALOG[identifier].get('requires',[]):self.start(dependency)
        with self.lock:
            if self.installed(identifier) or self.states.get(identifier,{}).get('status') in ('queued','downloading','verifying'):
                return
            self.states[identifier]={'status':'queued','downloaded':0,'error':None}
            self.pool.submit(self.download,identifier)

    def close(self):
        self.stop.set()
        self.pool.shutdown(wait=True,cancel_futures=True)

    def download(self, identifier):
        model=CATALOG[identifier]; path=self.path(identifier)
        transfer=model.get('archive',model)
        download_path=self.directory/('.cache-'+transfer['sha256']+'.tar.bz2') if 'archive' in model else path
        self.directory.mkdir(parents=True,exist_ok=True)
        partial=download_path.with_suffix(download_path.suffix+'.part')
        try:
            if 'archive' in model and download_path.is_file():
                if hashlib.sha256(download_path.read_bytes()).hexdigest()==transfer['sha256']:shutil.copyfile(download_path,partial)
                else:download_path.unlink()
            offset=partial.stat().st_size if partial.exists() else 0
            if offset > transfer['bytes']: partial.unlink(); offset=0
            if shutil.disk_usage(self.directory).free < transfer['bytes']-offset+model['bytes']+100*1024*1024:
                raise ValueError('Spazio insufficiente per il modello')
            if offset < transfer['bytes']:
                url=transfer.get('url') or f"https://huggingface.co/{model['repo']}/resolve/{model['revision']}/{model['file']}"
                headers={'Range':f'bytes={offset}-'} if offset else {}
                with urlopen(Request(url,headers=headers),context=ssl.create_default_context(cafile=certifi.where()),timeout=20) as response:
                    if response.status != 206: offset=0
                    elif response.headers.get('Content-Range','').split('/')[0] != f'bytes {offset}-{transfer["bytes"]-1}':
                        raise ValueError('Intervallo di download inatteso')
                    with partial.open('ab' if offset else 'wb') as output:
                        while not self.stop.is_set():
                            chunk=response.read(1024*1024)
                            if not chunk: break
                            offset+=len(chunk)
                            if offset>transfer['bytes']: raise ValueError('Dimensione del modello inattesa')
                            output.write(chunk)
                            with self.lock: self.states[identifier]={'status':'downloading','downloaded':offset,'error':None}
                if self.stop.is_set(): return
            with self.lock: self.states[identifier]={'status':'verifying','downloaded':offset,'error':None}
            digest=hashlib.sha256()
            with partial.open('rb') as downloaded:
                for chunk in iter(lambda:downloaded.read(4*1024*1024),b''): digest.update(chunk)
            if partial.stat().st_size!=transfer['bytes'] or digest.hexdigest()!=transfer['sha256']:
                partial.unlink(missing_ok=True)
                raise ValueError('Verifica SHA-256 fallita: riscaricare il modello')
            if 'archive' in model:
                partial.replace(download_path)
                extracted=path.with_suffix(path.suffix+'.part')
                with tarfile.open(download_path) as archive:
                    member=archive.getmember(transfer['member'])
                    if not member.isfile() or member.size!=model['bytes']:raise ValueError('File modello inatteso nell’archivio')
                    with archive.extractfile(member) as source,extracted.open('wb') as target:shutil.copyfileobj(source,target)
                if hashlib.sha256(extracted.read_bytes()).hexdigest()!=model['sha256']:
                    extracted.unlink();raise ValueError('Verifica del modello estratto fallita')
                extracted.replace(path)
            else:partial.replace(path)
            path.with_suffix(path.suffix+'.verified.json').write_text(json.dumps({'sha256':model['sha256'],'revision':model['revision'],'mtime_ns':path.stat().st_mtime_ns}))
            with self.lock: self.states[identifier]={'status':'installed','downloaded':model['bytes'],'error':None}
        except Exception as error:
            message=str(error) if isinstance(error,ValueError) else 'Download non riuscito. Controlla rete e spazio libero, poi riprova.'
            with self.lock: self.states[identifier]={'status':'failed','downloaded':partial.stat().st_size if partial.exists() else 0,'error':message}


def models_router(manager,authenticate):
    router=APIRouter(prefix='/api/v1',dependencies=[Depends(authenticate)])
    @router.get('/models')
    def models():
        return {'models':manager.status(),'runtimes':{'transcription':bool(runtime_path('whisper-cli')),'notes':bool(runtime_path('llama-cli')),'enhancement':True,'speakers':True}}
    @router.post('/models/{identifier}/download',status_code=202)
    def download(identifier:str):
        manager.start(identifier)
        return {'id':identifier,'status':'requested'}
    return router

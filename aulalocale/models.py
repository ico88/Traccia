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
}


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
        self.directory.mkdir(parents=True,exist_ok=True)
        partial=path.with_suffix(path.suffix+'.part')
        try:
            offset=partial.stat().st_size if partial.exists() else 0
            if offset > model['bytes']: partial.unlink(); offset=0
            if shutil.disk_usage(self.directory).free < model['bytes']-offset+100*1024*1024:
                raise ValueError('Spazio insufficiente per il modello')
            if offset < model['bytes']:
                url=f"https://huggingface.co/{model['repo']}/resolve/{model['revision']}/{model['file']}"
                headers={'Range':f'bytes={offset}-'} if offset else {}
                with urlopen(Request(url,headers=headers),context=ssl.create_default_context(cafile=certifi.where()),timeout=20) as response:
                    if response.status != 206: offset=0
                    elif response.headers.get('Content-Range','').split('/')[0] != f'bytes {offset}-{model["bytes"]-1}':
                        raise ValueError('Intervallo di download inatteso')
                    with partial.open('ab' if offset else 'wb') as output:
                        while not self.stop.is_set():
                            chunk=response.read(1024*1024)
                            if not chunk: break
                            offset+=len(chunk)
                            if offset>model['bytes']: raise ValueError('Dimensione del modello inattesa')
                            output.write(chunk)
                            with self.lock: self.states[identifier]={'status':'downloading','downloaded':offset,'error':None}
                if self.stop.is_set(): return
            with self.lock: self.states[identifier]={'status':'verifying','downloaded':offset,'error':None}
            digest=hashlib.sha256()
            with partial.open('rb') as downloaded:
                for chunk in iter(lambda:downloaded.read(4*1024*1024),b''): digest.update(chunk)
            if partial.stat().st_size!=model['bytes'] or digest.hexdigest()!=model['sha256']:
                partial.unlink(missing_ok=True)
                raise ValueError('Verifica SHA-256 fallita: riscaricare il modello')
            partial.replace(path)
            path.with_suffix(path.suffix+'.verified.json').write_text(json.dumps({'sha256':model['sha256'],'revision':model['revision'],'mtime_ns':path.stat().st_mtime_ns}))
            with self.lock: self.states[identifier]={'status':'installed','downloaded':model['bytes'],'error':None}
        except Exception as error:
            message=str(error) if isinstance(error,ValueError) else 'Download non riuscito. Controlla rete e spazio libero, poi riprova.'
            with self.lock: self.states[identifier]={'status':'failed','downloaded':partial.stat().st_size if partial.exists() else 0,'error':message}


def models_router(manager,authenticate):
    router=APIRouter(prefix='/api/v1',dependencies=[Depends(authenticate)])
    @router.get('/models')
    def models():
        return {'models':manager.status(),'runtimes':{'transcription':bool(runtime_path('whisper-cli')),'notes':bool(runtime_path('llama-cli'))}}
    @router.post('/models/{identifier}/download',status_code=202)
    def download(identifier:str):
        manager.start(identifier)
        return {'id':identifier,'status':'requested'}
    return router

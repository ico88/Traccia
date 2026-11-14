"""Local desktop launcher; native app bundle opens the same interface in a browser."""
from pathlib import Path
from threading import Thread
import argparse
import secrets
import socket
import sys
import time
import webbrowser

import uvicorn
from aulalocale.app import create_app


def main():
    if '--internal-denoise' in sys.argv:
        if sys.stdout is None:sys.stdout=open(1,'w',buffering=1,closefd=False)
        if sys.stderr is None:sys.stderr=open(2,'w',buffering=1,closefd=False)
        from aulalocale.ai_denoise import main as denoise
        denoise(sys.argv[sys.argv.index('--internal-denoise')+1:])
        return
    parser=argparse.ArgumentParser(description='AulaLocale local desktop launcher')
    parser.add_argument('--data',type=Path)
    parser.add_argument('--no-browser',action='store_true')
    args=parser.parse_args()
    root=args.data or (Path.home()/'Library'/'Application Support'/'AulaLocale' if sys.platform=='darwin' else Path.home()/'.local'/'share'/'aulalocale')
    root.mkdir(parents=True,exist_ok=True)
    if sys.stdout is None:sys.stdout=(root/'application.log').open('a',buffering=1)
    if sys.stderr is None:sys.stderr=sys.stdout
    token,nonce=secrets.token_urlsafe(32),secrets.token_urlsafe(32)
    # Bind first to avoid a port race; keep the server reachable only on loopback.
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(128)
    port=listener.getsockname()[1]
    server=None
    def shutdown():
        server.should_exit=True
    application=create_app(root,token,bootstrap_nonce=nonce,shutdown_callback=shutdown)
    server=uvicorn.Server(uvicorn.Config(application,host='127.0.0.1',port=port,log_level='warning'))
    if not args.no_browser:
        def open_window():
            deadline=time.monotonic()+30
            while not server.started and time.monotonic()<deadline:
                time.sleep(.1)
            if server.started:webbrowser.open(f'http://127.0.0.1:{port}/#access={nonce}')
        Thread(target=open_window,daemon=True).start()
    else:
        print(f'AulaLocale: http://127.0.0.1:{port}/',flush=True)
        print('Access token: '+token,flush=True)
    try:server.run(sockets=[listener])
    finally:listener.close()

if __name__=='__main__':main()

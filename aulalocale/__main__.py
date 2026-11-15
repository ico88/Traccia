"""Local desktop launcher; Mac uses a dedicated WebKit window; server/browser mode remains explicit."""
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
from aulalocale.preferences import DesktopPreferences




def main():
    internal=next((flag for flag in ['--internal-denoise','--internal-speakers','--internal-pdf'] if flag in sys.argv),None)
    if internal:
        if sys.stdout is None:sys.stdout=open(1,'w',buffering=1,closefd=False)
        if sys.stderr is None:sys.stderr=open(2,'w',buffering=1,closefd=False)
        if internal=='--internal-denoise':from aulalocale.ai_denoise import main as run_worker
        elif internal=='--internal-speakers':from aulalocale.ai_speakers import main as run_worker
        else:from aulalocale.pdf_import import main as run_worker
        run_worker(sys.argv[sys.argv.index(internal)+1:])
        return
    parser=argparse.ArgumentParser(description='Traccia local desktop launcher')
    parser.add_argument('--data',type=Path)
    parser.add_argument('--no-browser',action='store_true',help='Headless local service')
    parser.add_argument('--browser',action='store_true',help='Open the external browser instead of the Mac app window')
    args=parser.parse_args()
    root=args.data or (Path.home()/'Library'/'Application Support'/'AulaLocale' if sys.platform=='darwin' else Path.home()/'.local'/'share'/'aulalocale')
    root.mkdir(parents=True,exist_ok=True)
    if sys.stdout is None:sys.stdout=(root/'application.log').open('a',buffering=1)
    if sys.stderr is None:sys.stderr=sys.stdout
    token,nonce=secrets.token_urlsafe(32),secrets.token_urlsafe(32)
    # Bind first to avoid a port race; keep the server reachable only on loopback.
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(128)
    port=listener.getsockname()[1]
    server=None;window=None
    def shutdown():
        server.should_exit=True
        if window is not None:window.destroy()
    application=create_app(root,token,bootstrap_nonce=nonce,shutdown_callback=shutdown)
    server=uvicorn.Server(uvicorn.Config(application,host='127.0.0.1',port=port,log_level='warning'))
    if sys.platform=='darwin' and not args.no_browser and not args.browser:
        import webview
        service=Thread(target=lambda:server.run(sockets=[listener]),name='local-service',daemon=True)
        service.start()
        try:
            deadline=time.monotonic()+30
            while not server.started and service.is_alive() and time.monotonic()<deadline:time.sleep(.05)
            if not server.started:raise RuntimeError('Il servizio locale non si è avviato. Controlla il log dell’app.')
            preferences=DesktopPreferences(root)
            window=webview.create_window('Traccia',f'http://127.0.0.1:{port}/#access={nonce}&language={preferences.language()}',width=1280,height=860,min_size=(880,620),background_color='#f8f9f6')
            window.events.closed += lambda: setattr(server,'should_exit',True)
            webview.settings['ALLOW_DOWNLOADS']=True
            webview.start(private_mode=True,debug=False)
        finally:
            server.should_exit=True;service.join(timeout=15);listener.close()
        return
    if not args.no_browser:
        def open_window():
            deadline=time.monotonic()+30
            while not server.started and time.monotonic()<deadline:
                time.sleep(.1)
            if server.started:webbrowser.open(f'http://127.0.0.1:{port}/#access={nonce}')
        Thread(target=open_window,daemon=True).start()
    else:
        print(f'Traccia: http://127.0.0.1:{port}/',flush=True)
        print('Access token: '+token,flush=True)
    try:server.run(sockets=[listener])
    finally:listener.close()

if __name__=='__main__':main()

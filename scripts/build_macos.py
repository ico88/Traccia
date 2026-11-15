"""Build a development .app. Requires prebuilt Apple Silicon runtimes and PyInstaller."""
from pathlib import Path
import argparse
import platform
import shutil
import tempfile
import subprocess
import sys
import plistlib

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--dmg',action='store_true');args=parser.parse_args()
    if sys.platform!='darwin' or platform.machine()!='arm64':raise SystemExit('Build on an Apple Silicon Mac')
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    binaries=[ROOT/'runtimes'/name for name in ['whisper-cli','llama-cli','ffmpeg']]
    if not all(path.is_file() for path in binaries):raise SystemExit('Run scripts/setup_runtimes.py first')
    command=[sys.executable,'-m','PyInstaller','--noconfirm','--windowed','--onedir','--name','Traccia','--icon',str(ROOT/'branding'/'Traccia.icns'),
             '--osx-bundle-identifier','it.aulalocale.desktop','--distpath',str(output),'--workpath',str(ROOT/'work'/'pyinstaller'),
             '--additional-hooks-dir',str(ROOT/'scripts'/'hooks'),'--specpath',str(ROOT/'work'),'--paths',str(ROOT),
             '--hidden-import','webview.platforms.cocoa','--hidden-import','WebKit','--hidden-import','AppKit','--hidden-import','Foundation','--collect-all','webview','--collect-all','mutagen','--collect-all','sherpa_onnx','--collect-all','uvicorn',
             '--add-data',f'{ROOT / "aulalocale" / "web"}:aulalocale/web']
    for dependency in ['mutagen','imageio-ffmpeg','Pillow','fastapi','uvicorn','starlette','pydantic','certifi','numpy','sherpa-onnx','sherpa-onnx-core','pywebview','pyobjc-core','pyobjc-framework-Cocoa','pyobjc-framework-WebKit']:
        command+=['--copy-metadata',dependency]
    if (ROOT/'runtimes'/'licenses').is_dir():command+=['--add-data',f'{ROOT / "runtimes" / "licenses"}:runtimes/licenses']
    for binary in binaries:command+=['--add-binary',f'{binary}:runtimes']
    subprocess.run([sys.executable,str(ROOT/'scripts'/'export_notices.py'),'--output',str(ROOT/'work'/'third-party-notices')],check=True)
    command+=['--add-data',f'{ROOT / "work" / "third-party-notices"}:third-party-notices','--add-data',f'{ROOT / "LICENSE"}:LICENSE']
    command.append(str(ROOT/'scripts'/'desktop_entry.py'))
    subprocess.run(command,check=True)
    bundle=output/'Traccia.app'
    info=bundle/'Contents'/'Info.plist'
    data=plistlib.loads(info.read_bytes());data.update({'CFBundleShortVersionString':'0.10.0','CFBundleVersion':'11','CFBundleDisplayName':'Traccia','NSMicrophoneUsageDescription':'Traccia usa il microfono solo quando avvii una registrazione della lezione. L’audio resta sul tuo dispositivo.','NSHighResolutionCapable':True,'NSAppTransportSecurity':{'NSAllowsLocalNetworking':True}})
    info.write_bytes(plistlib.dumps(data))
    # Finder/iCloud may reattach these two packaging attributes while signing.
    # Retry only that specific error; never clear quarantine or bypass verification.
    for attempt in range(3):
        for attribute in ['com.apple.FinderInfo','com.apple.ResourceFork']:
            subprocess.run(['xattr','-dr',attribute,str(bundle)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
        signed=subprocess.run(['codesign','--force','--deep','--sign','-',str(bundle)],capture_output=True,text=True)
        if signed.returncode==0:break
        if 'resource fork, Finder information' not in signed.stderr or attempt==2:
            raise RuntimeError(signed.stderr)
    for attribute in ['com.apple.FinderInfo','com.apple.ResourceFork']:
        subprocess.run(['xattr','-dr',attribute,str(bundle)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
    subprocess.run(['codesign','--verify','--deep','--strict',str(bundle)],check=True)
    if args.dmg:
        with tempfile.TemporaryDirectory(prefix='aulalocale-dmg-') as temporary:
            stage=Path(temporary)
            shutil.copytree(bundle,stage/'Traccia.app',symlinks=True)
            (stage/'Applicazioni').symlink_to('/Applications')
            (stage/'LEGGIMI.txt').write_text('Traccia 0.10 - build di sviluppo Apple Silicon.\nTrascina Traccia in Applicazioni e avviala. I modelli si scaricano dalla schermata Modelli locali.\nBuild ad hoc non notarizzata, destinata ai test locali. Nessuna registrazione inclusa.\nSorgenti: https://github.com/ico88/Traccia/tree/sviluppo\n')
            subprocess.run(['hdiutil','create','-ov','-volname','Traccia','-srcfolder',str(stage),'-format','UDZO',str(output/'Traccia-0.10-AppleSilicon-sviluppo.dmg')],check=True)
    if (output/'Traccia').is_dir():shutil.rmtree(output/'Traccia')
    print('Development .app built. Distribution signing and notarization are not included.')

if __name__=='__main__':main()

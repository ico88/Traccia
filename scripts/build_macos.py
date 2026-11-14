"""Build a development .app. Requires prebuilt Apple Silicon runtimes and PyInstaller."""
from pathlib import Path
import argparse
import platform
import shutil
import tempfile
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--dmg',action='store_true');args=parser.parse_args()
    if sys.platform!='darwin' or platform.machine()!='arm64':raise SystemExit('Build on an Apple Silicon Mac')
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    binaries=[ROOT/'runtimes'/name for name in ['whisper-cli','llama-cli']]
    if not all(path.is_file() for path in binaries):raise SystemExit('Run scripts/setup_runtimes.py first')
    command=[sys.executable,'-m','PyInstaller','--noconfirm','--windowed','--onedir','--name','AulaLocale',
             '--osx-bundle-identifier','it.aulalocale.desktop','--distpath',str(output),'--workpath',str(ROOT/'work'/'pyinstaller'),
             '--specpath',str(ROOT/'work'),'--paths',str(ROOT),
             '--collect-all','imageio_ffmpeg','--collect-all','mutagen','--collect-all','sherpa_onnx','--collect-all','uvicorn',
             '--add-data',f'{ROOT / "aulalocale" / "web"}:aulalocale/web']
    for dependency in ['mutagen','imageio-ffmpeg','Pillow','fastapi','uvicorn','starlette','pydantic','certifi','numpy','sherpa-onnx','sherpa-onnx-core']:
        command+=['--copy-metadata',dependency]
    if (ROOT/'runtimes'/'licenses').is_dir():command+=['--add-data',f'{ROOT / "runtimes" / "licenses"}:runtimes/licenses']
    for binary in binaries:command+=['--add-binary',f'{binary}:runtimes']
    command.append(str(ROOT/'scripts'/'desktop_entry.py'))
    subprocess.run(command,check=True)
    bundle=output/'AulaLocale.app'
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
            shutil.copytree(bundle,stage/'AulaLocale.app',symlinks=True)
            (stage/'Applicazioni').symlink_to('/Applications')
            (stage/'LEGGIMI.txt').write_text('AulaLocale 0.8 - build di sviluppo Apple Silicon.\nTrascina AulaLocale in Applicazioni e avviala. I modelli si scaricano dalla schermata Modelli locali.\nBuild ad hoc non notarizzata, destinata ai test locali. Nessuna registrazione inclusa.\nSorgenti: https://github.com/ico88/aulalocale/tree/sviluppo\n')
            subprocess.run(['hdiutil','create','-ov','-volname','AulaLocale','-srcfolder',str(stage),'-format','UDZO',str(output/'AulaLocale-0.8-AppleSilicon-sviluppo.dmg')],check=True)
    if (output/'AulaLocale').is_dir():shutil.rmtree(output/'AulaLocale')
    print('Development .app built. Distribution signing and notarization are not included.')

if __name__=='__main__':main()

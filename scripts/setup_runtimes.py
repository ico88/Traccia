"""Developer build helper. Only fetches the two pinned official repositories."""
from pathlib import Path
import argparse
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
SOURCES=[('whisper','https://github.com/ggml-org/whisper.cpp.git','v1.9.5','d1be6fde11ac6e0407606b4e42fe72d34add8037','whisper-cli'),
         ('llama','https://github.com/ggml-org/llama.cpp.git','v1.0.0','b1b770d90d94cad9e9ea5b993bdbc383a522fb28','llama-cli')]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--jobs',type=int,default=4);args=parser.parse_args()
    if not 1<=args.jobs<=32:parser.error('--jobs must be between 1 and 32')
    cmake=shutil.which('cmake')
    if not cmake:raise SystemExit('Install cmake in the development environment: python -m pip install cmake')
    target=ROOT/'runtimes';target.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='aulalocale-build-') as temp:
        for name,url,tag,commit,binary in SOURCES:
            source=Path(temp)/name
            subprocess.run(['git','clone','--depth','1','--branch',tag,url,str(source)],check=True)
            actual=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
            if actual!=commit:raise SystemExit('Pinned source revision mismatch; build aborted')
            subprocess.run([cmake,'-S',str(source),'-B',str(source/'build'),'-DCMAKE_BUILD_TYPE=Release','-DBUILD_SHARED_LIBS=OFF','-DLLAMA_OPENSSL=OFF'],check=True)
            subprocess.run([cmake,'--build',str(source/'build'),'--target',binary,'-j',str(args.jobs)],check=True)
            shutil.copy2(source/'build'/'bin'/binary,target/binary)
            licenses=target/'licenses';licenses.mkdir(exist_ok=True)
            shutil.copy2(source/'LICENSE',licenses/(name+'.cpp-LICENSE'))
    print('Local native runtimes installed in runtimes/. Model downloads are separate.')

if __name__=='__main__':main()

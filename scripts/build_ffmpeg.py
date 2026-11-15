"""Build a pinned, audio-only FFmpeg and LAME; preserve exact corresponding sources."""
from pathlib import Path
import argparse,hashlib,os,shutil,subprocess,tarfile,urllib.request,ssl,sys
import certifi
ROOT=Path(__file__).resolve().parents[1]
SOURCES=[('lame','https://downloads.sourceforge.net/project/lame/lame/3.100/lame-3.100.tar.gz','ddfe36cab873794038ae2c1210557ad34857a4b6bdc515785d1da9e175b1da1e'),('ffmpeg','https://ffmpeg.org/releases/ffmpeg-9.0.tar.xz','7f607a00dd0d28a729d5a4811205812eef01cf6ef6155025febb6f36a9062d52')]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--sources',type=Path,required=True);p.add_argument('--jobs',type=int,default=4);a=p.parse_args()
 if not 1<=a.jobs<=16:p.error('jobs must be 1..16')
 a.sources=a.sources.resolve();a.sources.mkdir(exist_ok=True,parents=True)
 build=ROOT/'work'/'ffmpeg-build';build.mkdir(parents=True,exist_ok=True);prefix=build/'prefix';prefix.mkdir(exist_ok=True)
 for name,url,digest in SOURCES:
  archive=a.sources/url.rsplit('/',1)[1]
  if not archive.exists():
   with urllib.request.urlopen(url,context=ssl.create_default_context(cafile=certifi.where())) as r,archive.open('wb') as out:shutil.copyfileobj(r,out)
  if hashlib.sha256(archive.read_bytes()).hexdigest()!=digest:raise ValueError('Source checksum mismatch: '+name)
  with tarfile.open(archive) as t:t.extractall(build,filter='data')
 lame=build/'lame-3.100';ffmpeg=build/'ffmpeg-9.0'
 env={**os.environ,'CFLAGS':'-O2','LDFLAGS':f'-L{prefix}/lib','CPPFLAGS':f'-I{prefix}/include'}
 commands=[(lame,['./configure',f'--prefix={prefix}','--disable-shared','--enable-static','--disable-frontend']),
 (lame,['make','-j',str(a.jobs)]),(lame,['make','install']),
 (ffmpeg,['./configure',f'--prefix={prefix}','--disable-everything','--disable-autodetect','--disable-network','--disable-doc','--disable-debug','--disable-shared','--enable-static','--enable-ffmpeg','--enable-libmp3lame',f'--extra-cflags=-I{prefix}/include',f'--extra-ldflags=-L{prefix}/lib','--enable-protocol=file,pipe','--enable-demuxer=mp3,mov,wav,flac,aac','--enable-parser=mpegaudio,aac,flac','--enable-decoder=mp3,mp3float,aac,flac,pcm_s16le,pcm_s24le,pcm_s32le,pcm_f32le,pcm_f64le,alac','--enable-encoder=pcm_s16le,libmp3lame,aac,flac','--enable-muxer=mp3,wav,null,ipod,adts,flac','--enable-filter=highpass,afftdn,dynaudnorm,alimiter,loudnorm,aresample,aformat,anull,atrim,asetpts,volume,abuffer,abuffersink,arealtime']),
 (ffmpeg,['make','-j',str(a.jobs)])]
 import json
 (a.sources/'build-commands.json').write_text(json.dumps({'commands':[[str(cwd.relative_to(build)),[arg.replace(str(build),'<BUILD_ROOT>') for arg in cmd]] for cwd,cmd in commands],'environment':{'CFLAGS':'-O2','prefix':'ffmpeg-build/prefix'},'modifications':'No source changes; configuration only.','source_hashes':{url.rsplit('/',1)[1]:digest for _,url,digest in SOURCES}},indent=2))
 for cwd,cmd in commands:subprocess.run(cmd,cwd=cwd,env=env,check=True)
 target=ROOT/'runtimes';target.mkdir(exist_ok=True);shutil.copy2(ffmpeg/'ffmpeg',target/'ffmpeg')
 license_dir=target/'licenses';license_dir.mkdir(exist_ok=True)
 for source,dest in [(ffmpeg/'COPYING.LGPLv2.1','ffmpeg-LGPL-2.1.txt'),(lame/'COPYING','lame-LGPL.txt')]:shutil.copy2(source,license_dir/dest)
 print('Built audio-only FFmpeg; retain --sources directory alongside the released binary.')
if __name__=='__main__':main()

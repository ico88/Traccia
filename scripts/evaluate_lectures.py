"""Private, reproducible multi-lecture ASR / denoising / chunk-boundary evaluation.

References must be manually reviewed and explicitly marked reference_reviewed=true.
This script never downloads models, modifies inputs or writes into an existing output.
"""
from pathlib import Path
import argparse,hashlib,json,os,platform,subprocess,sys,time,wave
from compare_asr import score,normalized
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from aulalocale.models import CATALOG
from aulalocale.ai_denoise import enhance
import imageio_ffmpeg

def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for data in iter(lambda:f.read(4*1024**2),b''):h.update(data)
 return h.hexdigest()

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--models',type=Path,required=True);p.add_argument('--whisper',type=Path,required=True);a=p.parse_args()
 if a.output.exists():p.error('Choose a new output directory')
 config=json.loads(a.manifest.read_text());cases=config['samples'];ids=[c['id'] for c in cases]
 if len(ids)!=len(set(ids)) or any(not x.replace('-','').replace('_','').isalnum() for x in ids):p.error('Sample IDs must be unique safe identifiers')
 for c in cases:
  if not 0<=c['start'] or not 5<=c['duration']<=120:p.error('Invalid sample time range')
 for key in ['whisper-turbo','gtcrn']:
  if digest(a.models/CATALOG[key]['file'])!=CATALOG[key]['sha256']:p.error('Model checksum mismatch: '+key)
 a.output.mkdir(parents=True);ffmpeg=imageio_ffmpeg.get_ffmpeg_exe();rows=[];sources={};refs={}
 report={'platform':platform.platform(),'machine':platform.machine(),'models':{k:CATALOG[k]['sha256'] for k in ['whisper-turbo','gtcrn']},'gtcrn_strength':.7,'language':config.get('language','it'),'results':rows,'sources':sources,'accuracy':'No accuracy scores without explicitly human-reviewed references. Timings include fresh model loading.'}
 def run(command,log):
  with log.open('w') as f:subprocess.run(command,stdout=f,stderr=f,check=True,timeout=240,env={**os.environ,'HF_HUB_OFFLINE':'1'})
 for c in cases:
  source=Path(c['audio']).expanduser();source=source if source.is_absolute() else a.manifest.parent/source
  source=source.resolve()
  if str(source) not in sources:sources[str(source)]=digest(source)
  prefix=a.output/c['id'];original=prefix.with_suffix('.wav');wet=a.output/(c['id']+'-gtcrn.wav')
  run([ffmpeg,'-v','error','-nostdin','-ss',str(c['start']),'-i',str(source),'-t',str(c['duration']),'-ac','1','-ar','16000','-c:a','pcm_s16le',str(original)],prefix.with_suffix('.decode.log'))
  with wave.open(str(original)) as w:
   actual=w.getnframes()/w.getframerate()
   if abs(actual-c['duration'])>.1:raise ValueError('Sample extends past source end: '+c['id'])
  started=time.monotonic();enhance(original,wet,a.models/CATALOG['gtcrn']['file'],.7);denoise_seconds=time.monotonic()-started
  reference=c.get('reference','').strip() if c.get('reference_reviewed') is True else ''
  refs[c['id']]={'reference':'','reference_reviewed':False,'start':c['start'],'duration':c['duration'],'audio':str(source),'instructions':'Listen and enter a corrected reference, without looking at model hypotheses. Then set reference_reviewed=true.'}
  for condition,audio in [('normalized',original),('gtcrn-normalized',wet)]:
   prepared=a.output/(c['id']+'-'+condition+'.wav')
   run([ffmpeg,'-v','error','-nostdin','-i',str(audio),'-af','loudnorm=I=-20:TP=-2:LRA=11','-ar','16000','-ac','1','-c:a','pcm_s16le',str(prepared)],prefix.with_suffix('.prepare.log'))
   splits=[None]
   boundary=c.get('boundary')
   if boundary is not None and c['start']<boundary<c['start']+actual:splits.append(boundary-c['start'])
   for split in splits:
    text=[];elapsed=0;intervals=[(0,actual)] if split is None else [(0,split),(split,actual-split)]
    for number,(start,length) in enumerate(intervals):
     name=a.output/(c['id']+'-'+condition+('-whole' if split is None else '-split')+'-'+str(number));clip=name.with_suffix('.wav')
     run([ffmpeg,'-v','error','-nostdin','-ss',str(start),'-i',str(prepared),'-t',str(length),'-c:a','pcm_s16le',str(clip)],name.with_suffix('.decode.log'))
     begin=time.monotonic();run([str(a.whisper.resolve()),'-m',str((a.models/CATALOG['whisper-turbo']['file']).resolve()),'-f',str(clip.resolve()),'-l',config.get('language','it'),'-t','4','-oj','-of',str(name.resolve()),'-np','-sns','-ml','180','-sow'],name.with_suffix('.log'));elapsed+=time.monotonic()-begin
     data=json.loads(name.with_suffix('.json').read_text());text.append(' '.join(part['text'].strip() for part in data['transcription']))
    hypothesis=' '.join(text).strip();row={'sample':c['id'],'condition':condition,'boundary_split':split is not None,'start':c['start'],'duration':actual,'wall_seconds':elapsed,'real_time_factor':elapsed/actual,'denoise_seconds':denoise_seconds,'text':hypothesis,'scores':score(reference,hypothesis) if reference else None,'term_mentions':{term:normalized(term) in normalized(hypothesis) for term in c.get('terms',[])}}
    rows.append(row);(a.output/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(c['id'],condition,'split' if split else 'whole',round(elapsed,2),'seconds; human reference',bool(reference),flush=True)
 (a.output/'reference-template.json').write_text(json.dumps({'samples':[{'id':key,**value} for key,value in refs.items()]},ensure_ascii=False,indent=2))
 print('Complete. No personal audio or text should be committed to Git.')
if __name__=='__main__':main()

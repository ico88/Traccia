"""Score existing private hypotheses after human review; never rerun inference."""
import argparse,json
from pathlib import Path
try:from .compare_asr import score,normalized
except ImportError:from compare_asr import score,normalized

def score_report(report,review):
 entries=review['samples'];ids=[x['id'] for x in entries]
 if len(set(ids))!=len(ids):raise ValueError('Duplicate review IDs')
 known={r['sample'] for r in report['results']}
 if not set(ids)<=known:raise ValueError('Unknown sample in reference data')
 references={x['id']:x['reference'].strip() for x in entries if x.get('reference_reviewed') is True and x.get('reference','').strip()};groups={}
 for row in report['results']:
  reference=references.get(row['sample']);row['scores']=score(reference,row['text']) if reference else None
  if not reference:continue
  chars=len(normalized(reference).replace(' ',''));key=row['condition']+(' / split' if row['boundary_split'] else ' / whole');g=groups.setdefault(key,{'word_errors':0,'reference_words':0,'character_errors':0,'reference_characters':0,'samples':0});s=row['scores'];g['word_errors']+=round(s['wer']*s['reference_words']);g['reference_words']+=s['reference_words'];g['character_errors']+=round(s['cer']*chars);g['reference_characters']+=chars;g['samples']+=1
 for g in groups.values():g.update(wer=g['word_errors']/g['reference_words'],cer=g['character_errors']/g['reference_characters'])
 listening={}
 allowed={r['condition'] for r in report['results']}
 for sample in entries:
  for label,condition in sample.get('conditions',{}).items():
   if condition not in allowed:raise ValueError('Unknown listening condition')
   for metric,rating in sample.get('ratings',{}).get(label,{}).items():
    if rating is None:continue
    if metric not in ('clarity','noise_control','naturalness') or type(rating) is not int or not 1<=rating<=5:raise ValueError('Ratings must be integers 1..5')
    record=listening.setdefault(condition,{}).setdefault(metric,{'count':0,'sum':0});record['count']+=1;record['sum']+=rating
 for metrics in listening.values():
  for record in metrics.values():record['mean']=record['sum']/record['count']
 report['listening_ratings']=listening;report['aggregate_scores']=groups;report['human_reviewed_samples']=len(references);return report

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--results',type=Path,required=True);p.add_argument('--review',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():p.error('Choose a new output file')
 result=score_report(json.loads(a.results.read_text()),json.loads(a.review.read_text()));a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2));print('Scored',result['human_reviewed_samples'],'human-reviewed samples; other samples remain unmeasured.')
if __name__=='__main__':main()

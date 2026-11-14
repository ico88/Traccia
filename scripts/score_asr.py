"""Score an existing private comparison with human reference text, without running AI again."""
import argparse
import json
from pathlib import Path
from compare_asr import score


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results',type=Path,required=True)
    parser.add_argument('--references',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('Choose a new output file')
    data=json.loads(args.results.read_text());references=json.loads(args.references.read_text())
    for row in data['results']:
        reference=references.get(row['sample'],'')
        row['scores']=score(reference,row['text']) if reference.strip() else None
    args.output.write_text(json.dumps(data,ensure_ascii=False,indent=2))
    print('Scored',sum(row['scores'] is not None for row in data['results']),'hypotheses; empty references remain unmeasured.')


if __name__=='__main__':main()

"""Run from the repository root: python -m scripts.evaluate_knowledge."""
import argparse
import json
from pathlib import Path
from app.services.knowledge_evaluation import evaluate_retrieval


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path)
    args=parser.parse_args();report=evaluate_retrieval()
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v['metrics'] for k,v in report['variants'].items()},ensure_ascii=False,indent=2))

if __name__=='__main__':main()

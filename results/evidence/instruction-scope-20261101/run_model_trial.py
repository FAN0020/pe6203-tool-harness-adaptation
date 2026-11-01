"""Use the supplied backup billing credential for one frozen, unchanged CLI run."""
import argparse
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='results/raw/instruction-scope-pilot-20261101')
    args=parser.parse_args()
    key=os.environ.get('OPENROUTER_API_KEY_BACKUP')
    if not key:raise ValueError('Configured backup credential is required')
    os.environ['AGENT_API_KEY']=key
    os.environ['JUDGE_API_KEY']=key
    os.chdir(ROOT)
    sys.argv=['pe6203','experiment','search','run','--output',str(ROOT/args.output)]
    from pe6203.cli import main as cli_main
    return cli_main()

if __name__=='__main__':raise SystemExit(main())

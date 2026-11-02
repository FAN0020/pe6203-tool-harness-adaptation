"""Use the supplied backup billing credential for one frozen, unchanged CLI run."""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="results/raw/relation-witness-basis-pilot-20261102")
    args = parser.parse_args()
    key = os.environ.get("OPENROUTER_API_KEY_BACKUP")
    if not key:
        raise ValueError("Configured backup credential is required")
    os.environ["AGENT_API_KEY"] = key
    os.environ["JUDGE_API_KEY"] = key
    os.chdir(ROOT)
    sys.argv = ["pe6203", "experiment", "search", "run", "--output", str(ROOT / args.output)]
    import contextlib

    from pe6203.cli import main as cli_main

    with (ROOT / "results/raw/relation-witness-basis-pilot-20261102/runner-output.log").open(
        "w"
    ) as log:
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            result = cli_main()
    print("Frozen trial process finished; inspect blinded packets before scores.", flush=True)
    return result


if __name__ == "__main__":
    raise SystemExit(main())

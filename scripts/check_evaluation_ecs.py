"""Compare all 1,000 integer TF triplets with the pinned upstream ECS function."""

import argparse
import importlib.util
import itertools
import json
import sys
from pathlib import Path

from pe6203.evaluation import digest, ecs

REFERENCE_SHA256 = "7ac5164cf66149e2acee7369f1bb590e6ea153404aa786a6493860bc2a6a8a45"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-file", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    path = Path(args.upstream_file).resolve()
    if digest(path) != REFERENCE_SHA256:
        raise ValueError("Use evolutionary_volatility.py from pinned commit 888c779a")
    spec = importlib.util.spec_from_file_location("upstream_ecs_reference", path)
    reference = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = reference
    spec.loader.exec_module(reference)
    errors = []
    for values in itertools.product(range(1, 11), repeat=3):
        row = reference._compute_row("fixture", *values)
        errors.append(abs(ecs(values) - (row.mean - row.stdev)))
    result = {
        "reference_commit": "888c779a0fe735f612ca62bdd1fdd7c9e6bf8701",
        "reference_path": "src/custom/analysis/answer/evolutionary_volatility.py",
        "reference_file_sha256": digest(path),
        "triplets_checked": len(errors),
        "maximum_absolute_error": max(errors),
        "passed": max(errors) < 1e-12,
        "scope": "integer-score software parity check; not benchmark runs",
    }
    with Path(args.output).open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

"""Correct the A1 entry's redundant preflight without expanding any frozen limit.

The original A1 manifest/code remains unchanged and still enforces its explicit
approval. This wrapper only reuses the two successful frozen preflight receipts.
"""

import hashlib
import importlib.util
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_reusable_preflight(plan, output, spec):
    output = Path(output)
    if (
        sha(output / "plan.json") != spec["plan_sha256"]
        or json.loads((output / "plan.json").read_text()) != plan
    ):
        raise ValueError("Frozen plan differs from preflight-reuse evidence")
    names = {str(p.relative_to(output)) for p in (output / "preflight").glob("*.json")}
    if names != set(spec["preflight_files"]):
        raise ValueError("Preflight inventory changed")
    records = []
    for name, expected in spec["preflight_files"].items():
        if sha(output / name) != expected:
            raise ValueError("Preflight evidence changed")
        records.extend(json.loads((output / name).read_text()))
    if (
        plan.get("max_preflight_calls") != 2
        or len(records) != 2
        or {r["role"] for r in records} != {"agent", "judge"}
    ):
        raise ValueError("Frozen two-role preflight result is incomplete")
    settled = {
        r["response_id"]
        for r in json.loads((output / "spend-ledger.json").read_text())["requests"]
        if r["status"] == "settled"
    }
    for r in records:
        expected = plan["config"][r["role"]]["model"]
        if (
            r["status"] != "reachable"
            or r["model"] != expected
            or r["actual_model"] != expected
            or r["actual_provider"] != "DigitalOcean"
            or r["response_id"] not in settled
        ):
            raise ValueError("Frozen preflight result is not a matching settled success")
    return [r["response_id"] for r in records]


def main():
    from pe6203 import experiment

    here = Path(__file__).resolve().parent
    root = here.parents[2]
    path = here / "preflight-reuse-addendum.json"
    if sha(path) != (here / "preflight-reuse-addendum.sha256").read_text().strip():
        raise ValueError("Preflight-reuse addendum changed")
    spec = json.loads(path.read_text())
    for name, expected in spec["frozen_files"].items():
        if sha(root / name) != expected:
            raise ValueError(f"Preflight-reuse implementation changed: {name}")
    output = root / spec["output"]
    verify_reusable_preflight(json.loads((output / "plan.json").read_text()), output, spec)
    module_spec = importlib.util.spec_from_file_location(
        "approved_original_a1", here / "accounting_continuation.py"
    )
    a1 = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(a1)
    original = experiment.availability_preflight

    def reuse(plan, target):
        if Path(target).resolve() != output.resolve():
            return original(plan, target)
        ids = verify_reusable_preflight(plan, target, spec)
        print(
            f"Reused {len(ids)} frozen successful preflight receipts; no extra preflight request.",
            flush=True,
        )

    experiment.availability_preflight = reuse
    try:
        a1.main()
    finally:
        experiment.availability_preflight = original


if __name__ == "__main__":
    main()

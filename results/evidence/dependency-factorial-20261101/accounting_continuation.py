"""Proposed, explicitly disclosed A1 infrastructure continuation for one diagnostic.

The frozen source modules, plan, policy, unknown row and judge outcomes stay intact.
Only the approved pre-existing accounting stop is interpreted differently in this
process. Every new unknown charge or other stop retains the original stop behavior.
This is NOT settlement of the unknown charge and NOT a new experimental strategy.
Do not execute --run without the separately recorded failure-policy authorization.
"""

import argparse
import hashlib
import json
from contextlib import contextmanager
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def allowed(data, spec):
    """No new unknown, pending, capped or unexpected-provider stop is waived."""
    count = spec["approved_prefix_count"]
    requests = data.get("requests", [])
    return (
        data.get("policy") == spec["ledger_policy"]
        and data["policy"].get("limit_usd") is None
        and data.get("blocked") is True
        and data.get("stop_reason") == "unknown_charge"
        and len(requests) >= count
        and digest(requests[:count]) == spec["approved_prefix_sha256"]
        and [i for i, row in enumerate(requests) if row["status"] != "settled"]
        == [spec["unknown_index"]]
    )


@contextmanager
def overlay(spec):
    from pe6203 import benchmark, experiment, spend_guard

    ledger_path, run_path, outcome_path = (
        Path(spec[k]).resolve() for k in ("ledger", "run", "outcome")
    )
    original_ledger = spend_guard.ledger
    original_stopped = experiment.spend_stopped
    original_read = benchmark.read_json
    original_pending = experiment.pending_judging

    @contextmanager
    def scoped_ledger(policy):
        with original_ledger(policy) as data:
            exception = Path(policy["ledger"]).resolve() == ledger_path and allowed(data, spec)
            if exception:
                data["blocked"] = False
            try:
                yield data
            finally:
                # Preserve the on-disk stop marker and the complete unknown record.
                # A different/new stop is never cleared by this continuation.
                if exception:
                    data["blocked"] = True

    def scoped_stopped(policy):
        stopped = original_stopped(policy)
        if not stopped or not policy or Path(policy["ledger"]).resolve() != ledger_path:
            return stopped
        return not allowed(original_read(ledger_path), spec)

    def scoped_read(path):
        value = original_read(path)
        if Path(path).resolve() == outcome_path:
            if sha(path) != spec["outcome_sha256"]:
                raise ValueError("Approved original judge outcome changed")
            return {
                **value,
                "failure_category": "model_transport",
                "retryable": True,
                "continuation": {
                    "id": spec["id"],
                    "original_sha256": spec["outcome_sha256"],
                    "reason": "Original timeout retained; accounting-stop wrapper classification overridden only for bounded judge recovery.",
                },
            }
        return value

    def scoped_pending(directory, config):
        result = Path(directory) / "result.json"
        if (
            Path(directory).resolve() == run_path
            and result.exists()
            and sha(result) == spec["initial_result_sha256"]
        ):
            return True
        return original_pending(directory, config)

    spend_guard.ledger = scoped_ledger
    experiment.spend_stopped = scoped_stopped
    benchmark.read_json = scoped_read
    experiment.pending_judging = scoped_pending
    try:
        yield
    finally:
        spend_guard.ledger = original_ledger
        experiment.spend_stopped = original_stopped
        benchmark.read_json = original_read
        experiment.pending_judging = original_pending


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    root = here.parents[2]
    manifest_path = here / "continuation-a1.json"
    if sha(manifest_path) != (here / "continuation-a1.sha256").read_text().strip():
        raise ValueError("Continuation manifest changed")
    spec = json.loads(manifest_path.read_text())
    for name, expected in spec["frozen_files"].items():
        if sha(root / name) != expected:
            raise ValueError(f"Continuation input changed: {name}")
    from pe6203 import experiment
    from pe6203.benchmark import read_json

    output = root / spec["output"]
    if not allowed(read_json(spec["ledger"]), spec):
        raise ValueError("Stop is outside the single approved unknown-charge exception")
    experiment.check_plan(root, output, read_json(output / "plan.json"))
    print(
        "Continuation inputs verified; original knowledge, source and schedule unchanged.",
        flush=True,
    )
    if not args.run:
        print(
            "Read-only check; no model or native calls. Failure-policy approval remains required."
        )
        return
    # Authorization is separate from the frozen proposal; never inferred from time,
    # account login, available credit, or merely supplying a backup credential.
    authorization = read_json(here / "continuation-authorization.json")
    if (
        authorization.get("manifest_sha256") != sha(manifest_path)
        or authorization.get("approved") is not True
    ):
        raise ValueError("No explicit approval for this frozen failure-policy amendment")
    with overlay(spec):
        result = experiment.run_experiment(root, output, resume=True)
    print(
        json.dumps({"stop_reason": result.get("stop_reason"), "cells": len(result["cells"])}),
        flush=True,
    )


if __name__ == "__main__":
    main()

"""Verify all16 diagnostic cells, including the disclosed A1 interruption.

Refuses to reveal/aggregate official scores before all product reviews are frozen.
Unknown charges remain unknown; no historical actor or first valid judge is replaced.
"""

import contextlib
import io
import json
import statistics
import tarfile
from decimal import Decimal
from pathlib import Path

from raw_cell_verifier import archive_files, inspect_cell, sha
import verify_interruption

E = Path(__file__).resolve().parent


def main():
    freeze = json.loads((E / "review-freeze.json").read_text())
    assert freeze["executed_reviews"] == freeze["planned_reviews"] == 16
    assert freeze["all_reviews_before_scores"] is False
    assert freeze["per_review_before_own_scores"] == {f"F{i:02d}": i != 7 for i in range(1, 17)}
    assert all(sha((E / k).read_bytes()) == v for k, v in freeze["files"].items())
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        verify_interruption.main()
    partial = json.loads(captured.getvalue())
    assert partial == json.loads((E / "partial-decision.json").read_text())
    files, manifest = archive_files(E)
    old, old_manifest = archive_files(E / "interruption-1")
    prefix = manifest["prefix"] + "/"
    assert manifest["prefix"] == old_manifest["prefix"]

    def read(name):
        return json.loads(files[prefix + name])

    plan = read("plan.json")
    spec = plan["diagnostic_spec"]
    assert files[prefix + "plan.json"] == old[prefix + "plan.json"]
    assert sha(files[prefix + "plan.json"]) == files[prefix + "plan.sha256"].decode().strip()
    assert plan["cells"] == spec["schedule"] and len(plan["cells"]) == 16
    assert {(c["task_id"], c["strategy"], c["seed"]) for c in plan["cells"]} == {
        (t, a, b)
        for t in range(901001, 901005)
        for a in ["selective_patch", "dependency_cut"]
        for b in range(2)
    }
    for name, value in old.items():
        if (
            name.startswith(prefix + "adaptations/")
            or name.startswith(prefix + "catalogs/")
            or name.startswith(prefix + "preflight/")
            or any(name.startswith(prefix + f"cells/cell-{i:03d}/") for i in range(1, 7))
        ):
            assert files[name] == value
    seventh = prefix + "cells/cell-007/run/"
    for name, value in old.items():
        if name.startswith(seventh) and name.removeprefix(seventh) not in {
            "result.json",
            "raw_trace.json",
            "report.txt",
            "EVAL/901003.json",
            "events.jsonl",
        }:
            assert files[name] == value
    assert files[seventh + "events.jsonl"].startswith(old[seventh + "events.jsonl"])
    assert files[seventh + "revisions/resume-1/raw_trace.json"] == old[seventh + "raw_trace.json"]
    assert files[seventh + "revisions/resume-1/result.json"] == old[seventh + "result.json"]
    state = read("experiment.json")
    assert set(state["cells"]) == {c["id"] for c in plan["cells"]}
    assert all(r["status"] == "evaluated" for r in state["cells"].values()) and not state.get(
        "stop_reason"
    )
    for r in state["cells"].values():
        assert all(sha(files[prefix + k]) == v for k, v in r["files"].items())
    source_manifest = json.loads((E / "prefreeze-manifest.json").read_text())
    with tarfile.open(E / source_manifest["archive"]) as tf:
        source = {m.name: tf.extractfile(m).read() for m in tf if m.isfile()}
    api = {}
    exec(
        compile(source["src/pe6203/project_episode_projection.py"], "frozen_auditor.py", "exec"),
        api,
    )
    cases = {x["task_id"]: x for x in spec["cases"]}
    rows = []
    response_ids = []
    for i, c in enumerate(plan["cells"], 1):
        rid = f"F{i:02d}"
        review = json.loads((E / "individual-reviews" / f"{rid}.json").read_text())
        packet = json.loads((E / "review-inputs" / f"{rid}.json").read_text())
        assert review["input_sha256"] == sha((E / "review-inputs" / f"{rid}.json").read_bytes())
        assert set(review["properties"]) == {"records", "fields", "structure", "delivery"}
        assert set(review["properties"].values()) <= {"pass", "fail", "unknown"}
        assert review["core_pass"] == all(v == "pass" for v in review["properties"].values())
        names = [
            n
            for n in files
            if n.startswith(prefix + f"cells/{c['id']}/run/workspace/")
            and n.endswith("/tasks.json")
        ]
        assert len(names) == 1
        store = json.loads(files[names[0]])
        oracle = json.loads(
            source[
                f"experiments/extensions/dependency-factorial-v1/evaluation/oracle-{c['task_id']}.json"
            ]
        )
        assert api["audit_store"](oracle, store) == packet["properties"]
        assert all(review["properties"][k] == v for k, v in packet["properties"].items())
        assert (
            sha(files[names[0]]) == packet["store_sha256"]
            and files[names[0]] == (E / packet["store_path"]).read_bytes()
        )
        trace_name = prefix + f"cells/{c['id']}/run/raw_trace.json"
        assert packet["trace_sha256"] == sha(old[trace_name] if i == 7 else files[trace_name])
        row, ids = inspect_cell(
            files,
            prefix,
            c,
            "controlled_factorial_diagnostic_A1_amended",
            allow_unknown_cost=i == 7,
        )
        response_ids.extend(ids)
        row.update(
            review_id=rid,
            block_index=c["seed"],
            properties=review["properties"],
            core_pass=review["core_pass"],
            topology=cases[c["task_id"]]["topology"],
            payload=cases[c["task_id"]]["payload"],
            review_before_own_scores=i != 7,
        )
        rows.append(row)
    a1 = json.loads((E / "continuation-a1.json").read_text())
    auth = json.loads((E / "continuation-authorization.json").read_text())
    assert auth["approved"] is True and auth["manifest_sha256"] == sha(
        (E / "continuation-a1.json").read_bytes()
    )
    assert auth["manifest_sha256"] == (E / "continuation-a1.sha256").read_text().strip()
    ledger = read("spend-ledger.json")
    old_ledger = json.loads(old[prefix + "spend-ledger.json"])
    assert (
        ledger["policy"] == old_ledger["policy"] == a1["ledger_policy"]
        and ledger["policy"]["limit_usd"] is None
    )
    assert ledger["requests"][:91] == old_ledger["requests"]
    assert ledger["blocked"] is True and ledger["stop_reason"] == "unknown_charge"
    unknown = [r for r in ledger["requests"] if r["status"] != "settled"]
    assert unknown == [old_ledger["requests"][90]]
    settled = [r for r in ledger["requests"] if r["status"] == "settled"]
    assert all(
        r["actual_provider"] == "DigitalOcean" and r["actual_model"] == ledger["policy"]["model"]
        for r in settled
    )
    pre = [r for r in settled if r["max_completion_tokens"] == 32]
    assert len(pre) == 2
    assert len(response_ids) == len(set(response_ids)) and set(response_ids) == {
        r["response_id"] for r in settled if r not in pre
    }
    known = sum((Decimal(r["actual_usd"]) for r in settled), Decimal(0))
    assert known == Decimal(ledger["known_usd"])
    assert Decimal(ledger["unknown_reserved_usd"]) == Decimal(unknown[0]["reserved_usd"])
    seventh_runs = read("cells/cell-007/run/EVAL/901003.json")["eval_result"]["runs"]
    assert [(x["slot"], x["attempt"]) for x in seventh_runs] == [
        (1, 1),
        (2, 1),
        (3, 2),
        (4, 1),
        (5, 1),
    ]
    groups = []
    for task in cases:
        for arm in ["selective_patch", "dependency_cut"]:
            rs = [r for r in rows if r["task_id"] == task and r["strategy"] == arm]
            assert len(rs) == 2
            groups.append(
                {
                    **cases[task],
                    "strategy": arm,
                    "n": 2,
                    "normal_completion": sum(r["execution_status"] == "completed" for r in rs),
                    "core_pass": sum(r["core_pass"] for r in rs),
                    **{
                        p: sum(r["properties"][p] == "pass" for r in rs)
                        for p in ["records", "fields", "structure", "delivery"]
                    },
                    **{
                        p: statistics.mean(r[p] for r in rs)
                        for p in ["TF", "PE", "rounds", "tool_calls"]
                    },
                }
            )
    contrasts = []

    def delta(a, b):
        return {
            "normal_completion": int(b["execution_status"] == "completed")
            - int(a["execution_status"] == "completed"),
            "core_pass": int(b["core_pass"]) - int(a["core_pass"]),
            "fields_pass": int(b["properties"]["fields"] == "pass")
            - int(a["properties"]["fields"] == "pass"),
            "rounds": b["rounds"] - a["rounds"],
            "tool_calls": b["tool_calls"] - a["tool_calls"],
        }

    for block in range(2):
        rs = [r for r in rows if r["block_index"] == block]
        for task in cases:
            a = next(r for r in rs if r["task_id"] == task and r["strategy"] == "selective_patch")
            b = next(r for r in rs if r["task_id"] == task and r["strategy"] == "dependency_cut")
            contrasts.append(
                {"block": block, "contrast": "candidate_minus_SP", "task_id": task, **delta(a, b)}
            )
        for arm in ["selective_patch", "dependency_cut"]:
            for topology in ["shallow", "chain"]:
                a = next(
                    r
                    for r in rs
                    if r["strategy"] == arm
                    and r["topology"] == topology
                    and r["payload"] == "short"
                )
                b = next(
                    r
                    for r in rs
                    if r["strategy"] == arm and r["topology"] == topology and r["payload"] == "long"
                )
                contrasts.append(
                    {
                        "block": block,
                        "contrast": "long_minus_short",
                        "strategy": arm,
                        "topology": topology,
                        **delta(a, b),
                    }
                )
            for payload in ["short", "long"]:
                a = next(
                    r
                    for r in rs
                    if r["strategy"] == arm
                    and r["payload"] == payload
                    and r["topology"] == "shallow"
                )
                b = next(
                    r
                    for r in rs
                    if r["strategy"] == arm and r["payload"] == payload and r["topology"] == "chain"
                )
                contrasts.append(
                    {
                        "block": block,
                        "contrast": "chain_minus_shallow",
                        "strategy": arm,
                        "payload": payload,
                        **delta(a, b),
                    }
                )
    print(
        json.dumps(
            {
                "verified_complete_diagnostic": True,
                "preregistration_amended": True,
                "amendments": [
                    "A1 unknown-cost continuation and derived bounded judge recovery",
                    "Reuse2existing successful preflight receipts within original2-call cap",
                ],
                "raw_files": len(files),
                "source_files": len(source),
                "planned_and_executed_cells": 16,
                "official_rating_slots": 80,
                "rows": rows,
                "groups": groups,
                "contrasts": contrasts,
                "known_usd": str(known),
                "actual_total_usd": None,
                "unknown_cost_items": 1,
                "unknown_reserved_estimate_usd": ledger["unknown_reserved_usd"],
                "reserve_is_charge_or_enforced_upper_bound": False,
                "new_known_usd_after_A1": str(known - Decimal(old_ledger["known_usd"])),
                "started_requests": len(ledger["requests"]),
                "settled_requests": len(settled),
                "preflight_requests": 2,
                "updater_calls": 0,
                "actor_reruns": 0,
                "original_v1_reopened": False,
                "training_pool_admission": False,
                "formal_validation_started": False,
                "goal_complete": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

"""Offline raw-evidence verification and the prospectively fixed two-block gate."""
import json
import statistics
import tarfile
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from raw_cell_verifier import archive_files, inspect_cell, sha

FOLDER = Path(__file__).resolve().parent
ARMS = ("selective_patch", "observed_contract")


def summarize(rows):
    return {
        "n": len(rows),
        "completed": sum(r["execution_status"] == "completed" for r in rows),
        "execution_statuses": dict(Counter(r["execution_status"] for r in rows)),
        "core_pass": sum(r["core_pass"] for r in rows),
        "TF": statistics.mean(r["TF"] for r in rows),
        "PE": statistics.mean(r["PE"] for r in rows),
        "properties": {
            p: dict(Counter(r["properties"][p] for r in rows if p in r["properties"]))
            for p in sorted({p for r in rows for p in r["properties"]})
        },
        "api_usd": str(sum((Decimal(r["cost_usd"][role]) for r in rows
                            for role in ("agent", "judge")), Decimal(0))),
        "rounds": sum(r["rounds"] for r in rows),
        "tool_calls": sum(r["tool_calls"] for r in rows),
    }


def main():
    files, manifest = archive_files(FOLDER)
    prefix = manifest["prefix"] + "/"

    def read(name):
        return json.loads(files[prefix + name])

    plan = read("plan.json")
    assert sha(files[prefix + "plan.json"]) == files[prefix + "plan.sha256"].decode().strip()
    spec = plan["research"]["spec"]
    assert spec["evaluation_stage"] == "independent_validation"
    pairs = ((133, "middle"), (133, "late"), (235, "late"))
    assert len(plan["cells"]) == 36
    assert {(c["task_id"], c["version"], c["strategy"], c["seed"]) for c in plan["cells"]} == {
        (task, stage, arm, seed) for task, stage in pairs for arm in ARMS for seed in range(6)
    }
    lock = read("knowledge-lock.json")
    assert lock["plan_sha256"] == sha(files[prefix + "plan.json"])
    for name, digest in lock["files"].items():
        assert sha(files[prefix + name]) == digest, name
    prior = read("preexecution-review.json")
    assert prior["accepted"] and prior["planned"] == 36
    knowledge_checks = []
    update_costs = {}
    for task, stage in pairs:
        control = read(f"adaptations/{task}-{stage}-selective_patch/knowledge.json")
        candidate = read(f"adaptations/{task}-{stage}-observed_contract/knowledge.json")
        modified = []
        for a, b in zip(candidate["tools"], control["tools"], strict=True):
            assert {k: v for k, v in a.items() if k != "usage_rules"} == {
                k: v for k, v in b.items() if k != "usage_rules"}
            if a != b:
                assert a["usage_rules"][:len(b["usage_rules"])] == b["usage_rules"]
                modified.append(a["tool_id"])
        assert modified == (["math-mcp::validate_syntax"] if task == 133 else [])
        if task == 235:
            assert candidate == control == read("catalogs/235/early.json")
        check = next(c for c in prior["knowledge_checks"] if c["task_id"] == task and c["stage"] == stage)
        assert check["same_as_pilot"]
        for arm in ARMS:
            key = f"{task}-{stage}-{arm}"
            digest = sha(files[prefix + f"adaptations/{key}/knowledge.json"])
            assert digest == check["knowledge_sha256"][arm]
            if arm == "observed_contract":
                assert digest == spec["candidate_knowledge_sha256"][f"{task}-{stage}"]
            update_costs[key] = read(f"adaptations/{key}/adaptation.json")["cost"]
        knowledge_checks.append({"task_id": task, "stage": stage, "modified_tools": modified,
                                 "same_as_frozen_pilot_knowledge": True})

    source_manifest = json.loads((FOLDER / "source-manifest.json").read_text())
    source_archive = FOLDER / source_manifest["archive"]
    assert sha(source_archive.read_bytes()) == source_manifest["archive_sha256"]
    with tarfile.open(source_archive) as tar:
        source_files = {m.name: tar.extractfile(m).read() for m in tar if m.isfile()}
    assert {n: sha(v) for n, v in source_files.items()} == source_manifest["files"]
    for name, digest in plan["files"].items():
        if name.startswith("results/raw/" + manifest["prefix"] + "/"):
            assert sha(files[name.removeprefix("results/raw/")]) == digest
        elif name.startswith(".cache/"):
            assert source_manifest["runtime_hashes_only"][name] == digest
        else:
            assert sha(source_files[name]) == digest
    original = json.loads(source_files["experiments/observed-contract-v1.json"])
    for key in ("quality_cases", "validation_schedule", "evaluation", "mechanism"):
        assert spec[key] == original[key], key

    freeze = json.loads((FOLDER / "review-freeze-36.json").read_text())
    assert freeze["verified"] and freeze["complete"] and freeze["review_count"] == 36
    assert sha(source_files["experiments/observed-contract-v1.json"]) == freeze["protocol_sha256"]
    mapping = json.loads((FOLDER / "blind-map.json").read_text())
    assert len(mapping) == 36 and set(mapping.values()) == {c["id"] for c in plan["cells"]}
    reviews = {}
    for review_id, cell_id in mapping.items():
        path = FOLDER / "blind-reviews" / (review_id + ".json")
        assert sha(path.read_bytes()) == freeze["review_sha256"][path.name]
        review = json.loads(path.read_text())
        inp = (FOLDER / "blind-inputs" / (review_id + ".json")).read_bytes()
        assert sha(inp) == review["input_sha256"]
        assert review["method_and_scores_revealed"] is False
        assert review["generated_code_executed"] is False
        assert review["core_pass"] == all(v == "pass" for v in review["properties"].values())
        trace = read(f"cells/{cell_id}/run/raw_trace.json")
        assert json.loads(inp) == {
            "review_id": review_id, "question": trace["question"], "answer": trace.get("answer"),
            "calls": [{"arguments": e["call"]["function"]["arguments"],
                       "tool": e["call"]["function"]["name"], "result": e["result"]}
                      for e in trace["events"] if e["type"] == "tool_result"],
        }
        reviews[cell_id] = review
    state = read("experiment.json")
    assert set(state["cells"]) == {c["id"] for c in plan["cells"]}
    for cell in state["cells"].values():
        assert cell["status"] == "evaluated"
        for name, digest in cell["files"].items():
            assert sha(files[prefix + name]) == digest
    rows, ids = [], []
    for cell in plan["cells"]:
        row, response_ids = inspect_cell(files, prefix, cell, "A" if cell["seed"] < 3 else "B")
        review = reviews[cell["id"]]
        assert row["task_id"] == review["task_id"]
        row.update({"repeat_index": cell["seed"], "review_id": review["review_id"],
                    "properties": review["properties"], "core_pass": review["core_pass"]})
        rows.append(row)
        ids.extend(response_ids)
    assert len(ids) == len(set(ids))
    assert len({r["protocol_sha256"] for r in rows}) == 1
    ledger = read("spend-ledger.json")
    assert ledger["policy"]["limit_usd"] is None and not ledger["blocked"]
    assert Decimal(ledger["unknown_reserved_usd"]) == 0
    for request in ledger["requests"]:
        assert request["status"] == "settled" and request["actual_provider"] == "DigitalOcean"
        assert request["actual_model"] == ledger["policy"]["model"]
        assert request["provider"] == ledger["policy"]["provider_route"]
        assert request["provider"]["allow_fallbacks"] is False
        assert request["provider"]["only"] == ["digitalocean"]
    preflights = [r for r in ledger["requests"] if r["max_completion_tokens"] == 32]
    assert len(preflights) == 2
    assert set(ids) == {r["response_id"] for r in ledger["requests"] if r not in preflights}
    spent = sum((Decimal(r["actual_usd"]) for r in ledger["requests"]), Decimal(0))
    pf = sum((Decimal(r["actual_usd"]) for r in preflights), Decimal(0))
    assert spent == Decimal(ledger["known_usd"])
    assert abs(spent - pf - sum((Decimal(r["cost_usd"][role]) for r in rows
                                for role in ("agent", "judge")), Decimal(0))) < Decimal("1e-12")

    blocks = {}
    for block in ("A", "B"):
        summaries = {arm: {scope: summarize([r for r in rows if r["block"] == block
                      and r["strategy"] == arm and (r["task_id"] == 235) == (scope == "retention")])
                     for scope in ("changed", "retention")} for arm in ARMS}
        base, candidate = (summaries[a] for a in ARMS)
        gates = {
            "changed_completion_strictly_greater": candidate["changed"]["completed"] > base["changed"]["completed"],
            "changed_core_pass_strictly_greater": candidate["changed"]["core_pass"] > base["changed"]["core_pass"],
            "changed_TF_no_loss": candidate["changed"]["TF"] >= base["changed"]["TF"],
            "retention_completion_no_loss": candidate["retention"]["completed"] >= base["retention"]["completed"],
            "retention_core_pass_no_loss": candidate["retention"]["core_pass"] >= base["retention"]["core_pass"],
            "retention_TF_no_loss": candidate["retention"]["TF"] >= base["retention"]["TF"],
        }
        paired = defaultdict(Counter)
        for task, stage in pairs:
            for seed in (range(3) if block == "A" else range(3, 6)):
                pair = {r["strategy"]: r for r in rows if (r["task_id"], r["stage"], r["repeat_index"]) == (task, stage, seed)}
                for prop in ("completion", "core_pass"):
                    values = [pair[arm]["execution_status"] == "completed" if prop == "completion"
                              else pair[arm]["core_pass"] for arm in ARMS]
                    outcome = "both_pass" if all(values) else "both_fail" if not any(values) else "candidate_only" if values[1] else "control_only"
                    paired[("retention_" if task == 235 else "changed_") + prop][outcome] += 1
        blocks[block] = {"arms": summaries, "gates": gates, "passed": all(gates.values()), "paired": dict(paired)}
    per_condition = {f"{task}-{stage}-{arm}": summarize([r for r in rows if
                       (r["task_id"], r["stage"], r["strategy"]) == (task, stage, arm)])
                     for task, stage in pairs for arm in ARMS}
    elapsed = (datetime.fromisoformat(ledger["requests"][-1]["finished_at"])
               - datetime.fromisoformat(ledger["requests"][0]["started_at"])).total_seconds()
    print(json.dumps({
        "verified": True, "archive_sha256": manifest["archive_sha256"], "file_count": len(files),
        "review_freeze_commit": "c30aec3", "review_freeze_sha256": sha((FOLDER / "review-freeze-36.json").read_bytes()),
        "blocks": blocks, "per_condition": per_condition,
        "overall": {arm: summarize([r for r in rows if r["strategy"] == arm]) for arm in ARMS},
        "cells": rows, "knowledge_checks": knowledge_checks, "distinct_update_costs": update_costs,
        "update_cost_note": "Six shared adaptations computed once, reused across repeats; do not sum per-cell update fields as36 updates.",
        "judge_slots": 180, "api_requests": len(ledger["requests"]), "known_usd": str(spent),
        "preflight_usd": str(pf), "unknown_cost_items": 0, "elapsed_seconds": elapsed,
        "ECS": None, "verification_model_calls": 0,
        "success": all(b["passed"] for b in blocks.values()),
        "decision": "Accept only if every fixed block gate passes; otherwise reject candidate, retain evidence and keep research goal active.",
        "limits": ["Fresh repeats on exposed fixed tasks, not unseen-task generalization or statistical significance.",
                   "Same coordinating reviewer; method/TF/PE hidden until all property reviews frozen, but prose can reveal the intervention.",
                   "Static Python inspection only; no generated code execution or comprehensive security audit.",
                   "Partial schedule has no ECS; separate frozen three-stage baselines are not pooled.",
                   "Runtime binary digest retained; binary installation and remote provider behavior are not reproducible offline."],
    }, indent=2))


if __name__ == "__main__":
    main()

"""Verify this frozen six-cell pilot offline; historical scores are never changed."""

import json
import statistics
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from raw_cell_verifier import archive_files, inspect_cell, sha

FOLDER = Path(__file__).resolve().parent


def main():
    files, manifest = archive_files(FOLDER)
    prefix = manifest["prefix"] + "/"

    def read(name):
        return json.loads(files[prefix + name])

    plan = read("plan.json")
    assert sha(files[prefix + "plan.json"]) == files[prefix + "plan.sha256"].decode().strip()
    pairs = ((133, "middle"), (133, "late"), (235, "late"))
    assert {(c["task_id"], c["version"], c["strategy"]) for c in plan["cells"]} == {
        (t, stage, arm) for t, stage in pairs for arm in ("selective_patch", "observed_contract")
    }
    assert len(plan["cells"]) == 6
    lock = read("knowledge-lock.json")
    assert lock["plan_sha256"] == sha(files[prefix + "plan.json"])
    for name, digest in lock["files"].items():
        assert sha(files[prefix + name]) == digest
    prior = read("preexecution-review.json")
    knowledge_checks = []
    for task, stage in pairs:
        control = read(f"adaptations/{task}-{stage}-selective_patch/knowledge.json")
        candidate = read(f"adaptations/{task}-{stage}-observed_contract/knowledge.json")
        modified = []
        for a, b in zip(candidate["tools"], control["tools"], strict=True):
            assert {k: v for k, v in a.items() if k != "usage_rules"} == {
                k: v for k, v in b.items() if k != "usage_rules"
            }
            if a != b:
                assert a["usage_rules"][:len(b["usage_rules"])] == b["usage_rules"]
                modified.append(a["tool_id"])
        if task == 235:
            assert candidate == control == read("catalogs/235/early.json")
        check = next(c for c in prior["checks"] if c["task_id"] == task and c["stage"] == stage)
        assert modified == check["modified_tools"] == (["math-mcp::validate_syntax"] if task == 133 else [])
        for method in ("selective_patch", "observed_contract"):
            key = f"{task}-{stage}-{method}"
            digest = sha(files[prefix + f"adaptations/{key}/knowledge.json"])
            assert digest == check["knowledge_sha256"][method]
        knowledge_checks.append({"task_id": task, "stage": stage,
                                 "modified_usage_rule_tool_ids": modified,
                                 "all_structural_fields_unchanged": True,
                                 "matches_preexecution_review": True})
    state = read("experiment.json")
    assert set(state["cells"]) == {c["id"] for c in plan["cells"]}
    for c in state["cells"].values():
        assert c["status"] == "evaluated"
        for name, digest in c["files"].items():
            assert sha(files[prefix + name]) == digest
    rows = []
    ids = []
    for c in plan["cells"]:
        row, rids = inspect_cell(files, prefix, c, "pilot")
        rows.append(row)
        ids.extend(rids)
    assert len(ids) == len(set(ids))
    assert len({r["protocol_sha256"] for r in rows}) == 1
    ledger = read("spend-ledger.json")
    assert ledger["policy"]["limit_usd"] is None
    assert not ledger["blocked"] and Decimal(ledger["unknown_reserved_usd"]) == 0
    for r in ledger["requests"]:
        assert r["status"] == "settled" and r["actual_provider"] == "DigitalOcean"
        assert r["actual_model"] == ledger["policy"]["model"]
        assert (
            r["provider"] == ledger["policy"]["provider_route"] and "max_price" not in r["provider"]
        )
    preflights = [r for r in ledger["requests"] if r["max_completion_tokens"] == 32]
    assert len(preflights) == 2
    assert set(ids) == {r["response_id"] for r in ledger["requests"] if r not in preflights}
    spent = sum((Decimal(r["actual_usd"]) for r in ledger["requests"]), Decimal(0))
    pf = sum((Decimal(r["actual_usd"]) for r in preflights), Decimal(0))
    assert spent == Decimal(ledger["known_usd"])
    assert abs(
        spent
        - pf
        - sum(
            (Decimal(c["cost_usd"][role]) for c in rows for role in ("agent", "judge")), Decimal(0)
        )
    ) < Decimal("1e-12")
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["strategy"]].append(row)
    summary = {}
    for arm, cells in grouped.items():
        changed = [r for r in cells if r["task_id"] != 235]
        summary[arm] = {
            "cells": len(cells),
            "completed": sum(c["execution_status"] == "completed" for c in cells),
            "changed_completed": sum(c["execution_status"] == "completed" for c in changed),
            "retention_completed": sum(
                c["execution_status"] == "completed" for c in cells if c["task_id"] == 235
            ),
            "TF": statistics.mean(c["TF"] for c in cells),
            "PE": statistics.mean(c["PE"] for c in cells),
            "changed_TF": statistics.mean(c["TF"] for c in changed),
            "changed_PE": statistics.mean(c["PE"] for c in changed),
            "agent_judge_usd": str(
                sum(
                    (Decimal(c["cost_usd"][role]) for c in cells for role in ("agent", "judge")),
                    Decimal(0),
                )
            ),
            "update_seconds": sum(c["update_seconds"] for c in cells),
            "execution_seconds_sum": sum(c["seconds"] for c in cells),
        }
    elapsed = (
        datetime.fromisoformat(ledger["requests"][-1]["finished_at"])
        - datetime.fromisoformat(ledger["requests"][0]["started_at"])
    ).total_seconds()
    print(
        json.dumps(
            {
                "verified": True,
                "archive_sha256": manifest["archive_sha256"],
                "file_count": len(files),
                "cells": rows,
                "summary": summary,
                "knowledge_checks": knowledge_checks,
                "judge_slots": 30,
                "api_requests": len(ledger["requests"]),
                "known_usd": str(spent),
                "preflight_usd": str(pf),
                "unknown_cost_items": 0,
                "elapsed_seconds": elapsed,
                "ECS": None,
                "verification_model_calls": 0,
                "decision": "Interpret with independent quality review and all prior cohorts; no automatic promotion or repetition.",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

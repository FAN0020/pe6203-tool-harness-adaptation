"""Independently recompute the 12 archived cells; stdlib only, no API calls."""

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
    methods = ("no_update", "full_rewrite", "selective_patch", "budget_feedback")
    stages = ("early", "middle", "late")
    assert len(plan["cells"]) == 12
    assert {(c["task_id"], c["version"], c["strategy"], c["seed"]) for c in plan["cells"]} == {
        (90, stage, method, 0) for stage in stages for method in methods
    }
    lock = read("knowledge-lock.json")
    assert lock["plan_sha256"] == sha(files[prefix + "plan.json"])
    for path, digest in lock["files"].items():
        assert sha(files[prefix + path]) == digest
    for state in read("experiment.json")["cells"].values():
        assert state["status"] == "evaluated"
        for path, digest in state["files"].items():
            assert sha(files[prefix + path]) == digest
    k0 = read("catalogs/90/early.json")
    updates = []
    update_ids = []
    knowledge_checks = []
    for stage in stages:
        target = read(f"catalogs/90/{stage}.json")
        for method in methods:
            folder = f"adaptations/90-{stage}-{method}/"
            knowledge = read(folder + "knowledge.json")
            if stage == "early" or method == "no_update":
                assert knowledge == k0
                continue
            if method == "full_rewrite":
                audit = read(folder + "updater-audit.json")
                response = audit["response"]
                assert response["provider"] == "DigitalOcean"
                assert response["model"] == plan["config"]["agent"]["model"]
                assert not audit.get("request_retries")
                update_ids.append(response["id"])
                charge = Decimal(str(response["usage"]["cost"]))
                assert abs(charge - Decimal(str(audit["update_cost"]["api_cost_usd"]))) < Decimal(
                    "1e-12"
                )
                updates.append(
                    {
                        "stage": stage,
                        "cost_usd": str(charge),
                        "tokens": response["usage"]["total_tokens"],
                        "seconds": audit["update_cost"]["elapsed_seconds"],
                        "rewritten_records": len(knowledge["tools"]),
                    }
                )
                assert {t["tool_id"] for t in target["tools"]} == {
                    t["tool_id"] for t in knowledge["tools"]
                }
                for a, b in zip(target["tools"], knowledge["tools"], strict=True):
                    assert {k: v for k, v in a.items() if k != "description"} == {
                        k: v for k, v in b.items() if k != "description"
                    }
            else:
                for name in ("get_card_by_id", "get_card_image"):
                    assert next(t for t in knowledge["tools"] if t["name"] == name) == next(
                        t for t in k0["tools"] if t["name"] == name
                    )
                if stage == "late":
                    assert not any(t["name"] == "get_daily_challenge" for t in knowledge["tools"])
                    problem = next(t for t in knowledge["tools"] if t["name"] == "get_problem")
                    assert "daily" in problem["parameters"]["properties"]
                    assert "titleSlug" not in problem["parameters"].get("required", [])
            knowledge_checks.append({"stage": stage, "method": method, "verified": True})
    rows, request_ids = [], []
    for cell in plan["cells"]:
        row, ids = inspect_cell(files, prefix, cell, "daily_migration_pilot")
        trace = read(f"cells/{cell['id']}/run/raw_trace.json")
        calls = [e for e in trace["events"] if e["type"] == "tool_result"]

        def named(e):
            return e["call"]["function"]["name"].rsplit("__", 1)[0]

        row["stale_daily_tool_calls"] = (
            sum(named(e) == "get_daily_challenge" for e in calls)
            if cell["version"] == "late" else None
        )
        row["image_calls"] = sum(named(e) == "get_card_image" for e in calls)
        row["image_structured_errors"] = sum(
            named(e) == "get_card_image" and bool(e["result"].get("isError")) for e in calls
        )
        row["daily_selector_calls"] = sum(
            named(e) == "get_problem"
            and json.loads(e["call"]["function"]["arguments"]).get("daily") is True
            for e in calls
        )
        row["has_final_answer"] = bool(trace.get("answer"))
        rows.append(row)
        request_ids.extend(ids)
    assert len({r["protocol_sha256"] for r in rows}) == 1
    ledger = read("spend-ledger.json")
    assert ledger["policy"]["limit_usd"] is None
    assert not ledger["blocked"] and Decimal(ledger["unknown_reserved_usd"]) == 0
    for request in ledger["requests"]:
        assert request["status"] == "settled"
        assert request["actual_provider"] == "DigitalOcean"
        assert request["actual_model"] == ledger["policy"]["model"]
        assert request["provider"] == ledger["policy"]["provider_route"]
        assert "max_price" not in request["provider"]
    preflight = [r for r in ledger["requests"] if r["max_completion_tokens"] == 32]
    assert len(preflight) == 2
    all_ids = request_ids + update_ids + [r["response_id"] for r in preflight]
    assert len(all_ids) == len(set(all_ids))
    assert set(all_ids) == {r["response_id"] for r in ledger["requests"]}
    spent = sum((Decimal(r["actual_usd"]) for r in ledger["requests"]), Decimal(0))
    assert spent == Decimal(ledger["known_usd"])
    pf_cost = sum((Decimal(r["actual_usd"]) for r in preflight), Decimal(0))
    update_cost = sum((Decimal(r["cost_usd"]) for r in updates), Decimal(0))
    assert abs(
        spent
        - pf_cost
        - update_cost
        - sum(
            (Decimal(r["cost_usd"][role]) for r in rows for role in ("agent", "judge")), Decimal(0)
        )
    ) < Decimal("1e-12")
    groups = defaultdict(list)
    for row in rows:
        groups[row["strategy"]].append(row)
    summary = {}
    for method, cells in groups.items():
        tf = {r["stage"]: r["TF"] for r in cells}
        pe = {r["stage"]: r["PE"] for r in cells}
        values = [tf[s] for s in stages]
        summary[method] = {
            "completed": sum(r["execution_status"] == "completed" for r in cells),
            "TF": statistics.mean(values),
            "PE": statistics.mean(pe.values()),
            "ECS_population": statistics.mean(values) - statistics.pstdev(values),
            "ECS_sample": statistics.mean(values) - statistics.stdev(values),
            "TF_by_stage": tf,
            "PE_by_stage": pe,
            "TF_recovery_vs_own_Early": {s: tf[s] - tf["early"] for s in ("middle", "late")},
            "post_change_completed": sum(
                r["execution_status"] == "completed" and r["stage"] != "early" for r in cells
            ),
            "agent_judge_usd": str(
                sum(
                    (Decimal(r["cost_usd"][role]) for r in cells for role in ("agent", "judge")),
                    Decimal(0),
                )
            ),
            "update_tokens": sum(r["update"]["total_tokens"] for r in cells),
            "update_seconds": sum(r["update_seconds"] for r in cells),
            "update_usd": sum(r["update"]["usd"] for r in cells),
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
                "files": len(files),
                "cells": rows,
                "summary": summary,
                "knowledge_checks": knowledge_checks,
                "updater_calls": updates,
                "api_requests": len(ledger["requests"]),
                "known_usd": str(spent),
                "preflight_usd": str(pf_cost),
                "updater_usd": str(update_cost),
                "unknown_cost_items": 0,
                "elapsed_seconds_including_updates": elapsed,
                "new_verification_model_calls": 0,
                "decision": "Independent semantic review required; no automatic promotion. One task, one execution per method-stage, live public content.",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

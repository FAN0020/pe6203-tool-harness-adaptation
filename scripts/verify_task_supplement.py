"""Offline audit of complete-or-blocked supplemental cells; never calls a model."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from decimal import Decimal
from pathlib import Path

from pe6203.benchmark import read_json, write_json
from scripts import eval_v3_formal as common
from scripts import eval_v35_three_tasks as paired


def verify(root, out):
    plan = read_json(out / "plan.json")
    paired.verify(root, out, plan)
    knowledge_freeze = read_json(out / "knowledge-freeze.json")
    receipts = [json.loads(x) for x in (out / "api/receipts.jsonl").read_text().splitlines()]
    checks = {"frozen_source_and_inputs": True,
              "unique_planned_cells": len({c["id"] for c in plan["cell_order"]}) == plan["trajectories_planned"],
              "all_known_costs": all(r["usd"] is not None for r in receipts),
              "expected_models_and_providers": all(r.get("model") == plan["model"] and r.get("provider") == "DigitalOcean" for r in receipts),
              "unique_receipt_numbers": len({r["request_number"] for r in receipts}) == len(receipts),
              "frozen_knowledge": all(common.sha(out / p) == row["sha256"] for p, row in knowledge_freeze["files"].items())}
    questions = [t["question"] for t in plan["tasks"].values()]
    api_ok, private_updater = [], []
    receipt_total = Decimal(0)
    for row in receipts:
        p = out / "api" / f"request-{row['request_number']:05}"
        req, resp, outcome = [read_json(p / n) for n in ("request.json", "response.json", "outcome.json")]
        api_ok.append(req["body"]["model"] == plan["model"]
                      and req["body"]["extra_body"]["provider"] == plan["provider_routing"]["provider"]
                      and resp.get("id") == row.get("id")
                      and outcome == row and "seed" not in req["body"])
        if row["phase"] == "updater":
            private_updater.append(not any(q in json.dumps(req["body"]["messages"], ensure_ascii=False) for q in questions))
        if row["usd"] is not None:
            receipt_total += Decimal(str(row["usd"]))
    checks["api_bodies_and_receipts_consistent"] = all(api_ok)
    checks["updater_receives_no_benchmark_question"] = all(private_updater)
    checks["all_requests_receipted"] = len(list((out / "api").glob("request-*"))) == len(receipts)
    rows = []
    for cell in plan["cell_order"]:
        directory = out / "runs" / cell["id"]
        adaptation = read_json(out / cell["adaptation"])
        blocked = out / "blocked-cells" / (cell["id"] + ".json")
        if adaptation["status"] != "validated":
            rows.append({**cell, "outcome": "update_failed_not_executed", "TF": None, "PE": None,
                         "checks": {"blocked_receipt": blocked.is_file(), "actor_not_run": not directory.exists()},
                         "failure": adaptation.get("validation", {}).get("errors", [])})
            continue
        if not (directory / "result.json").is_file():
            rows.append({**cell, "outcome": "missing_execution", "TF": None, "PE": None,
                         "checks": {"result_saved": False}})
            continue
        result, trace = [read_json(directory / n) for n in ("result.json", "raw_trace.json")]
        evaluation = read_json(directory / "EVAL" / f"{cell['task_id']}.json")["eval_result"]
        record_checks = {
            "full_five_rating_slots": evaluation["aggregate"]["successful_runs"] == plan["ratings_per_trajectory"] == len(evaluation["runs"]),
            "TF_recomputed": abs(evaluation["aggregate"]["task_fulfillment_mean"] - result["TF"]) < 1e-10,
            "PE_recomputed": abs(evaluation["aggregate"]["planning_and_efficiency_mean"] - result["PE"]) < 1e-10,
            "injected_frozen_knowledge": read_json(directory / "knowledge.json") == read_json((out / cell["adaptation"]).parent / "knowledge.json"),
            "live_environment_matches_preflight": read_json(directory / "environment-metadata.json") == read_json(out / f"catalogs/{cell['task_id']}/{cell['stage']}.json"),
            "question_unmodified": trace["question"] == plan["tasks"][str(cell["task_id"])]["question"],
            "no_extra_python_validation": not result["config"].get("artifact_validation"),
        }
        for role in ("agent", "judge"):
            actual = sum((Decimal(str(r["usd"])) for r in receipts if r["cell"] == cell["id"] and r["phase"] == role and r["usd"] is not None), Decimal(0))
            saved = result["cost"][role].get("usd")
            record_checks[role + "_cost_matches_receipts"] = saved is not None and abs(actual - Decimal(str(saved))) < Decimal("1e-10")
        rows.append({**cell, "outcome": "scored", "execution_status": result["execution_status"],
                     "TF": result["TF"], "PE": result["PE"], "checks": record_checks})
    checks["every_condition_accounted_or_failed_admission"] = all(all(r["checks"].values()) for r in rows)
    if "no_update" in {c["arm"] for c in plan["cell_order"]}:
        checks["no_update_exact_Early_K0"] = all(
            read_json(out / f"adaptations/{task}/{stage}/no_update/knowledge.json") == read_json(out / f"catalogs/{task}/early.json")
            for task in plan["tasks"] for stage in common.STAGES)
    secrets = [os.environ.get(k) for k in ("OPENROUTER_API_KEY", "AGENT_API_KEY", "JUDGE_API_KEY") if os.environ.get(k)]
    checks["no_credentials_in_records"] = not any(
        secret.encode() in p.read_bytes() for p in out.rglob("*.json") for secret in secrets)
    arms = {}
    for arm in sorted({c["arm"] for c in plan["cell_order"]}):
        selected = [r for r in rows if r["arm"] == arm]
        scored = [r for r in selected if r["outcome"] == "scored"]
        arms[arm] = {"planned": len(selected), "scored": len(scored),
                     "update_blocked_trajectories": sum(r["outcome"] == "update_failed_not_executed" for r in selected),
                     "normal_final_answers": sum(r.get("execution_status") == "completed" for r in selected),
                     "scored_only_TF": sum(r["TF"] for r in scored) / len(scored) if scored else None,
                     "scored_only_PE": sum(r["PE"] for r in scored) / len(scored) if scored else None,
                     "update_conditions_validated": sum(read_json(out / f"adaptations/{tid}/{stage}/{arm}/adaptation.json")["status"] == "validated" for tid in plan["tasks"] for stage in common.STAGES),
                     "update_conditions_planned": len(plan["tasks"]) * 3}
    output = {"checks": checks, "passed": all(checks.values()), "by_arm": arms,
              "planned": len(rows), "outcomes": dict(Counter(r["outcome"] for r in rows)),
              "requests": len(receipts), "actual_known_usd": str(receipt_total), "rows": rows,
              "caveat": "TF/PE are conditional on successful update/execution/scoring. Blocked conditions have no official score; they are never discarded or imputed to zero."}
    write_json(out / "verification.json", output)
    print(json.dumps({k: v for k, v in output.items() if k != "rows"}), flush=True)
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.root.resolve(), args.input.resolve())
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

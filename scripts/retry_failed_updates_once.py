"""One exploratory retry of every missing five-task update condition.

Original records and headline scores are immutable. No success-only replacement,
method changes, fallback knowledge, or repeat-until-success sampling is allowed.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import shutil
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

from integration import baselines as provider
from pe6203 import runner, selective_v6
from pe6203.baselines import write_adaptation
from pe6203.benchmark import load_task, read_json, source, write_json
from scripts import eval_five_task_supplement as supplement
from scripts import eval_v3_formal as common
from scripts import eval_v35_three_tasks as paired

ARMS = ("v2", "v3", "v5", "v6")
CONDITIONS = (
    ("v2", 283, "late"), ("v2", 430, "late"), ("v2", 90, "late"),
    ("v3", 283, "late"), ("v5", 133, "middle"),
    ("v6", 430, "late"), ("v6", 90, "late"),
)


def original(root, arm, task, stage):
    if arm == "v2" and task == 283:
        return root / "evaluation/v2/recorded-results/v2-eval/cases/task283-late-selective_patch-r0.json"
    batch = "v35-original-three-20261103" if arm in ("v3", "v5") else "five-task-supplement-20261103"
    return root / f"results/raw/{batch}/adaptations/{task}/{stage}/{arm}/adaptation.json"


def prepare(root, out):
    if out.exists():
        raise ValueError("Retry experiment requires a new directory")
    out.mkdir(parents=True)
    _, upstream = source(root)
    originals, conditions = {}, []
    for arm, task, stage in CONDITIONS:
        p = original(root, arm, task, stage)
        record = read_json(p)
        if record["status"] not in ("failed", "adaptation_failed"):
            raise ValueError("Retry eligible set contains an originally successful condition")
        originals[str(p.relative_to(root))] = common.sha(p)
        conditions.append({"arm": arm, "task_id": task, "stage": stage,
                           "original_record": str(p.relative_to(root)), "original_status": record["status"]})
        source_batch = "v35-original-three-20261103" if task in (133, 283) else "five-task-supplement-20261103"
        for version in ("early", stage):
            p = root / f"results/raw/{source_batch}/catalogs/{task}/{version}.json"
            target = out / f"catalogs/{task}/{version}.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                shutil.copy2(p, target)
        if arm == "v3":
            p = root / f"results/raw/v35-original-three-20261103/capability-evidence/{task}/{stage}.json"
            target = out / f"capability-evidence/{task}/{stage}.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)
    base = read_json(root / "results/raw/v35-original-three-20261103/plan.json")
    cells = []
    rng = random.Random(20261103)
    for repeat in (1, 2, 3):
        order = list(conditions)
        rng.shuffle(order)
        for c in order:
            cells.append({**c, "id": f"{c['task_id']}-{c['stage']}-{c['arm']}-retry1-r{repeat}",
                          "repeat": repeat, "seed": 200 + repeat, "strategy": "selective_patch",
                          "adaptation": f"adaptations/{c['task_id']}/{c['stage']}/{c['arm']}/adaptation.json"})
    hashes = paired.source_hashes(root)
    for name in ("scripts/retry_failed_updates_once.py", "scripts/eval_five_task_supplement.py"):
        hashes[name] = common.sha(root / name)
    plan = {"schema": "all-failed-updates-one-retry-1", "frozen_at": common.now(),
            "conditions": conditions, "original_record_hashes": originals,
            "tasks": {str(t): load_task(upstream, t) for t in sorted({c['task_id'] for c in conditions})},
            "source_files_sha256": hashes,
            "catalogs_sha256": {str(p.relative_to(out)): common.sha(p) for p in out.glob("catalogs/*/*.json")},
            "capability_evidence_sha256": {str(p.relative_to(out)): common.sha(p) for p in out.glob("capability-evidence/*/*.json")},
            "model": base["model"], "provider_routing": base["provider_routing"],
            "actor_and_judge": deepcopy(base["actor_and_judge"]), "updater": deepcopy(base["updater"]),
            "cell_order": cells, "trajectories_planned": 21, "ratings_per_trajectory": 5,
            "concurrency": 4, "budget_known_usd": 1,
            "budget_basis": "Operational stop at USD1; seven updates plus at most21actors and105validjudge slots; not a user-specified budget.",
            "retry_policy": {"update_attempts_per_failed_condition": 1,
                             "successful_retry_actor_runs": 3,
                             "original_records_overwritten": False,
                             "success_only_replacement": False,
                             "method_or_prompt_changes": False,
                             "fallback": False,
                             "all_outcomes_and_costs_retained": True,
                             "analysis_status": "posthoc_exploratory_recovery_study_not_primary_comparison"},
            "comparability": {"recent_failures": "same pinned DigitalOcean route and frozen method settings",
                              "historical_V2_283": "Historical routing was not pinned; this retry uses current DigitalOcean protocol, not an exact historical-provider replication",
                              "controls": "No new baseline runs; cannot claim retry-based superiority over single-attempt controls"}}
    write_json(out / "plan.json", plan)
    return plan


def check_originals(root, plan):
    for name, expected in plan["original_record_hashes"].items():
        if common.sha(root / name) != expected:
            raise ValueError("Original result changed: " + name)


def adapt_once(out, plan, guard):
    manifest = {}
    for c in plan["conditions"]:
        task, stage, arm = c["task_id"], c["stage"], c["arm"]
        directory = out / f"adaptations/{task}/{stage}/{arm}"
        common.CELL.set(f"retry1-update-{task}-{stage}-{arm}")
        context = {"selective_mode": f"hybrid_{arm}", "updater": plan["updater"]}
        if arm == "v3":
            context["capability_evidence"] = read_json(out / f"capability-evidence/{task}/{stage}.json")
        try:
            artifact = write_adaptation(out / f"catalogs/{task}/early.json", out / f"catalogs/{task}/{stage}.json",
                                        "selective_patch", directory, context)
            print(json.dumps({"type": "retry_update", **c, "status": artifact["status"], "cost": artifact["cost"]}), flush=True)
        except Exception as exc:
            write_json(directory / "retry-error.json", {"error_type": type(exc).__name__, "detail": str(exc)})
            print(json.dumps({"type": "retry_update_failed", **c, "detail": str(exc)}), flush=True)
        for name in ("adaptation.json", "knowledge.json"):
            p = directory / name
            if p.exists():
                manifest[str(p.relative_to(out))] = {"sha256": common.sha(p)}
        if guard.stopped:
            raise RuntimeError("Receipt guard stopped retry batch")
    write_json(out / "knowledge-freeze.json", {"frozen_at": common.now(), "files": manifest})


def summarize(out, plan):
    original_arms = paired.ARMS
    try:
        paired.ARMS = ARMS
        summary = paired.summarize(out, plan)
    finally:
        paired.ARMS = original_arms
    conditions = []
    for c in plan["conditions"]:
        p = out / f"adaptations/{c['task_id']}/{c['stage']}/{c['arm']}/adaptation.json"
        a = read_json(p) if p.exists() else {}
        conditions.append({**c, "retry_update_status": a.get("status", "not_attempted"),
                           "failure": a.get("validation", {}).get("errors", [])})
    summary["retry_conditions"] = conditions
    summary["retry_updates_passed"] = sum(c["retry_update_status"] == "validated" for c in conditions)
    summary["primary_scores_replaced"] = False
    write_json(out / "summary.json", summary)
    return summary


def verify(root, out, plan):
    paired.verify(root, out, plan)
    check_originals(root, plan)
    freeze = read_json(out / "knowledge-freeze.json")["files"]
    checks = {"original_records_unchanged": True, "frozen_sources_and_inputs": True,
              "knowledge_unchanged": all(common.sha(out / p) == v["sha256"] for p, v in freeze.items())}
    receipts = [json.loads(x) for x in (out / "api/receipts.jsonl").read_text().splitlines()]
    checks["known_charges_and_pinned_route"] = all(r.get("usd") is not None and r.get("provider") == "DigitalOcean" and r.get("model") == plan["model"] for r in receipts)
    rows = []
    for cell in plan["cell_order"]:
        directory = out / "runs" / cell["id"]
        adaptation = read_json(out / cell["adaptation"])
        if adaptation["status"] != "validated":
            ok = not directory.exists() and (out / "blocked-cells" / (cell["id"] + ".json")).exists()
            rows.append({"id": cell["id"], "outcome": "retry_update_failed", "verified": ok})
            continue
        result = read_json(directory / "result.json")
        evaluation = read_json(directory / "EVAL" / f"{cell['task_id']}.json")["eval_result"]["aggregate"]
        knowledge_ok = read_json(directory / "knowledge.json") == read_json((out / cell["adaptation"]).parent / "knowledge.json")
        valid = evaluation["successful_runs"] == 5 and abs(evaluation["task_fulfillment_mean"] - result["TF"]) < 1e-10 and abs(evaluation["planning_and_efficiency_mean"] - result["PE"]) < 1e-10
        costs_ok = all(abs(sum((Decimal(str(r["usd"])) for r in receipts if r["cell"] == cell["id"] and r["phase"] == role), Decimal(0))-Decimal(str(result["cost"][role]["usd"]))) < Decimal("1e-10") for role in ("agent", "judge"))
        rows.append({"id": cell["id"], "outcome": "scored", "TF": result["TF"], "PE": result["PE"], "verified": knowledge_ok and valid and costs_ok})
    checks["all_21_cells_accounted"] = len(rows) == 21 and all(r["verified"] for r in rows)
    write_json(out / "verification.json", {"passed": all(checks.values()), "checks": checks, "rows": rows})
    if not all(checks.values()):
        raise ValueError("Offline retry verification failed")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "execute", "verify"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root, out = args.root.resolve(), args.output.resolve()
    if args.action == "prepare":
        plan = prepare(root, out)
        print(json.dumps({"prepared": True, "conditions": len(plan["conditions"]), "max_actor_runs": 21}), flush=True)
        return
    plan = read_json(out / "plan.json")
    if args.action == "verify":
        verify(root, out, plan)
        print(json.dumps(summarize(out, plan)["retry_conditions"]), flush=True)
        return
    paired.verify(root, out, plan)
    check_originals(root, plan)
    if (out / "api").exists():
        raise ValueError("Retry batch already executed; no repeat-until-success sampling")
    common.credential_environment(None)
    guard = supplement.Guard(out / "api", plan["budget_known_usd"])
    runner.AsyncOpenAI = guard.async_client
    provider._request_completion = guard.updater
    selective_v6.request_completion = guard.structured_updater
    try:
        adapt_once(out, plan, guard)
        asyncio.run(common.actors(root, out, plan, guard))
    finally:
        summarize(out, plan)
        check_originals(root, plan)


if __name__ == "__main__":
    main()

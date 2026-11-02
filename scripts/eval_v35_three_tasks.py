"""Fresh paired V3/V5 evaluation on the original three tasks; no legacy-score mixing.

The existing formal runner, official judge, model route and actor policy are reused.
Preparation has no model calls. Execution never reruns an existing trajectory.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import random
import statistics
import subprocess
from collections import Counter
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

from integration import baselines as provider
from pe6203 import runner
from pe6203.baselines import write_adaptation
from pe6203.benchmark import load_task, read_json, source, write_json
from pe6203.capability import fingerprint
from pe6203.experiment import collect_catalogs, configure_runtime
from scripts import eval_v3_formal as common

TASKS = (133, 235, 283)
ARMS = ("v3", "v5")
STAGES = common.STAGES


def make_cells():
    cells = []
    rng = random.Random(20261103)
    for repeat in range(1, 4):
        conditions = [(task, stage) for task in TASKS for stage in STAGES]
        rng.shuffle(conditions)
        for index, (task, stage) in enumerate(conditions):
            arms = ARMS if (index + repeat) % 2 else tuple(reversed(ARMS))
            for arm in arms:
                cells.append({
                    "id": f"{task}-{stage}-{arm}-r{repeat}", "task_id": task,
                    "stage": stage, "arm": arm, "strategy": "selective_patch",
                    "repeat": repeat, "seed": 100 + repeat,
                    "adaptation": f"adaptations/{task}/{stage}/{arm}/adaptation.json",
                })
    return cells


def source_hashes(root):
    files = subprocess.check_output(
        ["git", "ls-files", "src", "integration", "configs"], cwd=root, text=True
    ).splitlines()
    files += ["scripts/eval_v35_three_tasks.py", "scripts/eval_v3_formal.py"]
    return {name: common.sha(root / name) for name in files if (root / name).is_file()}


def prepare(root, out):
    if out.exists():
        raise ValueError("Use a fresh output directory; existing evidence is immutable")
    configure_runtime(root)
    lock, upstream = source(root)
    tasks = {str(t): load_task(upstream, t) for t in TASKS}
    out.mkdir(parents=True)
    asyncio.run(collect_catalogs(root, TASKS, out))
    evidence = {}
    hashes = {}
    for task in TASKS:
        for stage in STAGES:
            p = out / f"catalogs/{task}/{stage}.json"
            hashes[str(p.relative_to(out))] = common.sha(p)
            catalog = read_json(p)
            bundle = {"version": "capability-evidence-v1", "entries": [
                {"tool_id": t["tool_id"], "tool_fingerprint": fingerprint(t),
                 "kind": "catalog", "quote": t["description"][:4000]}
                for t in catalog["tools"] if t["description"].strip()
            ]}
            p = out / f"capability-evidence/{task}/{stage}.json"
            write_json(p, bundle)
            evidence[str(p.relative_to(out))] = common.sha(p)
    config = read_json(root / "configs/course-benchmark-v1.3.json")
    for role in ("agent", "judge"):
        config[role]["extra_body"] = deepcopy(common.ROUTING)
    config["request_retry"] = {"max_retries": 0}
    config["runtime"] = None
    config["comparison_scope"] = "knowledge_update_only_same_actor_no_artifact_repair"
    updater = read_json(root / "configs/course-updater.json")
    updater.update(allow_metadata_api=True, request_retry={"max_retries": 0})
    plan = {
        "schema": "v35-original-three-tasks-1", "frozen_at": common.now(),
        "implementation_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "benchmark_commit": lock["commit"], "tasks": tasks,
        "source_files_sha256": source_hashes(root), "catalogs_sha256": hashes,
        "capability_evidence_sha256": evidence, "model": common.MODEL,
        "provider_routing": common.ROUTING, "actor_and_judge": config,
        "updater": updater, "cell_order": make_cells(), "trajectories_planned": 54,
        "ratings_per_trajectory": 5, "concurrency": 4, "budget_known_usd": 2,
        "budget_basis": "Operational stop at USD2; historical 54-actor prorated costs below USD1; not a user-specified budget. Unknown charges stop new requests.",
        "knowledge": {"v3": "hybrid_v3 with literal catalog capability evidence",
                      "v5": "hybrid_v5 catalog-only",
                      "freeze": "Early K0 -> each target directly; one adaptation reused for three actors"},
        "validity": {"questions": "unmodified official selected tasks; no reference answers",
                     "updater": "no task questions, trajectories, answers, tests or judge scores",
                     "execution": "same existing actor; no extra Python validation or repair",
                     "reruns": "none; failures and all charges retained",
                     "comparison": "V3 versus V5 paired cohort; historical NU/FR/V6 are not concurrent controls",
                     "generalization": "three selected tasks, descriptive results only"},
    }
    write_json(out / "plan.json", plan)
    return plan


def verify(root, out, plan):
    for name, expected in plan["source_files_sha256"].items():
        if common.sha(root / name) != expected:
            raise ValueError(f"Frozen source changed: {name}")
    for field in ("catalogs_sha256", "capability_evidence_sha256"):
        for name, expected in plan[field].items():
            if common.sha(out / name) != expected:
                raise ValueError(f"Frozen input changed: {name}")


def adapt_all(out, plan, guard):
    manifest = {}
    for task in TASKS:
        for stage in STAGES:
            for arm in ARMS:
                directory = out / f"adaptations/{task}/{stage}/{arm}"
                common.CELL.set(f"update-{task}-{stage}-{arm}")
                context = {"selective_mode": f"hybrid_{arm}", "updater": plan["updater"]}
                if arm == "v3":
                    context["capability_evidence"] = read_json(
                        out / f"capability-evidence/{task}/{stage}.json")
                try:
                    artifact = write_adaptation(
                        out / f"catalogs/{task}/early.json",
                        out / f"catalogs/{task}/{stage}.json", "selective_patch", directory, context)
                    print(json.dumps({"type": "adaptation", "task": task, "stage": stage,
                                      "arm": arm, "status": artifact["status"],
                                      "cost": artifact["cost"]}), flush=True)
                except Exception as exc:
                    write_json(directory / "evaluation-error.json",
                               {"status": "failed", "error_type": type(exc).__name__, "detail": str(exc)})
                    print(json.dumps({"type": "adaptation_failed", "task": task,
                                      "stage": stage, "arm": arm, "detail": str(exc)}), flush=True)
                for name in ("adaptation.json", "knowledge.json"):
                    p = directory / name
                    if p.exists():
                        manifest[str(p.relative_to(out))] = {"sha256": common.sha(p)}
                if guard.stopped:
                    raise RuntimeError("API receipt guard stopped updates")
    write_json(out / "knowledge-freeze.json", {"frozen_at": common.now(), "files": manifest})


def summarize(out, plan):
    rows = []
    for cell in plan["cell_order"]:
        p = out / "runs" / cell["id"] / "result.json"
        if not p.exists():
            rows.append({**cell, "status": "not_run", "TF": None, "PE": None})
            continue
        result = read_json(p)
        trace = read_json(p.parent / "raw_trace.json")
        calls = [e for e in trace["events"] if e.get("type") == "tool_result"]
        rows.append({**cell, "status": result["status"],
                     "execution_status": result["execution_status"],
                     "judge_status": result["judge_status"], "TF": result["TF"], "PE": result["PE"],
                     "tool_calls": len(calls), "tool_errors": sum(bool(e["result"].get("isError")) for e in calls),
                     "actor_usd": result["cost"]["agent"].get("usd"),
                     "judge_usd": result["cost"]["judge"].get("usd")})
    ledger = out / "api/receipts.jsonl"
    receipts = [json.loads(x) for x in ledger.read_text().splitlines()] if ledger.exists() else []
    aggregate = {}
    for arm in ARMS:
        selected = [r for r in rows if r["arm"] == arm]
        scored = [r for r in selected if r["TF"] is not None and r["PE"] is not None]
        updates = [r for r in receipts if r["phase"] == "updater" and r["cell"].endswith("-" + arm)]
        update_cost = str(sum((Decimal(str(r["usd"])) for r in updates if r["usd"] is not None), Decimal(0)))
        actor_cost = str(sum((Decimal(str(r["actor_usd"])) for r in selected if r.get("actor_usd") is not None), Decimal(0)))
        aggregate[arm] = {"planned": len(selected), "scored": len(scored),
                          "TF": statistics.mean(r["TF"] for r in scored) if scored else None,
                          "PE": statistics.mean(r["PE"] for r in scored) if scored else None,
                          "normal_final_answers": sum(r.get("execution_status") == "completed" for r in selected),
                          "tool_errors": sum(r.get("tool_errors", 0) for r in selected),
                          "update_usd_once": update_cost, "actor_usd": actor_cost,
                          "deployment_usd": str(Decimal(update_cost) + Decimal(actor_cost))}
    summary = {"planned": len(rows), "saved": sum(r["status"] != "not_run" for r in rows),
               "scored": sum(r["TF"] is not None and r["PE"] is not None for r in rows),
               "by_arm": aggregate, "rows": rows,
               "api_requests": len(receipts),
               "unknown_charge_requests": sum(r["usd"] is None for r in receipts),
               "known_actual_usd": str(sum((Decimal(str(r["usd"])) for r in receipts if r["usd"] is not None), Decimal(0))),
               "phase_requests": dict(Counter(r["phase"] for r in receipts))}
    write_json(out / "summary.json", summary)
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with (out / "trajectories.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "execute", "summarize"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root, out = args.root.resolve(), args.output.resolve()
    if args.action == "prepare":
        plan = prepare(root, out)
        print(json.dumps({"prepared": True, "planned": plan["trajectories_planned"]}), flush=True)
        return
    plan = read_json(out / "plan.json")
    if args.action == "execute":
        verify(root, out, plan)
        if (out / "api").exists() or (out / "knowledge-freeze.json").exists():
            raise ValueError("Existing execution cannot be rerun")
        common.credential_environment(None)
        guard = common.ReceiptGuard(out / "api", plan["budget_known_usd"])
        runner.AsyncOpenAI = guard.async_client
        provider._request_completion = guard.updater
        try:
            adapt_all(out, plan, guard)
            asyncio.run(common.actors(root, out, plan, guard))
        finally:
            summarize(out, plan)
    else:
        print(json.dumps(summarize(out, plan)["by_arm"]), flush=True)


if __name__ == "__main__":
    main()

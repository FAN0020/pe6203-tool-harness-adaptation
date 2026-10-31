"""Read-only audit of saved experiments; no models, MCP calls or score changes."""

import hashlib
import itertools
import json
import math
import statistics
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect(name):
    directory = ROOT / "results/raw" / name
    plan = read(directory / "plan.json")
    assert sha(directory / "plan.json") == (directory / "plan.sha256").read_text().strip()
    summary = read(directory / "summary.json")
    verified_files = 0
    for cell in read(directory / "experiment.json")["cells"].values():
        for relative, expected in cell.get("files", {}).items():
            assert sha(directory / relative) == expected, (name, relative)
            verified_files += 1
    records = []
    for path in sorted(directory.glob("cells/*/run/result.json")):
        result = read(path)
        if result.get("TF") is not None:
            evaluation = read(path.parent / "EVAL" / f"{result['task_id']}.json")
            ratings = [
                json.loads(x["response"]["choices"][0]["message"]["content"])
                for x in evaluation["eval_result"]["runs"]
            ]
            assert len(ratings) == 5
            for field, key in [("TF", "task_fulfillment"), ("PE", "planning_and_efficiency")]:
                assert math.isclose(
                    result[field], statistics.mean(x[key] for x in ratings), abs_tol=1e-12
                )
        records.append(result)
    scored = sum(r.get("TF") is not None for r in records)
    assert scored == summary["scored"]
    return (
        {
            "output": str(directory.relative_to(ROOT)),
            "planned": len(plan["cells"]),
            "saved_executions": len(records),
            "scored": scored,
            "valid_rating_slots": scored * 5,
            "execution_status": dict(Counter(r["execution_status"] for r in records)),
            "terminal_files_verified": verified_files,
            "plan_sha256": sha(directory / "plan.json"),
        },
        records,
        plan,
    )


def main():
    names = [
        "course-v1.3-final-20261031",
        "selective-search-confirmation-r1-20261031",
        "selective-search-v1.1-development-20261031",
        "selective-search-v2.1-development-20261031",
        "selective-search-v3-development-20261031",
        "selective-search-confirmation-r2-20261031",
        "selective-search-confirmation-r3-20261031",
    ]
    audits, all_records, plans = [], {}, {}
    for name in names:
        audit, records, plan = inspect(name)
        audits.append(audit)
        all_records[name], plans[name] = records, plan
    records = all_records[names[0]]
    methods = ["no_update", "full_rewrite", "selective_patch"]
    expected = set(itertools.product([133, 235, 283], ["early", "middle", "late"], methods, [0]))
    assert {(r["task_id"], r["version"], r["strategy"], r["seed"]) for r in records} == expected
    metrics = []
    for method in methods:
        rows = [r for r in records if r["strategy"] == method]
        pop, sample = [], []
        for task in [133, 235, 283]:
            tf = [r["TF"] for r in rows if r["task_id"] == task]
            pop.append(statistics.mean(tf) - statistics.pstdev(tf))
            sample.append(statistics.mean(tf) - statistics.stdev(tf))
        metrics.append(
            {
                "method": method,
                "TF": statistics.mean(r["TF"] for r in rows),
                "PE": statistics.mean(r["PE"] for r in rows),
                "ECS_population": statistics.mean(pop),
                "ECS_sample": statistics.mean(sample),
                "execution_status": dict(Counter(r["execution_status"] for r in rows)),
            }
        )
    p, q = plans[names[0]], plans[names[1]]
    compatibility = {
        "config_equal": p["config"] == q["config"],
        "updater_equal": p["updater"] == q["updater"],
        "benchmark_equal": p["benchmark_commit"] == q["benchmark_commit"],
        "dataset_equal": p["dataset_revision"] == q["dataset_revision"],
        "changed_shared_source_files": sorted(
            k for k in p["files"].keys() & q["files"].keys() if p["files"][k] != q["files"][k]
        ),
        "decision": "Reuse all R1 as separate appendix; 81 original-arm executions already give 3 repeats. No pooling with course v1.3. R1 freezes shared adaptations; Full Rewrite regenerated a separate artifact set.",
    }
    timing = {}
    for task in [133, 235, 283]:
        rows = [r for r in records if r["task_id"] == task]
        seconds = [r["seconds"] for r in rows]
        costs = [
            sum(r["cost"][role].get("known_usd") or 0 for role in ["agent", "judge"]) for r in rows
        ]
        timing[str(task)] = {
            label: {"min": min(values), "median": statistics.median(values), "max": max(values)}
            for label, values in [("seconds", seconds), ("known_agent_judge_usd", costs)]
        }
    cost = read(ROOT / "results/evidence/course-v1.3-20261031/cost-audit.json")
    preflight = sum(
        x["usage"]["cost"]
        for path in (ROOT / audits[0]["output"] / "preflight").glob("*.json")
        for x in read(path)
    )
    starts = [datetime.fromisoformat(r["started_at"]) for r in records]
    ends = [
        datetime.fromisoformat(r["started_at"]) + timedelta(seconds=r["seconds"]) for r in records
    ]
    archive = ROOT / "results/evidence/course-v1.3-20261031/raw-trial.tar.gz"
    archive_sha = sha(archive)
    assert archive_sha == "e95e15694abe9a12e37c813f81e6e0fb0b5ccd00c2003f2a25a36a092c8001c9"
    result = {
        "status": "offline_verified",
        "no_model_calls": True,
        "historical_files_modified": False,
        "cohorts": audits,
        "course_metrics": metrics,
        "r1_reuse": compatibility,
        "course_cost": {
            "known_execution_usd": cost["known_execution_usd"],
            "update_usd": cost["update_usd"],
            "preflight_usd": preflight,
            "known_total_usd": cost["known_execution_usd"] + cost["update_usd"] + preflight,
            "unknown_request_charges": cost["unknown_execution_charges"],
        },
        "measured_cost_runtime_basis": timing,
        "course_execution_span_minutes": (max(ends) - min(starts)).total_seconds() / 60,
        "course_archive_sha256": archive_sha,
    }
    (OUT / "reuse-audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": result["status"],
                "cohorts": len(audits),
                "scored_trajectories_verified": sum(a["scored"] for a in audits),
                "rating_slots_verified": sum(a["valid_rating_slots"] for a in audits),
                "terminal_files_verified": sum(a["terminal_files_verified"] for a in audits),
            }
        )
    )


if __name__ == "__main__":
    main()

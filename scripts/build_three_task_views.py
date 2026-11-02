"""Build transparent three-task reporting views from immutable recorded batches.

No model calls, branch rewrites, raw-score edits or success-only selections.
The original four/five-task studies remain linked with their exact provenance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

SOURCE_REF = "7e4094e4e5fcc9dd3e4f108c3872789b6b6b946a"
TASKS = (133, 235, 283)
FIRST_PATH = "evaluation/supplements/five-task-20261103/v35-original-three-20261103/summary.json"
RETRY_PATH = "evaluation/supplements/failed-updates-retry-once-20261103/summary.json"


def read_source(root, path):
    raw = subprocess.check_output(["git", "show", f"{SOURCE_REF}:{path}"], cwd=root)
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def metrics(rows):
    scored = [r for r in rows if r.get("TF") is not None and r.get("PE") is not None]
    ecs = []
    for task in TASKS:
        values = []
        for repeat in (1, 2, 3):
            stage = {r["stage"]: r["TF"] for r in scored if r["task_id"] == task and r["repeat"] == repeat}
            if set(stage) == {"early", "middle", "late"}:
                ts = [stage[s] for s in ("early", "middle", "late")]
                values.append(statistics.mean(ts) - statistics.pstdev(ts))
        ecs.append({"task_id": task, "complete_repeats": len(values),
                    "ECS": statistics.mean(values) if len(values) == 3 else None})
    return {"planned_actor_executions": 27, "scored_actor_executions": len(scored),
            "normal_final_answers": sum(r.get("execution_status") == "completed" for r in rows),
            "TF_on_scored": statistics.mean(r["TF"] for r in scored),
            "PE_on_scored": statistics.mean(r["PE"] for r in scored),
            "ECS_population": statistics.mean(r["ECS"] for r in ecs) if all(r["ECS"] is not None for r in ecs) else None,
            "ECS_by_task": ecs, "missing_actor_executions": 27 - len(scored)}


def make_view(first, retry, version):
    rows = [deepcopy(r) for r in first["rows"] if r["arm"] == version and r["task_id"] in TASKS]
    if len(rows) != 27 or {r["task_id"] for r in rows} != set(TASKS):
        raise ValueError("First-attempt view must cover all original27 planned trajectories")
    after = []
    for row in rows:
        if row.get("TF") is not None and row.get("PE") is not None:
            after.append({**row, "source_attempt": "first"})
            continue
        candidates = [r for r in retry["rows"] if r["arm"] == version and r["task_id"] == row["task_id"] and r["stage"] == row["stage"] and r["repeat"] == row["repeat"] and r.get("TF") is not None and r.get("PE") is not None]
        if len(candidates) > 1:
            raise ValueError("Multiple first-retry scores are not eligible for selection")
        after.append({**deepcopy(candidates[0]), "source_attempt": "one_retry"} if candidates else {**row, "source_attempt": "first_failed"})
    return rows, after


def build(root):
    first, first_sha = read_source(root, FIRST_PATH)
    retry, retry_sha = read_source(root, RETRY_PATH)
    result = {}
    for version in ("v3", "v5"):
        out = root / "evaluation" / version / "three-task-view"
        out.mkdir(parents=True, exist_ok=True)
        before, after = make_view(first, retry, version)
        first_cost = first["by_arm"][version]
        retry_cost = retry["by_arm"][version]
        costs = {"first_update_usd": first_cost["update_usd_once"],
                 "first_actor_usd": first_cost["actor_usd"],
                 "extra_retry_update_usd": retry_cost["update_usd_once"],
                 "extra_retry_actor_usd": retry_cost["actor_usd"],
                 "retry_aware_deployment_usd": str(Decimal(first_cost["deployment_usd"]) + Decimal(retry_cost["deployment_usd"]))}
        common = {"tasks": list(TASKS), "stages": ["early", "middle", "late"],
                  "version": version, "actor_repeats": 3, "judge_ratings_per_actor": 5,
                  "report_scope": "Retrospective task alignment requested2026-11-03; original reporting task set restored after extension studies",
                  "source_commit": SOURCE_REF,
                  "source_files": {FIRST_PATH: first_sha, RETRY_PATH: retry_sha},
                  "comparability": "Same task IDs as V6; different historical batches/repeats/provider and Python artifact protocols remain. Not a controlled version ranking.",
                  "raw_records_changed": False}
        views = {
            "first-attempt.json": {**common, "attempt_policy": "first_attempt_only", "metrics": metrics(before), "rows": before},
            "one-retry.json": {**common, "attempt_policy": "posthoc_once_retry_of_failed_updates_all_valid_scores_included", "metrics": metrics(after), "costs": costs, "rows": after,
                               "validity": "Exploratory retry-aware view; not original single-attempt result; all failure and retry costs retained"},
        }
        for name, data in views.items():
            (out / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        b = views["one-retry.json"]["metrics"]
        (out / "README.md").write_text(
            f"# {version.upper()} — 133 / 235 / 283\n\n"
            "This is the current three-task reporting view, aligned to original V6 task IDs. "
            "It is derived offline from recorded evaluations; no task has been rerun or relabelled by this view. "
            "Original four/five-task studies and negative results remain historical evidence.\n\n"
            "| Scored / planned | Normal final answers | TF | PE | ECS population |\n"
            "| --- | --- | ---: | ---: | ---: |\n"
            f"| {b['scored_actor_executions']}/27 | {b['normal_final_answers']}/27 | {b['TF_on_scored']:.3f} | {b['PE_on_scored']:.3f} | {b['ECS_population']:.3f} |\n\n"
            "Method: this summary includes one retry of failed knowledge updates and every valid resulting actor score. "
            "It is a post hoc supplement, with three actor repeats per task/stage; five judge ratings are not five actor executions. "
            "Providers, repeat counts and artifact protocols differ from historical V6, so this is a descriptive comparison.\n\n"
            f"Actual update+actor cost, including failed attempts and retries: USD {costs['retry_aware_deployment_usd']}. "
            "Judge and local CPU costs are separate.\n\n"
            "The displayed metrics come from [one-retry.json](one-retry.json). "
            "The [first-attempt record](first-attempt.json) is retained for audit, without a second headline table.\n\n"
            f"Sources are pinned to commit `{SOURCE_REF}` on the historical evaluation branch: "
            f"[first cohort](https://github.com/FAN0020/pe6203-tool-harness-adaptation/blob/{SOURCE_REF}/{FIRST_PATH}), "
            f"[once-retry cohort](https://github.com/FAN0020/pe6203-tool-harness-adaptation/blob/{SOURCE_REF}/{RETRY_PATH}). "
            "The source JSON hashes are recorded in both views. No later V6 development implementation is imported.\n\n"
            "Offline regeneration: `python scripts/build_three_task_views.py`. "
            "The pinned source commit must be available locally (fetch the historical evaluation branch if necessary).\n"
        )
        result[version] = {"first": views["first-attempt.json"]["metrics"], "one_retry": b}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(json.dumps(build(args.root.resolve()), ensure_ascii=False))


if __name__ == "__main__":
    main()

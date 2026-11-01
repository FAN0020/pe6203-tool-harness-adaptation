"""Pinned QI-V2 evaluation and offline, task-level handoff. No implicit API calls."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
from pe6203.costs import provider_usd  # noqa: E402
from pe6203.evaluation import ecs, judge_scores  # noqa: E402


def read(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def blob_sha(path):
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def check(root):
    protocol = read(root / "experiments/v2-eval-protocol.json")
    changed = [
        p
        for p, h in protocol["source_git_blob_sha"].items()
        if not (root / p).is_file() or blob_sha(root / p) != h
    ]
    cfg = read(root / "configs/course-benchmark-v1.3.json")
    updater = read(root / "configs/course-updater.json")
    names = {
        v[k] for v in [cfg["agent"], cfg["judge"], updater] for k in ("api_key_env", "base_url_env")
    }
    missing = sorted(k for k in names if not os.environ.get(k))
    lock = read(root / "configs/benchmark.lock.json")
    cache = root / ".cache/mcpevol"
    absent = ["upstream"] if not (cache / "upstream/.git").exists() else []
    absent += [
        v["directory"]
        for v in lock["stages"].values()
        if not (cache / v["directory"] / "node_modules").is_dir()
    ]
    return {
        "status": "ready_for_prepare" if not (changed or missing or absent) else "blocked",
        "source_mismatches": changed,
        "missing_environment_variables": missing,
        "missing_benchmark_installations": absent,
        "model_calls": 0,
        "planned_executions": 27,
        "planned_judge_ratings": 135,
        "strategy_commit": protocol["strategy_commit"],
        "baseline_main_commit": protocol["baseline_main_commit"],
    }


def costs(items):
    # No observation is unknown, not a measured zero. Retain partial known spend.
    present = [x for x in items if isinstance(x, dict)]
    unknown = sum(x is None or x.get("usd") is None for x in items)
    known = sum(
        x.get("usd") if x.get("usd") is not None else (x.get("known_usd") or 0) for x in present
    )
    return {
        "records": len(items),
        "known_usd": known if present else None,
        "usd": known if items and unknown == 0 else None,
        "unknown_usd_records": unknown,
        **{
            k: sum(x[k] for x in present)
            if items and len(present) == len(items) and all(x.get(k) is not None for x in present)
            else None
            for k in ("total_tokens", "seconds")
        },
    }


def csv_write(path, rows):
    if rows:
        with path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


def summarize(output):
    plan = read(output / "plan.json")
    if not plan or plan.get("suite", {}).get("suite_id") != "course-qi-v2-eval-20261101":
        raise ValueError(
            "Use a plan prepared with benchmark-v2-eval.json; no historical relabeling"
        )
    if sha(output / "plan.json") != (output / "plan.sha256").read_text().strip():
        raise ValueError("Frozen plan hash mismatch")
    cells = plan["cells"]
    expected = {
        (t, v, s, 0)
        for t in (133, 235, 283)
        for v in ("early", "middle", "late")
        for s in ("no_update", "full_rewrite", "selective_patch")
    }
    if (
        len(cells) != 27
        or {(c["task_id"], c["version"], c["strategy"], c["seed"]) for c in cells} != expected
    ):
        raise ValueError("Expected exactly the frozen 27 distinct cells")
    ledger = read(output / "experiment.json", {"cells": {}})
    for item in ledger["cells"].values():
        for p, h in item.get("files", {}).items():
            if not (output / p).is_file() or sha(output / p) != h:
                raise ValueError("Recorded evidence changed: " + p)
    dest = output / "v2-eval"
    dest.mkdir(exist_ok=True)
    rows, details, bycost = [], [], {}
    questions = {t["idx"]: t["question"] for t in plan["tasks"]}
    expected_hash = {t["task_id"]: t["question_sha256"] for t in plan["suite"]["tasks"]}
    for c in cells:
        d = output / "cells" / c["id"]
        result = read(d / "run/result.json", {})
        adaptation = read(d / "adaptation/adaptation.json", {})
        if result:
            operational = {"root", "output_dir", "adaptation_path", "knowledge_path", "update_cost"}
            actual_cfg = {k: v for k, v in result.get("config", {}).items() if k not in operational}
            expected_cfg = {k: v for k, v in plan["config"].items() if k not in operational}
            if actual_cfg != expected_cfg:
                raise ValueError("Execution settings differ from frozen plan: " + c["id"])
        if (
            c["strategy"] == "selective_patch"
            and adaptation
            and adaptation.get("pipeline_version") != "hybrid_v2"
        ):
            raise ValueError("Non-V2 adaptation in " + c["id"])
        trace = read(d / "run/raw_trace.json", {})
        events = trace.get("events", [])
        initial = next((e for e in events if e.get("type") == "initial_messages"), {})
        question = questions[c["task_id"]]
        messages = initial.get("messages", trace.get("trajectory_messages", []))
        actual = next((m.get("content") for m in messages if m.get("role") == "user"), None)
        question_ok = hashlib.sha256(question.encode()).hexdigest() == expected_hash[c["task_id"]]
        if not question_ok or (actual is not None and actual != question):
            raise ValueError("Original task mismatch in " + c["id"])
        payload = read(d / "run/EVAL" / f"{c['task_id']}.json")
        values, issue = (
            judge_scores(payload) if payload is not None else (None, "missing_judge_records")
        )
        if result.get("judge_status") != "complete":
            values, issue = None, "judge_not_complete"
        state = result.get("execution_status", "not_started")
        files = [
            {"path": str(p.relative_to(output)), "bytes": p.stat().st_size, "sha256": sha(p)}
            for p in sorted((d / "run/workspace").rglob("*"))
            if p.is_file() and not p.is_symlink()
        ]
        answer = trace.get("answer", "")
        tool_events = [e for e in events if e.get("type") == "tool_result"]
        row = {
            **c,
            "question_hash_matches": question_ok,
            "execution_prompt_matches": actual == question if actual is not None else None,
            "status": result.get(
                "status", "adaptation_failed" if adaptation.get("status") == "failed" else "pending"
            ),
            "execution_status": state,
            "normally_completed": state == "completed",
            "TF": values["TF"] if values else None,
            "PE": values["PE"] if values else None,
            "score_issue": issue,
            "answer_present": bool(answer.strip()),
            "workspace_files": len(files),
            "tool_calls": len(tool_events),
            "tool_errors": sum(bool(e.get("result", {}).get("isError")) for e in tool_events),
            "case_file": f"cases/{c['id']}.json",
        }
        cellcost = {
            "update": adaptation.get("cost"),
            **{role: result.get("cost", {}).get(role) for role in ("agent", "judge")},
        }
        bycost[c["id"]] = cellcost
        detail = {
            **row,
            "question": question,
            "final_answer": answer,
            "workspace_manifest": files,
            "tool_observations": tool_events,
            "cost": cellcost,
            "adaptation_errors": adaptation.get("validation", {}).get("errors", []),
            "trace_path": str((d / "run/raw_trace.json").relative_to(output)),
            "artifact_quality": "not_manually_reviewed",
        }
        write(dest / row["case_file"], detail)
        rows.append(row)
        details.append(detail)
    strategies = []
    for s in ("no_update", "full_rewrite", "selective_patch"):
        group = [r for r in rows if r["strategy"] == s]
        scored = [r for r in group if r["TF"] is not None]
        strategies.append(
            {
                "strategy": s,
                "planned": len(group),
                "started": sum(r["execution_status"] != "not_started" for r in group),
                "normally_completed": sum(r["normally_completed"] for r in group),
                "completion_rate_planned": sum(r["normally_completed"] for r in group) / len(group),
                "scored": len(scored),
                "TF_mean_available": statistics.mean(r["TF"] for r in scored) if scored else None,
                "PE_mean_available": statistics.mean(r["PE"] for r in scored) if scored else None,
                "all_nine_scored": len(scored) == 9,
                "cost": {
                    role: costs([bycost[r["id"]][role] for r in group])
                    for role in ("update", "agent", "judge")
                },
            }
        )
    preflight = [
        item for p in sorted((output / "preflight").glob("*.json")) for item in read(p, [])
    ]
    preflight_cost = costs(
        [
            {
                "usd": provider_usd(x.get("usage")),
                "total_tokens": (x.get("usage") or {}).get("total_tokens"),
                "seconds": x.get("seconds"),
            }
            for x in preflight
        ]
    )
    matched = []
    for t in (133, 235, 283):
        for v in ("early", "middle", "late"):
            group = [r for r in rows if r["task_id"] == t and r["version"] == v]
            if all(r["TF"] is not None for r in group):
                matched.extend(group)
    ecs_rows = []
    for s in ("no_update", "full_rewrite", "selective_patch"):
        for t in (133, 235, 283):
            vals = [r["TF"] for r in rows if r["strategy"] == s and r["task_id"] == t]
            ecs_rows.append(
                {
                    "task": t,
                    "strategy": s,
                    "ECS_population": ecs(vals) if all(v is not None for v in vals) else None,
                }
            )
    summary = {
        "status": "complete" if all(r["TF"] is not None for r in rows) else "incomplete",
        "planned_executions": 27,
        "scored_executions": sum(r["TF"] is not None for r in rows),
        "strategies": strategies,
        "matched_three_method_cells": len(matched) // 3,
        "matched_results": [
            {
                "strategy": s,
                **{
                    k: statistics.mean(r[k] for r in matched if r["strategy"] == s)
                    if matched
                    else None
                    for k in ("TF", "PE")
                },
            }
            for s in ("no_update", "full_rewrite", "selective_patch")
        ],
        "ecs": ecs_rows,
        "preflight_cost": preflight_cost,
        "notes": [
            "Five ratings assess one execution.",
            "Completion means runner reached a final answer; artifact correctness needs review.",
            "Available-case means have explicit denominators; compare matched cells when incomplete.",
            "Unknown costs remain null. Preflight cost is separate.",
        ],
    }
    write(dest / "summary.json", summary)
    csv_write(dest / "runs.csv", rows)
    lines = [
        "# QI-V2 evaluation",
        "",
        f"Status: {summary['status']}; scored {summary['scored_executions']}/27 executions.",
        "",
        "| Method | Completed / planned | Scored | TF available | PE available |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in strategies:
        lines.append(
            f"| {r['strategy']} | {r['normally_completed']}/9 | {r['scored']} | {r['TF_mean_available']} | {r['PE_mean_available']} |"
        )
    lines += [
        "",
        "Each case JSON contains the original question, prompt match, full answer, workspace hashes, tool observations and cost.",
        "Normal completion does not certify product correctness. See summary.json for matched comparisons, ECS and separate costs.",
    ]
    (dest / "README.md").write_text("\n".join(lines) + "\n")
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["check", "prepare", "run", "report"])
    p.add_argument("--output", type=Path)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--limit", type=int)
    args = p.parse_args()
    if args.action == "check":
        result = check(ROOT)
        if args.output:
            write(args.output, result)
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "ready_for_prepare" else 2
    if not args.output:
        p.error("--output is required; use a fresh experiment directory")
    if args.action in ("prepare", "run"):
        state = check(ROOT)
        if state["status"] != "ready_for_prepare":
            print(json.dumps(state, indent=2))
            return 2
        from pe6203.experiment import prepare, report, run_experiment

        if args.action == "prepare":
            prepare(
                ROOT, args.output, None, repeats=1, suite_path="experiments/benchmark-v2-eval.json"
            )
            return 0
        if args.limit is not None and args.limit < 1:
            p.error("--limit must be positive")
        try:
            run_experiment(ROOT, args.output, resume=args.resume, limit=args.limit)
        finally:
            report(args.output)
            summary = summarize(args.output)
    else:
        summary = summarize(args.output)
    print(
        json.dumps({"status": summary["status"], "scored_executions": summary["scored_executions"]})
    )
    return 0 if summary["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())

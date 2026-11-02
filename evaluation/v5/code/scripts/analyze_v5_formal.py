"""Offline readout of the frozen V5 knowledge-only experiment; no API requests."""

from __future__ import annotations

import argparse
import ast
import csv
import json
import math
import re
import statistics
from collections import Counter
from decimal import Decimal
from pathlib import Path

from pe6203.benchmark import read_json, write_json
from pe6203.judge import ecs


def mean(values):
    return statistics.mean(values) if values and all(v is not None for v in values) else None


def add(values):
    return (
        str(sum((Decimal(str(v)) for v in values), Decimal(0)))
        if all(v is not None for v in values)
        else None
    )


def read_runs(root, plan):
    rows = []
    for cell in plan["cell_order"]:
        directory = root / "runs" / cell["id"]
        result_path = directory / "result.json"
        if not result_path.exists():
            rows.append(
                {**cell, "status": "not_run", "TF": None, "PE": None, "execution_status": "not_run"}
            )
            continue
        result = read_json(result_path)
        trace = read_json(directory / "raw_trace.json")
        events = trace["events"]
        proposals = [e for e in events if e.get("type") == "tool_result"]
        calls = [
            (e["call"]["function"]["name"], e["call"]["function"]["arguments"]) for e in proposals
        ]
        repeated = sum(n - 1 for n in Counter(calls).values())
        row = {
            **cell,
            **result,
            "rounds": sum(e.get("type") == "agent_response" for e in events),
            "tool_calls": len(proposals),
            "tool_errors": sum(bool(e["result"].get("isError")) for e in proposals),
            "exact_repeat_calls": repeated,
            "agent_usd": result["cost"]["agent"].get("usd"),
            "agent_prompt_tokens": result["cost"]["agent"].get("prompt_tokens"),
            "agent_completion_tokens": result["cost"]["agent"].get("completion_tokens"),
            "judge_usd": result["cost"]["judge"].get("usd"),
        }
        rows.append(row)
    return rows


def parse_arguments(raw):
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return {"invalid_json_arguments": raw}


def audit_extract(root, rows, destination):
    """Checkable facts and review flags, not a new model-written success score."""
    bytask = {}
    facts = []
    for row in rows:
        p = root / "runs" / row["id"] / "raw_trace.json"
        if not p.exists():
            continue
        trace = read_json(p)
        answer = trace.get("answer", "")
        calls = [e for e in trace["events"] if e.get("type") == "tool_result"]
        code_blocks = re.findall(r"```(?:python|py)\s*\n(.*?)```", answer, re.S | re.I)
        static = []
        for code in code_blocks:
            try:
                tree = ast.parse(code)
                static.append(
                    {
                        "parse": "passed",
                        "builtin_eval_calls": sum(
                            isinstance(n, ast.Call)
                            and isinstance(n.func, ast.Name)
                            and n.func.id == "eval"
                            for n in ast.walk(tree)
                        ),
                    }
                )
            except SyntaxError as exc:
                static.append({"parse": "failed", "line": exc.lineno, "error": exc.msg})
        fact = {
            "cell": row["id"],
            "answer_characters": len(answer),
            "execution_status": row["execution_status"],
            "TF": row["TF"],
            "PE": row["PE"],
            "python_static_parse": static,
            "scope": "Static syntax only; no Python execution, safety proof, or repair feedback",
            "tool_calls": [
                {
                    "native_tool": row.get("model_tool_routes", {}).get(
                        e["call"]["function"]["name"]
                    ),
                    "arguments": parse_arguments(e["call"]["function"]["arguments"]),
                    "is_error": bool(e["result"].get("isError")),
                }
                for e in calls
            ],
        }
        facts.append(fact)
        bytask.setdefault(row["task_id"], []).append(
            "## "
            + row["id"]
            + "\n"
            + json.dumps(
                {
                    "TF": row["TF"],
                    "PE": row["PE"],
                    "tool_calls": row["tool_calls"],
                    "errors": row["tool_errors"],
                    "static": static,
                }
            )
            + "\n\n"
            + answer
            + "\n"
        )
    write_json(destination / "artifact-facts.json", facts)
    for task, texts in bytask.items():
        (destination / f"answers-{task}.md").write_text("\n".join(texts))


def analyze(root, destination):
    destination.mkdir(parents=True, exist_ok=True)
    plan = read_json(root / "plan.json")
    rows = read_runs(root, plan)
    summaries = []
    updates = {}
    for task in (430, 133, 90, 235):
        for stage in ("early", "middle", "late"):
            for arm in ("no_update", "selective_patch"):
                p = root / "adaptations" / str(task) / stage / arm / "adaptation.json"
                artifact = read_json(p) if p.exists() else {"status": "not_run", "cost": {}}
                updates[(task, stage, arm)] = artifact
                group = [
                    r
                    for r in rows
                    if r["task_id"] == task and r["stage"] == stage and r["strategy"] == arm
                ]
                update = artifact["cost"].get("usd")
                actor = mean([r.get("agent_usd") for r in group])
                summaries.append(
                    {
                        "task_id": task,
                        "stage": stage,
                        "strategy": arm,
                        "planned": 3,
                        "saved": sum(r["status"] != "not_run" for r in group),
                        "completed": sum(r["execution_status"] == "completed" for r in group),
                        "scored": sum(r["TF"] is not None and r["PE"] is not None for r in group),
                        "TF_mean": mean([r["TF"] for r in group]),
                        "TF_runs": [r["TF"] for r in group],
                        "PE_mean": mean([r["PE"] for r in group]),
                        "PE_runs": [r["PE"] for r in group],
                        "actor_usd_mean": actor,
                        "actor_usd_runs": [r.get("agent_usd") for r in group],
                        "actor_input_tokens_mean": mean(
                            [r.get("agent_prompt_tokens") for r in group]
                        ),
                        "actor_output_tokens_mean": mean(
                            [r.get("agent_completion_tokens") for r in group]
                        ),
                        "rounds_mean": mean([r.get("rounds") for r in group]),
                        "tool_calls_mean": mean([r.get("tool_calls") for r in group]),
                        "tool_errors_mean": mean([r.get("tool_errors") for r in group]),
                        "updater_status": artifact["status"],
                        "updater_usd_once": update,
                        "updater_input_tokens": artifact["cost"].get("prompt_tokens"),
                        "updater_calls": artifact["cost"].get("calls"),
                        "single_task_usd": float(Decimal(str(update)) + Decimal(str(actor)))
                        if actor is not None and update is not None
                        else None,
                        "three_repeat_deployment_usd": add(
                            [update] + [r.get("agent_usd") for r in group]
                        ),
                        "judge_usd": add([r.get("judge_usd") for r in group]),
                    }
                )
    comparisons = []
    for task in (430, 133, 90, 235):
        for stage in ("early", "middle", "late"):
            base = next(
                x
                for x in summaries
                if x["task_id"] == task and x["stage"] == stage and x["strategy"] == "no_update"
            )
            v5 = next(
                x
                for x in summaries
                if x["task_id"] == task
                and x["stage"] == stage
                and x["strategy"] == "selective_patch"
            )
            saved = (
                base["actor_usd_mean"] - v5["actor_usd_mean"]
                if base["actor_usd_mean"] is not None and v5["actor_usd_mean"] is not None
                else None
            )
            comparisons.append(
                {
                    "task_id": task,
                    "stage": stage,
                    "actor_usd_saving_mean": saved,
                    "single_task_usd_delta_v5_minus_nu": v5["single_task_usd"]
                    - base["single_task_usd"]
                    if v5["single_task_usd"] is not None and base["single_task_usd"] is not None
                    else None,
                    "equal_knowledge_control": stage == "early" or task == 235,
                    "algebraic_break_even_executions": math.ceil(v5["updater_usd_once"] / saved)
                    if stage != "early"
                    and task != 235
                    and saved is not None
                    and saved > 0
                    and v5["updater_usd_once"] > 0
                    else None,
                    "break_even_caveat": "Point estimate, assumes identical quality, stable marginal cost/cache and reusable unchanged knowledge; not a measured deployment threshold",
                }
            )
    evol = []
    for task in (430, 133, 90, 235):
        for arm in ("no_update", "selective_patch"):
            per_repeat = []
            for repeat in range(1, 4):
                scores = {
                    r["stage"]: r["TF"]
                    for r in rows
                    if r["task_id"] == task and r["strategy"] == arm and r["repeat"] == repeat
                }
                per_repeat.append({"repeat": repeat, **ecs(scores)})
            evol.append(
                {
                    "task_id": task,
                    "strategy": arm,
                    "per_repeat": per_repeat,
                    "upstream_population_mean": mean(
                        [x["upstream_population"] for x in per_repeat]
                    ),
                    "paper_sample_mean": mean([x["paper_sample"] for x in per_repeat]),
                }
            )
    receipts = [json.loads(s) for s in (root / "api/receipts.jsonl").read_text().splitlines()]
    accounting = {
        role: {
            "calls": sum(r["phase"] == role for r in receipts),
            "usd": add([r["usd"] for r in receipts if r["phase"] == role]),
            "prompt_tokens": sum(
                r.get("usage", {}).get("prompt_tokens", 0) for r in receipts if r["phase"] == role
            ),
            "completion_tokens": sum(
                r.get("usage", {}).get("completion_tokens", 0)
                for r in receipts
                if r["phase"] == role
            ),
        }
        for role in ("updater", "agent", "judge")
    }
    overall = {}
    for arm in ("no_update", "selective_patch"):
        group = [r for r in rows if r["strategy"] == arm]
        updates_usd = [x["updater_usd_once"] for x in summaries if x["strategy"] == arm]
        actor_usd = [r.get("agent_usd") for r in group]
        overall[arm] = {
            "planned": 36,
            "saved": sum(r["status"] != "not_run" for r in group),
            "completed": sum(r["execution_status"] == "completed" for r in group),
            "scored": sum(r["TF"] is not None for r in group),
            "TF_mean": mean([r["TF"] for r in group]),
            "PE_mean": mean([r["PE"] for r in group]),
            "actor_usd": add(actor_usd),
            "updater_usd": add(updates_usd),
            "deployment_cohort_usd": add(actor_usd + updates_usd),
            "tool_errors": sum(r.get("tool_errors", 0) for r in group),
        }
    write_json(
        destination / "summary.json",
        {
            "scope": plan["schema"],
            "planned": 72,
            "cell_summaries": summaries,
            "comparisons": comparisons,
            "ECS": evol,
            "overall": overall,
            "accounting": accounting,
            "total_known_usd": add([r["usd"] for r in receipts]),
            "unknown_charges": sum(r["usd"] is None for r in receipts),
        },
    )
    fields = [
        "id",
        "task_id",
        "stage",
        "strategy",
        "repeat",
        "status",
        "execution_status",
        "judge_status",
        "TF",
        "PE",
        "rounds",
        "tool_calls",
        "tool_errors",
        "agent_prompt_tokens",
        "agent_completion_tokens",
        "agent_usd",
        "judge_usd",
    ]
    with (destination / "trajectories.csv").open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    audit_extract(root, rows, destination)

    def f(value, digits=3):
        return f"{value:.{digits}f}" if value is not None else "NA"

    lines = [
        "# V5 formal knowledge-only evaluation",
        "",
        "Four selected original MCPEvol-Bench tasks, three environments, No Update vs V5, three independent actor executions per cell. Five official-rubric judge ratings per trajectory. Model repeats have no reproducibility seed. No extra Python execution/repair in either arm. Catalog-only V5; no independent source/probe bundle.",
        "",
        "| Arm | Saved / planned | Final answers | TF /10 | PE /10 | Actor USD | Update USD once | Cohort deployment USD |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for arm, o in overall.items():
        lines.append(
            f"| {arm} | {o['saved']}/36 | {o['completed']}/36 | {f(o['TF_mean'])} | {f(o['PE_mean'])} | {o['actor_usd']} | {o['updater_usd']} | {o['deployment_cohort_usd']} |"
        )
    lines += [
        "",
        "Update API charges are counted once per task/environment and reused across its three actor executions. Judge charges are evaluation overhead, excluded from deployment costs. Final-answer termination does not independently certify task completion. TF/PE are model-judged; five ratings are not five independent actor executions.",
        "",
        "| Task | Stage | TF NU → V5 | PE NU → V5 | Actor USD NU → V5 | V5 update USD | Single-task USD NU → V5 | Errors NU → V5 |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for task in (430, 133, 90, 235):
        for stage in ("early", "middle", "late"):
            n = next(
                s
                for s in summaries
                if s["task_id"] == task and s["stage"] == stage and s["strategy"] == "no_update"
            )
            v = next(
                s
                for s in summaries
                if s["task_id"] == task
                and s["stage"] == stage
                and s["strategy"] == "selective_patch"
            )
            lines.append(
                f"| {task} | {stage} | {f(n['TF_mean'])} → {f(v['TF_mean'])} | {f(n['PE_mean'])} → {f(v['PE_mean'])} | {f(n['actor_usd_mean'], 6)} → {f(v['actor_usd_mean'], 6)} | {f(v['updater_usd_once'], 6)} | {f(n['single_task_usd'], 6)} → {f(v['single_task_usd'], 6)} | {f(n['tool_errors_mean'], 2)} → {f(v['tool_errors_mean'], 2)} |"
            )
    lines += [
        "",
        "All cells use unmodified original questions. Official selected-task membership, question SHA256, upstream commit, release archive hashes and source/config hashes are saved in preflight.json and plan.json. Raw receipts include strict DigitalOcean-only routing and provider-reported usage/cost. Unknown costs remain null and stop new requests.",
        "",
        "Costs can vary with cache hits and answer lengths. The Early conditions and task235 have equal knowledge and are controls for variation, not evidence of an update benefit. Three repeats per cell do not support broad significance claims or a main-merge decision by themselves.",
        "",
        f"API accounting: {json.dumps(accounting)}. Total actual charged USD: {add([r['usd'] for r in receipts])}; unknown-charge requests: {sum(r['usd'] is None for r in receipts)}.",
        "",
        "See trajectories.csv for every actor execution, summary.json for individual repeats and both ECS conventions, artifact-facts.json for static checks, and answers-*.md for the exact final answers. Static parsing is not execution or a security proof.",
    ]
    (destination / "README.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"overall": overall, "accounting": accounting}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    analyze(args.input, args.output)

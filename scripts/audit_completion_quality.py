"""Read archived evidence without running agents, tools, code artifacts, or judges.

This is a factual review packet, not a new quality score or promotion decision.
Persisted task state, original ratings and terminal status remain separate.
"""

import argparse
import hashlib
import json
import statistics
import tarfile
from collections import Counter, defaultdict
from pathlib import Path


def numeric(value):
    return type(value) in (int, float)


def range_facts(tasks, field):
    values = [t[field] for t in tasks if numeric(t.get(field))]
    return {
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "known": len(values),
        "unknown": len(tasks) - len(values),
    }


def task_facts(store):
    tasks = store["tasks"]
    ids = {t["id"] for t in tasks}
    parents = {t["parentId"] for t in tasks if t.get("parentId") in ids}
    leaves = [t for t in tasks if t["id"] not in parents]
    hours = [t["estimatedHours"] for t in leaves if numeric(t.get("estimatedHours"))]
    return {
        "project_count": len(store.get("projects", [])),
        "task_count": len(tasks),
        "duplicate_ids": sorted(k for k, n in Counter(t["id"] for t in tasks).items() if n > 1),
        "parent_ids": sorted(parents),
        "leaf_ids": sorted(t["id"] for t in leaves),
        "dangling_parents": [
            {"id": t["id"], "parentId": t["parentId"]}
            for t in tasks
            if t.get("parentId") and t["parentId"] not in ids
        ],
        "complexity_all": range_facts(tasks, "complexity"),
        "complexity_leaves": range_facts(leaves, "complexity"),
        "leaf_hours": {"known_total": sum(hours), "unknown": len(leaves) - len(hours)},
        "tasks": tasks,
        "interpretation": (
            "Stored complexity values are declarations, not proof that a task is manageable. "
            "Parent/leaf classification uses actual parentId links, not names or tags. "
            "Missing fields remain unknown. Semantic scope and answer claims need review."
        ),
    }


def cell_facts(archive, names, result_member):
    def read(name):
        return json.load(archive.extractfile(name)) if name in names else None

    result = read(result_member)
    prefix = result_member.removesuffix("result.json")
    trace_member = prefix + "raw_trace.json"
    trace = read(trace_member) or {}
    calls, rounds, invalid = [], [], []
    events = trace.get("events", [])
    for event in events:
        if event["type"] == "agent_response":
            response = event.get("response") or {}
            choice = (response.get("choices") or [{}])[0]
            rounds.append(
                {
                    "round": event.get("round"),
                    "finish_reason": choice.get("finish_reason"),
                    "completion_tokens": (response.get("usage") or {}).get("completion_tokens"),
                    "tool_calls": len((choice.get("message") or {}).get("tool_calls") or []),
                }
            )
        if event["type"] != "tool_result":
            continue
        call = event["call"]
        raw_args = call["function"]["arguments"]
        try:
            arguments = json.loads(raw_args)
        except (ValueError, TypeError):
            arguments = None
            invalid.append(call.get("id"))
        calls.append(
            {
                "round": event.get("round"),
                "id": call.get("id"),
                "tool": call["function"]["name"],
                "arguments": arguments,
                "arguments_raw_if_invalid": raw_args if arguments is None else None,
                "is_error": event["result"].get("isError", False),
            }
        )
    cost = {}
    for role in ("agent", "judge", "update"):
        stage_cost = (result.get("cost") or {}).get(role) or {}
        total = stage_cost.get("usd")
        cost[role] = {"known_usd": stage_cost.get("known_usd", total), "total_usd": total}
    store_member = prefix + "workspace/.agentic-tools-mcp/tasks/tasks.json"
    store = read(store_member)
    answer = trace.get("answer")
    return {
        "cell_id": prefix.split("/cells/")[1].split("/")[0],
        "task_id": result["task_id"],
        "stage": result["version"],
        "strategy": result["strategy"],
        "execution_status": result.get("execution_status", "unknown"),
        "raw_stop": trace.get("stop"),
        "raw_exceeded": trace.get("exceeded"),
        "trace_available": trace_member in names,
        "has_final_answer": isinstance(answer, str) and bool(answer.strip()),
        "original_scores": {"TF": result.get("TF"), "PE": result.get("PE")},
        "tool_call_count": len(calls),
        "tool_error_count": sum(c["is_error"] is True for c in calls),
        "invalid_json_call_ids": invalid,
        "rounds": rounds,
        "calls": calls,
        "elapsed_seconds": max((e.get("elapsed_seconds", 0) for e in events), default=None),
        "cost": cost,
        "question": trace.get("question"),
        "answer": answer,
        "task_store": task_facts(store) if store else None,
        "evidence": {
            "result": result_member,
            "trajectory": trace_member if trace_member in names else None,
            "persisted_tasks": store_member if store else None,
        },
    }


def audit(path):
    with tarfile.open(path) as archive:
        names = {m.name for m in archive if m.isfile()}
        cells = [
            cell_facts(archive, names, n)
            for n in sorted(names)
            if "/cells/" in n and n.endswith("/run/result.json")
        ]
    if not cells:
        raise ValueError("No archived cell results found")
    grouped = defaultdict(list)
    for cell in cells:
        grouped[cell["strategy"]].append(cell)
    summary = {}
    for strategy, rows in grouped.items():
        # Updater artifacts can be shared by many cells: do not multiply their cost.
        role_costs = [r["cost"][role] for r in rows for role in ("agent", "judge")]
        score_values = {
            key: [r["original_scores"][key] for r in rows if numeric(r["original_scores"][key])]
            for key in ("TF", "PE")
        }
        summary[strategy] = {
            "cells": len(rows),
            "completed": sum(r["execution_status"] == "completed" for r in rows),
            "statuses": dict(Counter(r["execution_status"] for r in rows)),
            "original_score_means": {
                key: statistics.mean(values) if values else None
                for key, values in score_values.items()
            },
            "original_score_counts": {key: len(values) for key, values in score_values.items()},
            "known_usd": sum(c["known_usd"] for c in role_costs if numeric(c["known_usd"])),
            "cost_scope": "Agent + judge only; shared update/probe/preflight costs are separate",
            "unreported_stage_totals": sum(c["total_usd"] is None for c in role_costs),
            "elapsed_seconds_sum": sum(r["elapsed_seconds"] or 0 for r in rows),
            "unknown_elapsed_cells": sum(r["elapsed_seconds"] is None for r in rows),
        }
    return {
        "schema_version": 1,
        "source_archive": str(path),
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "scope": "Factual offline extraction; no new judge scores or quality/promotion decision",
        "new_model_calls": 0,
        "summary": summary,
        "cells": cells,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument(
        "--output", type=Path, required=True, help="New directory; never overwritten"
    )
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; preserve it and choose a new directory")
    data = audit(args.archive)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "facts.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(args.output), "summary": data["summary"]}))


if __name__ == "__main__":
    main()

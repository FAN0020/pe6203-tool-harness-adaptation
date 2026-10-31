"""Run the six preregistered retention diagnostics, never replacing an execution."""

import argparse
import copy
import json
import statistics
from collections import Counter
from pathlib import Path

from pe6203.benchmark import read_json, write_json
from pe6203.evaluation import judge_scores
from pe6203.experiment import (
    configure_runtime,
    freeze_files,
    pending_judging,
    sha,
    verify_files,
    writer_lock,
)
from pe6203.judge import save_once
from pe6203.runner import resume_judging, run

ROOT = Path.cwd()
OUTPUT = ROOT / "results/raw/course-v1.3-retention-diagnostic-20261031"
FORMAL = ROOT / "results/raw/course-v1.3-final-20261031"


def check():
    plan = read_json(OUTPUT / "plan.json")
    assert sha(OUTPUT / "plan.json") == (OUTPUT / "plan.sha256").read_text().strip()
    assert plan["config"] == read_json(ROOT / "configs/course-benchmark-v1.3.json")
    verify_files(ROOT, read_json(FORMAL / "plan.json")["files"])
    assert sha(ROOT / plan["source_knowledge"]) == plan["source_sha256"]
    arms = {}
    for arm, expected in plan["knowledge_sha256"].items():
        assert sha(OUTPUT / f"{arm}.json") == expected
        arms[arm] = read_json(OUTPUT / f"{arm}.json")
    early = read_json(ROOT / "results/raw/finalized-trial-20261031/catalogs/235/early.json")
    assert (
        sha(ROOT / "results/raw/finalized-trial-20261031/catalogs/235/early.json")
        == plan["early_sha256"]
    )
    expected = copy.deepcopy(arms["rewrite"])
    originals = {(t["server_id"], t["name"]): t for t in early["tools"]}
    differences = 0
    for tool in expected["tools"]:
        description = originals[tool["server_id"], tool["name"]]["description"]
        differences += description != tool["description"]
        tool["description"] = description
    assert expected == arms["rollback_descriptions"] and differences == 28
    assert Counter(c["arm"] for c in plan["cells"]) == {"rewrite": 3, "rollback_descriptions": 3}
    return plan


def summarize(plan):
    rows = []
    for cell in plan["cells"]:
        directory = OUTPUT / "cells" / cell["id"]
        result_path = directory / "result.json"
        row = {**cell, "status": "pending"}
        if result_path.exists():
            result = read_json(result_path)
            eval_path = directory / "EVAL/235.json"
            scores, issue = (
                judge_scores(read_json(eval_path)) if eval_path.exists() else (None, "missing_eval")
            )
            tf, pe = (scores["TF"], scores["PE"]) if scores else (None, None)
            trace = read_json(directory / "raw_trace.json")
            calls = [e for e in trace["events"] if e["type"] == "tool_result"]
            maps = [e for e in calls if "map" in e["call"]["function"]["name"]]
            row.update(
                status=result["status"],
                execution_status=result["execution_status"],
                TF=tf,
                PE=pe,
                score_issue=issue,
                cost=result["cost"],
                tool_calls=len(calls),
                tool_errors=sum(bool(e["result"].get("isError")) for e in calls),
                map_calls=maps,
                chosen_tools=dict(Counter(e["call"]["function"]["name"] for e in calls)),
                answer=trace["answer"],
            )
        rows.append(row)
    aggregate = {}
    for arm in plan["knowledge_sha256"]:
        selected = [r for r in rows if r["arm"] == arm and r.get("TF") is not None]
        aggregate[arm] = {"complete_ratings": len(selected)}
        for field in ["TF", "PE", "tool_calls", "tool_errors"]:
            values = [r[field] for r in selected]
            aggregate[arm][field] = {
                "values": values,
                "mean": statistics.mean(values) if values else None,
                "range": [min(values), max(values)] if values else None,
            }
    result = {
        "kind": plan["kind"],
        "rows": rows,
        "arms": aggregate,
        "limits": "Three independent executions per arm; no provider seed; exposed diagnostic, not main benchmark or proof from one low score.",
    }
    write_json(OUTPUT / "summary.json", result)
    print(json.dumps(aggregate, ensure_ascii=False), flush=True)
    return result


def execute(plan):
    assert read_json(FORMAL / "summary.json")["scored"] == 27, "Finish main matrix first"
    configure_runtime(ROOT)
    driver = {"sha256": sha(Path(__file__)), "plan_sha256": sha(OUTPUT / "plan.json")}
    manifest = OUTPUT / "driver-lock.json"
    if manifest.exists():
        assert read_json(manifest) == driver
    else:
        save_once(manifest, driver)
    ledger_path = OUTPUT / "ledger.json"
    ledger = read_json(ledger_path) if ledger_path.exists() else {"cells": {}}
    transport_failures = 0
    for cell in plan["cells"]:
        directory = OUTPUT / "cells" / cell["id"]
        old = ledger["cells"].get(cell["id"], {})
        verify_files(OUTPUT, old.get("files", {}))
        result = None
        if pending_judging(directory, plan["config"]):
            print(cell["id"], "resume missing judge slots only", flush=True)
            _, result = resume_judging(directory)
        elif (directory / "result.json").exists():
            continue
        elif directory.exists():
            ledger["cells"][cell["id"]] = {"status": "interrupted_no_replay"}
            write_json(ledger_path, ledger)
            continue
        else:
            print(cell["id"], "starting fixed execution", flush=True)
            _, result = run(
                plan["task"],
                plan["stage"],
                "full_rewrite",
                cell["repeat"],
                {
                    **plan["config"],
                    "root": str(ROOT),
                    "output_dir": str(directory),
                    "knowledge_path": str(OUTPUT / f"{cell['arm']}.json"),
                    "update_cost": {
                        "method": "replay_frozen_knowledge_diagnostic",
                        "total_tokens": 0,
                        "seconds": 0,
                        "usd": 0,
                    },
                },
            )
        ledger["cells"][cell["id"]] = {
            "status": result["status"],
            "files": freeze_files(
                OUTPUT,
                [
                    p
                    for p in directory.rglob("*")
                    if p.is_file() and "workspace" not in p.relative_to(directory).parts
                ],
            ),
        }
        write_json(ledger_path, ledger)
        summarize(plan)
        if result.get("judge_recovery", {}).get("paused"):
            print("Paused: judge transport outage; preserve attempt budgets", flush=True)
            break
        transport_failures = (
            transport_failures + 1 if result.get("failure_category") == "model_transport" else 0
        )
        if transport_failures >= 2:
            print("Paused: consecutive transport failures", flush=True)
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["check", "run", "report"])
    args = parser.parse_args()
    frozen = check()
    if args.mode == "run":
        with writer_lock(OUTPUT):
            execute(frozen)
    elif args.mode == "report":
        summarize(frozen)
    else:
        print(
            "PASS: fixed six cells; only 28 descriptions differ; current source/config hashes match"
        )

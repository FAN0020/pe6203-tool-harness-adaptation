"""Single routing-fault intervention, with an unchanged controlled agent runtime.

This deliberately loads one invalid knowledge artifact through the research replay
entry point. Normal adaptation validation is not changed or disabled in production.
"""

import argparse
import asyncio
import copy
import json
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from pe6203.benchmark import read_json, source, write_json
from pe6203.experiment import configure_runtime, freeze_files, sha, verify_files, writer_lock
from pe6203.runner import prepare_tools, run
from pe6203.transport import sessions, snapshot

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PROPOSAL = ROOT / "results/evidence/routing-fault-proposal-20261031"
MAIN = ROOT / "results/raw/tool-migration-pilot-20261031"
OUTPUT = ROOT / "results/raw/routing-fault-check-20261031"


def check():
    plan = read_json(OUTPUT / "plan.json")
    assert sha(OUTPUT / "plan.json") == (OUTPUT / "plan.sha256").read_text().strip()
    verify_files(ROOT, plan["source_files"])
    verify_files(ROOT, plan["diagnostic_files"])
    verify_files(OUTPUT, plan["knowledge_files"])
    source(ROOT)
    control = read_json(OUTPUT / "knowledge/control.json")
    fault = read_json(OUTPUT / "knowledge/fault.json")
    changed = copy.deepcopy(control)
    tool = next(t for t in changed["tools"] if t["tool_id"] == "wikipedia-mcp::readArticle")
    tool["routing"]["tool_name"] = "read_article"
    assert changed == fault
    control_tools, control_routes = prepare_tools(control["tools"], "budget_feedback", "namespaced")
    fault_tools, fault_routes = prepare_tools(fault["tools"], "budget_feedback", "namespaced")
    assert control_tools == fault_tools
    different = [k for k in control_routes if control_routes[k] != fault_routes[k]]
    assert len(different) == 1 and different[0].startswith("readArticle__")
    return plan


def prepare():
    assert not OUTPUT.exists(), "Never overwrite a diagnostic"
    original = read_json(MAIN / "plan.json")
    verify_files(ROOT, original["files"])
    source(ROOT)
    OUTPUT.mkdir(parents=True)
    (OUTPUT / "knowledge").mkdir()
    for condition in ("control", "fault"):
        shutil.copyfile(
            PROPOSAL / f"{condition}-knowledge.json", OUTPUT / f"knowledge/{condition}.json"
        )
    config = copy.deepcopy(original["config"])
    config["spend_guard"]["ledger"] = str(OUTPUT.relative_to(ROOT) / "spend-ledger.json")
    assert config["spend_guard"]["limit_usd"] is None
    plan = {
        "kind": "controlled_fault_injection_scope_guard_ablation_not_natural_method_failure",
        "prepared_at": datetime.now(UTC).isoformat(),
        "authorization": "User active goal to continue necessary strategy research; latest instruction removes total monetary/trajectory ceilings. No deployment or communication.",
        "proposal": read_json(PROPOSAL / "plan.json"),
        "main_pilot_review": "results/evidence/tool-migration-pilot-20261031/quality-review.json",
        "task": next(t for t in original["tasks"] if t["idx"] == 430),
        "stage": "late",
        "config": config,
        "source_files": original["files"],
        "diagnostic_files": freeze_files(
            ROOT,
            [
                Path(__file__),
                PROPOSAL / "plan.json",
                PROPOSAL / "scope-guard-check.json",
                HERE / "protocol.json",
            ],
        ),
        "knowledge_files": freeze_files(OUTPUT, (OUTPUT / "knowledge").glob("*.json")),
        "cells": [
            {"id": "cell-001", "condition": "fault"},
            {"id": "cell-002", "condition": "control"},
        ],
        "order": "Fault then control, fixed before execution; no model seed; one trajectory per condition. No score-dependent repetitions.",
        "model_facing_tools_equal": True,
        "internal_strategy_label": "budget_feedback in both cells, used only to select the existing runtime; explicit knowledge snapshots define the intervention",
        "direct_replay": {
            "order": ["control", "fault"],
            "arguments": {"pageId": 210648},
            "server": "wikipedia-mcp",
            "only_read_only_public_calls": True,
        },
        "new_updater_or_preflight_calls": 0,
        "normal_validator": "Both scope and identity checks reject fault; bypass exists only via explicit research knowledge_path, not a production behavior change.",
    }
    write_json(OUTPUT / "plan.json", plan)
    (OUTPUT / "plan.sha256").write_text(sha(OUTPUT / "plan.json") + "\n")
    check()
    print("Prepared paired routing intervention; no model or tool calls", flush=True)


async def replay(plan):
    target = OUTPUT / "same-input-replay.json"
    assert not target.exists(), "Never overwrite direct replay"
    lock, _ = source(ROOT)
    rows = []
    with tempfile.TemporaryDirectory(prefix="pe6203-routing-replay-") as work:
        async with sessions(
            ROOT, "late", plan["task"]["servers"], work, OUTPUT / "replay.stderr.log", 30
        ) as clients:
            catalog = await snapshot(clients, "late", lock["commit"])
            assert catalog == read_json(MAIN / "catalogs/430/late.json")
            write_json(OUTPUT / "catalog.json", catalog)
            for condition in plan["direct_replay"]["order"]:
                knowledge = read_json(OUTPUT / f"knowledge/{condition}.json")
                _, routes = prepare_tools(knowledge["tools"], "budget_feedback", "namespaced")
                alias = next(n for n in routes if n.startswith("readArticle__"))
                route = routes[alias]
                row = {
                    "condition": condition,
                    "model_tool_name": alias,
                    "route": route,
                    "arguments": plan["direct_replay"]["arguments"],
                    "time": datetime.now(UTC).isoformat(),
                }
                try:
                    result = await asyncio.wait_for(
                        clients[route["server_id"]].call_tool(route["tool_name"], row["arguments"]),
                        30,
                    )
                    row["result"] = result.model_dump(mode="json", exclude_none=True)
                except Exception as exc:
                    row["exception"] = f"{type(exc).__name__}: {exc}"
                rows.append(row)
                write_json(target, {"new_model_calls": 0, "observations": rows})
                print("Direct replay recorded:", condition, flush=True)


def execute(plan):
    with writer_lock(OUTPUT):
        state_path = OUTPUT / "state.json"
        state = read_json(state_path) if state_path.exists() else {"cells": {}}
        for cell in plan["cells"]:
            check()
            cell_id = cell["id"]
            if cell_id in state["cells"]:
                verify_files(OUTPUT, state["cells"][cell_id]["files"])
                continue
            directory = OUTPUT / "cells" / cell_id / "run"
            assert not directory.exists(), (
                "Interrupted trajectory preserved; no automatic agent replay"
            )
            write_json(
                directory.parent / "condition.json",
                {**cell, "plan_sha256": sha(OUTPUT / "plan.json")},
            )
            print(cell_id, "starting controlled trajectory", flush=True)
            _, result = run(
                430,
                "late",
                "budget_feedback",
                0,
                {
                    **plan["config"],
                    "root": str(ROOT),
                    "output_dir": str(directory),
                    "knowledge_path": str(OUTPUT / f"knowledge/{cell['condition']}.json"),
                    "experiment_kind": plan["kind"],
                    "diagnostic_plan_sha256": sha(OUTPUT / "plan.json"),
                    "update_cost": {
                        "method": "replay_frozen_controlled_diagnostic",
                        "total_tokens": 0,
                        "seconds": 0,
                        "usd": 0,
                    },
                },
            )
            state["cells"][cell_id] = {
                "status": result["status"],
                "files": freeze_files(
                    OUTPUT, [p for p in directory.parent.rglob("*") if p.is_file()]
                ),
            }
            write_json(state_path, state)
            print(
                json.dumps(
                    {
                        "cell": cell_id,
                        "status": result["status"],
                        "execution_status": result["execution_status"],
                        "TF": result["TF"],
                        "PE": result["PE"],
                    }
                ),
                flush=True,
            )
            assert result["status"] == "evaluated", (
                "Incomplete run preserved; investigate before continuing"
            )
            assert read_json(directory / "environment-metadata.json") == read_json(
                OUTPUT / "catalog.json"
            )
        print("Both diagnostic conditions finished; no automatic expansion", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "check", "replay", "run"])
    args = parser.parse_args()
    configure_runtime(ROOT)
    if args.mode == "prepare":
        prepare()
    else:
        frozen = check()
        if args.mode == "replay":
            asyncio.run(replay(frozen))
        elif args.mode == "run":
            from dotenv import load_dotenv

            load_dotenv(ROOT / ".env")
            execute(frozen)
        else:
            print(
                "Verified exact one-field intervention and identical model-facing tools; no calls"
            )

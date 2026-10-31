"""Exactly four approved controlled trajectories using the frozen main runtime."""

import argparse
import asyncio
import copy
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DELIVERY = Path(__file__).resolve().parent
OUTPUT = ROOT / "results/raw/course-targeted-diagnostics-20261031"
RUNTIME = OUTPUT / "frozen-source"
MAIN = ROOT / "results/raw/course-v1.3-final-20261031"
ARCHIVE = ROOT / "submission/evidence/source-main-12d693c.tar.gz"
U_SOURCE = MAIN / "cells/task133-late-selective_patch-r0/run/knowledge.json"
O_SOURCE = (
    ROOT
    / "results/raw/selective-search-v1.1-development-20261031/cells/task133-middle-linked_notes-r0/run/knowledge.json"
)
NOTE = "validate_syntax now accepts optional detailed and allow_variables flags; evaluate's validate_only remains a separate syntax-only path, so choose based on whether evaluation is also wanted."


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tool(k, identity):
    return next(t for t in k["tools"] if t["tool_id"] == identity)


def omitted(k):
    k = copy.deepcopy(k)
    s = tool(k, "math-mcp::validate_syntax")["parameters"]
    del s["properties"]["allow_variables"]
    s["required"].remove("allow_variables")
    return k


def reverted(k):
    k = copy.deepcopy(k)
    t = tool(k, "math-mcp::evaluate")
    assert t["usage_rules"] == [NOTE]
    t["usage_rules"] = []
    return k


def runtime_imports():
    sys.path[:0] = [str(RUNTIME / "src"), str(RUNTIME)]
    import pe6203.runner
    from pe6203.experiment import configure_runtime

    configure_runtime(ROOT)
    assert Path(pe6203.runner.__file__).is_relative_to(RUNTIME)


def verify_main_inputs():
    main = read(MAIN / "plan.json")
    for name, expected in main["files"].items():
        location = RUNTIME if name.startswith(("src/", "integration/")) else ROOT
        assert sha(location / name) == expected, name
    return main


async def capture_catalogs(task, lock):
    from pe6203.transport import sessions, snapshot

    for stage in ["middle", "late"]:
        with tempfile.TemporaryDirectory(prefix="pe6203-diagnostic-catalog-") as d:
            work = Path(d)
            async with sessions(ROOT, stage, task["servers"], work, work / "stderr.log") as clients:
                catalog = await snapshot(clients, stage, lock["commit"])
        assert catalog == read(MAIN / f"catalogs/133/{stage}.json"), stage
        write(OUTPUT / f"catalogs/133/{stage}.json", catalog)


def prepare():
    expected = next(
        x["sha256"]
        for x in read(ROOT / "submission/SHA256SUMS.json")
        if x["path"] == "evidence/source-main-12d693c.tar.gz"
    )
    assert sha(ARCHIVE) == expected
    OUTPUT.mkdir(parents=True, exist_ok=False)
    with tarfile.open(ARCHIVE) as archive:
        archive.extractall(RUNTIME, filter="data")
    runtime_imports()
    main = verify_main_inputs()
    from pe6203.benchmark import load_task, source
    from pe6203.runner import credentials
    from pe6203.transport import server_profiles

    lock, upstream = source(ROOT)
    task = load_task(upstream, 133)
    config = read(ROOT / "configs/course-benchmark-v1.3.json")
    assert config == main["config"]
    endpoints = {role: credentials(config[role])[1] for role in ["agent", "judge"]}
    assert all(endpoints[r] == main["endpoints"][r] for r in endpoints)
    asyncio.run(capture_catalogs(task, lock))
    write(OUTPUT / "task.json", task)
    (OUTPUT / "knowledge").mkdir()
    shutil.copyfile(U_SOURCE, OUTPUT / "knowledge/under_complete.json")
    write(OUTPUT / "knowledge/under_omitted.json", omitted(read(U_SOURCE)))
    shutil.copyfile(O_SOURCE, OUTPUT / "knowledge/over_note.json")
    write(OUTPUT / "knowledge/over_reverted.json", reverted(read(O_SOURCE)))
    server_files = {}
    profiles = server_profiles(ROOT, lock)
    for stage in ["middle", "late"]:
        for server in task["servers"]:
            package = (
                ROOT
                / ".cache/mcpevol"
                / lock["stages"][stage]["directory"]
                / "node_modules"
                / server
            )
            assert (package / profiles[server]["entry"]).is_file()
            for p in sorted(package.rglob("*")):
                if p.is_file() and not p.is_symlink():
                    server_files[str(p.relative_to(ROOT))] = sha(p)
    plan = {
        "kind": "approved_controlled_diagnostic_not_main_benchmark",
        "prepared_at": datetime.now(UTC).isoformat(),
        "approval": {
            "user_reply": "批准",
            "scope": "Four trajectories in submission/diagnostic-options.html; no expansion or deployment",
            "proposal_sha256": sha(ROOT / "submission/diagnostic-options.html"),
        },
        "runtime_source": "12d693c archive; exact main-run source hashes",
        "source_archive_sha256": expected,
        "driver_sha256": sha(Path(__file__)),
        "task": task,
        "config": config,
        "endpoints": endpoints,
        "sources": {str(p.relative_to(ROOT)): sha(p) for p in [U_SOURCE, O_SOURCE]},
        "knowledge_sha256": {p.stem: sha(p) for p in sorted((OUTPUT / "knowledge").glob("*.json"))},
        "catalog_sha256": {
            stage: sha(OUTPUT / f"catalogs/133/{stage}.json") for stage in ["middle", "late"]
        },
        "server_files": server_files,
        "runtime_versions": {
            "python": platform.python_version(),
            "node": subprocess.check_output(
                [os.environ["MCPEVOL_NODE"], "--version"], text=True
            ).strip(),
            "platform": platform.platform(),
        },
        "cells": [
            {"id": "under_omitted", "stage": "late", "kind": "controlled_fault_injection"},
            {"id": "under_complete", "stage": "late", "kind": "fault_injection_control"},
            {"id": "over_reverted", "stage": "middle", "kind": "single_rule_rollback_control"},
            {"id": "over_note", "stage": "middle", "kind": "historical_linked_notes_replay"},
        ],
        "order": "Under: omitted then complete; over: reverted then note. Frozen before execution; no provider seed.",
        "internal_runner_strategy_label": "selective_patch is only the pinned engine's accepted routing label; these are controlled diagnostics, never natural main-method cases",
        "treatments": {
            "under": "Remove only validate_syntax.parameters.properties.allow_variables and its required-list entry",
            "over": "Revert only evaluate.usage_rules to []; three other archived rule changes remain",
        },
        "limits": {
            "max_trajectories": 4,
            "judge_slots_per_trajectory": 5,
            "updater_calls": 0,
            "review_projected_usd": 0.25,
            "review_projected_seconds": 1800,
            "stop_on_unknown_billing": True,
            "no_agent_replays": True,
        },
        "previous_evidence_manifest_sha256": sha(ROOT / "submission/evidence/corpus-manifest.json"),
        "limitations": [
            "Injected missing fact is not a natural original Selective Patch failure",
            "evaluate is related to validate_syntax; unchanged metadata does not imply unrelated knowledge",
            "One execution per condition; no provider seed or prevalence/statistical/general-causality claim",
            "Course acceptance of controlled faults is not presumed",
        ],
    }
    write(OUTPUT / "plan.json", plan)
    (OUTPUT / "plan.sha256").write_text(sha(OUTPUT / "plan.json") + "\n")
    check()
    shutil.copyfile(OUTPUT / "plan.json", DELIVERY / "plan.json")
    print(
        json.dumps(
            {
                "prepared": 4,
                "model_calls": 0,
                "source_inputs": "match main",
                "live_catalogs": "match archived Middle/Late",
                "server_files": len(server_files),
            }
        ),
        flush=True,
    )


def check():
    plan = read(OUTPUT / "plan.json")
    assert sha(OUTPUT / "plan.json") == (OUTPUT / "plan.sha256").read_text().strip()
    assert plan["driver_sha256"] == sha(Path(__file__))
    assert plan["source_archive_sha256"] == sha(ARCHIVE)
    verify_main_inputs()
    for key in ["sources", "server_files"]:
        for name, expected in plan[key].items():
            assert sha(ROOT / name) == expected, name
    for name, expected in plan["knowledge_sha256"].items():
        assert sha(OUTPUT / f"knowledge/{name}.json") == expected, name
    for stage, expected in plan["catalog_sha256"].items():
        assert sha(OUTPUT / f"catalogs/133/{stage}.json") == expected, stage
    assert len(plan["cells"]) == len({c["id"] for c in plan["cells"]}) == 4
    assert omitted(read(OUTPUT / "knowledge/under_complete.json")) == read(
        OUTPUT / "knowledge/under_omitted.json"
    )
    assert reverted(read(OUTPUT / "knowledge/over_note.json")) == read(
        OUTPUT / "knowledge/over_reverted.json"
    )
    return plan


def summarize(plan):
    rows = []
    for cell in plan["cells"]:
        directory = OUTPUT / "cells" / cell["id"] / "run"
        row = {**cell, "status": "pending"}
        if (directory / "result.json").exists():
            result = read(directory / "result.json")
            trace = read(directory / "raw_trace.json")
            calls = [e for e in trace["events"] if e["type"] == "tool_result"]
            row.update(
                status=result["status"],
                execution_status=result["execution_status"],
                TF=result["TF"],
                PE=result["PE"],
                seconds=result["seconds"],
                cost=result["cost"],
                calls=[
                    {"round": e["round"], "call": e["call"], "observation": e["result"]}
                    for e in calls
                ],
                tool_calls=len(calls),
                tool_errors=sum(bool(e["result"].get("isError")) for e in calls),
                answer=trace.get("answer", ""),
            )
        rows.append(row)
    finished = [r for r in rows if "cost" in r]
    known = sum(
        (r["cost"].get(role) or {}).get("known_usd", 0) or 0
        for r in finished
        for role in ["agent", "judge"]
    )
    summary = {
        "kind": plan["kind"],
        "rows": rows,
        "finished": len(finished),
        "known_usd": known,
        "unknown_cost_cells": [r["id"] for r in finished if r["cost"]["usd"] is None],
        "seconds": sum(r["seconds"] for r in finished),
    }
    write(OUTPUT / "summary.json", summary)
    print(
        json.dumps(
            {
                "finished": len(finished),
                "known_usd": known,
                "unknown_cost_cells": summary["unknown_cost_cells"],
                "cells": [
                    {
                        k: r.get(k)
                        for k in [
                            "id",
                            "status",
                            "execution_status",
                            "TF",
                            "PE",
                            "tool_calls",
                            "tool_errors",
                        ]
                    }
                    for r in rows
                ],
            }
        ),
        flush=True,
    )
    return summary


def execute(plan):
    from pe6203.experiment import freeze_files, verify_files, writer_lock
    from pe6203.runner import credentials, run

    assert all(
        credentials(plan["config"][r])[1] == plan["endpoints"][r] for r in ["agent", "judge"]
    )
    ledger_path = OUTPUT / "ledger.json"
    with writer_lock(OUTPUT):
        ledger = read(ledger_path) if ledger_path.exists() else {"cells": {}}
        if ledger.get("stop_reason"):
            raise RuntimeError("Frozen review stop: " + ledger["stop_reason"])
        for cell in plan["cells"]:
            check()
            parent = OUTPUT / "cells" / cell["id"]
            directory = parent / "run"
            old = ledger["cells"].get(cell["id"])
            if old:
                verify_files(OUTPUT, old["files"])
                continue
            if directory.exists():
                raise RuntimeError(
                    "Interrupted directory preserved; no agent replay: " + cell["id"]
                )
            write(
                parent / "condition.json",
                {**cell, "plan_sha256": sha(OUTPUT / "plan.json"), "not_main_benchmark": True},
            )
            print(cell["id"] + ": starting one approved execution", flush=True)
            _, result = run(
                133,
                cell["stage"],
                "selective_patch",
                0,
                {
                    **plan["config"],
                    "root": str(ROOT),
                    "output_dir": str(directory),
                    "knowledge_path": str(OUTPUT / f"knowledge/{cell['id']}.json"),
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
            ledger["cells"][cell["id"]] = {
                "status": result["status"],
                "files": freeze_files(
                    OUTPUT,
                    [
                        p
                        for p in parent.rglob("*")
                        if p.is_file() and "workspace" not in p.relative_to(parent).parts
                    ],
                ),
            }
            summary = summarize(plan)
            n = summary["finished"]
            if summary["unknown_cost_cells"]:
                ledger["stop_reason"] = "unknown billing requires review"
            elif result["status"] != "evaluated":
                ledger["stop_reason"] = (
                    "incomplete execution/judging requires review; no agent replay"
                )
            elif summary["known_usd"] / n * 4 > 0.25:
                ledger["stop_reason"] = "projected cost above $0.25"
            elif summary["seconds"] / n * 4 > 1800:
                ledger["stop_reason"] = "projected runtime above 30 minutes"
            elif read(directory / "environment-metadata.json") != read(
                OUTPUT / f"catalogs/133/{cell['stage']}.json"
            ):
                ledger["stop_reason"] = "live metadata changed"
            write(ledger_path, ledger)
            if ledger.get("stop_reason"):
                print("STOP: " + ledger["stop_reason"], flush=True)
                return
        print("STOP: all four approved trajectories are terminal; no expansion", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "check", "run", "report"])
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare()
    else:
        runtime_imports()
        frozen = check()
        if args.mode == "run":
            execute(frozen)
        elif args.mode == "report":
            summarize(frozen)
        else:
            print("PASS: exact treatments and main-runtime hashes; no model calls")

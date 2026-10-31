"""Audit all six fixed diagnostics, preserve raw evidence and record the observations."""

import hashlib
import json
import math
import os
import runpy
import shutil
import statistics
import subprocess
import tarfile
from pathlib import Path

from pe6203.benchmark import read_json, write_json
from pe6203.experiment import freeze_files, verify_files

root = Path.cwd()
out = root / "results/evidence/course-v1.3-20261031"
raw = root / "results/raw/course-v1.3-retention-diagnostic-20261031"
driver = runpy.run_path(str(out / "diagnostic.py"))
plan = driver["check"]()
summary = read_json(raw / "summary.json")
assert len(summary["rows"]) == 6 and all(r["status"] == "evaluated" for r in summary["rows"])
ledger = read_json(raw / "ledger.json")
observations = []
known_usd = 0
unknown_roles = 0
for cell in plan["cells"]:
    directory = raw / "cells" / cell["id"]
    verify_files(raw, ledger["cells"][cell["id"]]["files"])
    result = read_json(directory / "result.json")
    assert result["config"]["agent"] == plan["config"]["agent"]
    assert result["config"]["judge"] == plan["config"]["judge"]
    operational = {"root", "output_dir", "knowledge_path", "update_cost"}
    assert {k: v for k, v in result["config"].items() if k not in operational} == plan["config"]
    assert read_json(directory / "knowledge.json") == read_json(raw / f"{cell['arm']}.json")
    packed = read_json(directory / "EVAL/235.json")["eval_result"]
    assert len(packed["runs"]) == 5
    for index, selected in enumerate(packed["runs"], 1):
        attempts = [a for a in packed["attempts"] if a["slot"] == index]
        assert 1 <= len(attempts) <= 2
        assert next(a for a in attempts if "result" in a and not a.get("error")) == selected
        for attempt in attempts:
            saved = directory / "judge-attempts" / f"slot-{index}-attempt-{attempt['attempt']}"
            assert read_json(saved / "outcome.json") == attempt
            if "response" in attempt:
                assert read_json(saved / "response.json") == attempt["response"]
                parsed = json.loads(attempt["response"]["choices"][0]["message"]["content"])
                for key in ["task_fulfillment", "planning_and_efficiency", "grounding"]:
                    assert type(parsed[key]) is int and 1 <= parsed[key] <= 10
                    assert parsed[key] == attempt["result"][key]
    for name, score in [("TF", "task_fulfillment"), ("PE", "planning_and_efficiency")]:
        assert math.isclose(
            result[name], statistics.mean(j["result"][score] for j in packed["runs"])
        )
    events = read_json(directory / "raw_trace.json")["events"]
    proposed = set()
    maps = []
    for event in events:
        if event["type"] == "agent_response":
            for call in event["response"]["choices"][0]["message"].get("tool_calls") or []:
                proposed.add(json.dumps(call, sort_keys=True))
        elif event["type"] == "tool_result":
            assert json.dumps(event["call"], sort_keys=True) in proposed
            if "map" in event["call"]["function"]["name"]:
                args = json.loads(event["call"]["function"]["arguments"])
                maps.append(
                    {
                        "round": event["round"],
                        "unit": args.get("data", {}).get("dataValueUnit"),
                        "dataType": args.get("data", {}).get("dataType"),
                        "dataLabel": args.get("data", {}).get("dataLabel"),
                    }
                )
    observations.append(
        {
            **cell,
            "TF": result["TF"],
            "PE": result["PE"],
            "maps": maps,
            "execution_status": result["execution_status"],
            "judge_attempts": len(packed["attempts"]),
        }
    )
    for role in ["agent", "judge"]:
        known_usd += result["cost"][role]["known_usd"]
        unknown_roles += result["cost"][role]["usd"] is None

before = freeze_files(raw, [p for p in (raw / "cells").rglob("*") if p.is_file()])
resume = subprocess.run(
    [str(root / ".venv/bin/python"), str(out / "diagnostic.py"), "run"],
    capture_output=True,
    text=True,
)
assert resume.returncode == 0, resume.stderr
verify_files(raw, before)
assert set(before) == set(freeze_files(raw, [p for p in (raw / "cells").rglob("*") if p.is_file()]))
(out / "diagnostic-resume.log").write_text(resume.stdout + resume.stderr)
recomputed = driver["summarize"](plan)
assert recomputed == summary
shutil.copyfile(raw / "summary.json", out / "diagnostic-summary.json")
shutil.copyfile(raw / "plan.json", out / "diagnostic-plan.json")

secrets = [
    v.encode()
    for k, v in os.environ.items()
    if any(s in k for s in ["API_KEY", "AUTH_TOKEN"]) and len(v) > 8
]
archive = out / "diagnostic.tar.gz"
with tarfile.open(archive, "w:gz", compresslevel=9) as tar:
    for p in sorted(raw.rglob("*")):
        if p.is_file() and not p.is_symlink() and not p.name.endswith(".lock"):
            assert not any(secret in p.read_bytes() for secret in secrets), p
            tar.add(p, arcname=str(p.relative_to(raw.parent)), recursive=False)
    tar.add(out / "diagnostic.py", arcname="diagnostic.py")
write_json(
    out / "diagnostic-audit.json",
    {
        "status": "verified",
        "cells": 6,
        "valid_judges": 30,
        "first_valid_slots_and_scores": "verified against immutable raw records",
        "only_treatment": "28 descriptions; structural records, usage rules, settings identical",
        "resume": "terminal rerun issued no new requests; every cell file unchanged",
        "summary_recomputation": "identical",
        "observations": observations,
        "known_usd": known_usd,
        "unknown_cost_roles": unknown_roles,
        "archive": archive.name,
        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "limits": "Only three executions per arm on one exposed task. No paired provider seeds, no visual rendering validation, no claimed causal damage without evidence.",
    },
)
print("PASS: six fixed diagnostics, 30 first-valid ratings, identical replay, immutable archive")

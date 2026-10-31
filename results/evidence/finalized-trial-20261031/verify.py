"""Read-only audit and archive of this frozen trial; run from repository root."""

import hashlib
import json
import math
import os
import shutil
import statistics
import subprocess
import tarfile
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from pe6203.benchmark import load_task, source
from pe6203.judge import official_prompt
from pe6203.runner import prepare_tools
from pe6203.selective import METADATA_DIFF_FIELDS, diff_catalogs

root = Path.cwd()
trial = root / "results/raw/finalized-trial-20261031"
out = root / "results/evidence/finalized-trial-20261031"


def read(p):
    return json.loads(p.read_text())


def write(p, d):
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n")


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def same(x, y):
    assert (x is None and y is None) or (
        x is not None and y is not None and math.isclose(x, y, rel_tol=1e-10, abs_tol=1e-10)
    ), (x, y)


plan = read(trial / "plan.json")
summary = read(trial / "summary.json")
analysis = read(trial / "analysis/summary.json")
assert len(summary["rows"]) == 27 and all(
    r["status"] not in ["pending", "running"] for r in summary["rows"]
)
lock, upstream = source(root)
assert sha(trial / "plan.json") == (trial / "plan.sha256").read_text().strip()
for name, digest in plan["files"].items():
    assert sha(root / name) == digest, name
stages = ["early", "middle", "late"]
methods = ["no_update", "full_rewrite", "selective_patch"]
tasks = {t["task_id"]: load_task(upstream, t["task_id"]) for t in plan["suite"]["tasks"]}
for t in plan["suite"]["tasks"]:
    assert (
        hashlib.sha256(tasks[t["task_id"]]["question"].encode()).hexdigest() == t["question_sha256"]
    )
assert {(c["task_id"], c["version"], c["strategy"]) for c in plan["cells"]} == {
    (t, v, s) for t in tasks for v in stages for s in methods
}
assert {c["seed"] for c in plan["cells"]} == {0}
operational = {"root", "output_dir", "adaptation_path", "knowledge_path", "update_cost"}
expected = {k: v for k, v in plan["config"].items() if k not in operational}
observations = []
models = set()
protocols = set()
scores = {}
valid_judges = judge_attempts = 0
measurement = []
budget = []
for c in plan["cells"]:
    d = trial / "cells" / c["id"]
    r = read(d / "run/result.json")
    a = read(d / "adaptation/adaptation.json")
    k = read(d / "adaptation/knowledge.json")
    old = read(trial / "catalogs" / str(c["task_id"]) / "early.json")
    target = read(trial / "catalogs" / str(c["task_id"]) / (c["version"] + ".json"))
    assert a["status"] == "validated"
    assert {key: v for key, v in r["config"].items() if key not in operational} == expected
    assert (
        r["benchmark_commit"] == lock["commit"]
        and r["dataset_revision"] == lock["dataset_revision"]
    )
    assert (
        r["knowledge_sha256"] == hashlib.sha256(json.dumps(k, sort_keys=True).encode()).hexdigest()
    )
    assert a["output"]["knowledge_file_sha256"] == sha(d / "adaptation/knowledge.json")
    assert read(d / "run/environment-metadata.json") == target
    tools, routes = prepare_tools(k["tools"], c["strategy"], plan["config"]["tool_name_policy"])
    assert r["model_tool_routes"] == routes
    before = {x["tool_id"]: x for x in old["tools"]}
    after = {x["tool_id"]: x for x in k["tools"]}
    current = {x["tool_id"]: x for x in target["tools"]}
    preserved = rebuilt = 0
    if c["strategy"] == "no_update" or c["version"] == "early":
        assert k == old
        preserved = len(before)
    elif c["strategy"] == "full_rewrite":
        assert set(after) == set(current)
        for tid in current:
            assert {f: v for f, v in after[tid].items() if f != "description"} == {
                f: v for f, v in current[tid].items() if f != "description"
            }
        audit = read(d / "adaptation/updater-audit.json")
        request = json.loads(audit["request"][1]["content"])
        response = audit["response"]
        assert len(audit["request"]) == 2 and set(request) == {"tools", "rewrite_checks"}
        assert request["tools"] == [
            {**t, "native_name": t["name"], "name": t["tool_id"]} for t in target["tools"]
        ]
        payload = json.loads(response["choices"][0]["message"]["content"])
        assert len(payload["tools"]) == len(current) and {
            x["name"] for x in payload["tools"]
        } == set(current)
        assert a["cost"]["calls"] >= 1
        models.add(response["model"])
        rebuilt = len(current)
    else:
        diff = diff_catalogs(old, target)
        assert set(after) == set(current)
        for tid in diff["unchanged_tool_ids"]:
            assert after[tid] == before[tid]
        for x in diff["changed"] + diff["added"]:
            assert all(
                after[x["tool_id"]][f] == current[x["tool_id"]][f] for f in METADATA_DIFF_FIELDS
            )
        assert (
            a["cost"]["calls"] == 0
            and a["formal_llm_rewrite"] is False
            and not a["validation"]["errors"]
            and not a.get("unresolved_items")
        )
        preserved = len(diff["unchanged_tool_ids"])
        rebuilt = len(diff["changed"]) + len(diff["added"])
    events = [json.loads(line) for line in (d / "run/events.jsonl").read_text().splitlines()]
    initial = next(e for e in events if e["type"] == "initial_messages")
    assert initial["messages"][1] == {"role": "user", "content": tasks[c["task_id"]]["question"]}
    proposals = set()
    calls = errors = 0
    names = set()
    validations = []
    retries = []
    for line, e in enumerate(events, 1):
        if e["type"] == "agent_response":
            models.add(e["response"]["model"])
            for call in e["response"]["choices"][0]["message"].get("tool_calls") or []:
                proposals.add((call["id"], call["function"]["name"], call["function"]["arguments"]))
            if e["response"]["choices"][0]["finish_reason"] == "length":
                budget.append(
                    {"cell": c["id"], "round": e["round"], "usage": e["response"].get("usage")}
                )
        elif e["type"] == "tool_result":
            call = e["call"]
            f = call["function"]
            assert (call["id"], f["name"], f["arguments"]) in proposals
            calls += 1
            names.add(f["name"])
            errors += bool(e["result"].get("isError"))
            if f["name"].startswith("validate_syntax__"):
                args = json.loads(f["arguments"])
                validations.append(
                    {
                        "line": line,
                        "round": e["round"],
                        "allow_variables_present": "allow_variables" in args,
                        "allow_variables": args.get("allow_variables"),
                        "error": bool(e["result"].get("isError")),
                    }
                )
        elif e["type"] == "request_retry":
            retries.append(
                {
                    "role": e["role"],
                    "error_type": e["error_type"],
                    "failed_attempt": e["failed_attempt"],
                }
            )
        elif e["type"] == "judge_result" and e.get("response"):
            models.add(e["response"]["model"])
    protocols.add(r["protocol_sha256"])
    valid = total = 0
    ep = d / "run/EVAL" / f"{c['task_id']}.json"
    answer = d / "run/ANSWER" / f"{c['task_id']}.json"
    if answer.exists():
        trace = read(answer)
        assert trace["involved_tools"] == tools
    else:
        assert r["execution_status"] == "failed"
    if ep.exists():
        judges = read(ep)["eval_result"]["runs"]
        total = len(judges)
        for ji, j in enumerate(judges, 1):
            assert (
                official_prompt(
                    upstream,
                    tasks[c["task_id"]],
                    target["tools"],
                    trace["trajectory_messages"],
                    trace["answer"],
                    j["dimension_order"],
                )
                == (d / "run" / f"judge-prompt-{ji}.txt").read_text()
            )
            ok = (
                isinstance(j.get("result"), dict)
                and not j.get("error")
                and all(
                    type(j["result"].get(f)) is int and 1 <= j["result"][f] <= 10
                    for f in ["task_fulfillment", "planning_and_efficiency", "grounding"]
                )
            )
            valid += ok
            if ok:
                raw = j["response"]["choices"][0]["message"]["content"].strip()
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
                parsed = json.loads(raw)
                assert all(
                    parsed[f] == j["result"][f]
                    for f in ["task_fulfillment", "planning_and_efficiency", "grounding"]
                )
            else:
                measurement.append(
                    {
                        "cell": c["id"],
                        "judge_run": ji,
                        "error": j.get("error"),
                        "finish_reason": ((j.get("response", {}).get("choices") or [{}])[0]).get(
                            "finish_reason"
                        ),
                    }
                )
        if valid == total == 5:
            scores[c["task_id"], c["version"], c["strategy"]] = {
                f: sum(j["result"][key] for j in judges) / 5
                for f, key in [("TF", "task_fulfillment"), ("PE", "planning_and_efficiency")]
            }
    valid_judges += valid
    judge_attempts += total
    observations.append(
        {
            "cell": c["id"],
            "task": c["task_id"],
            "stage": c["version"],
            "strategy": c["strategy"],
            "preserved_records": preserved,
            "rebuilt_or_patched_records": rebuilt,
            "model_selected_tool_calls": calls,
            "chosen_tools": sorted(names),
            "tool_errors": errors,
            "valid_judges": valid,
            "judge_attempts": total,
            "status": r["status"],
            "execution_status": r["execution_status"],
            "validate_syntax_calls": validations,
            "request_retries": retries,
            "failure_category": r.get("failure_category"),
            "causes": r.get("causes"),
        }
    )
assert models == {plan["config"]["agent"]["model"]} and len(protocols) == 1
matched = {v: [t for t in tasks if all((t, v, m) in scores for m in methods)] for v in stages}
for row in analysis["main_results"]:
    ids = matched[row["stage"]]
    assert row["matched_tasks"] == row["matched_cells"] == len(ids)
    for f in ["TF", "PE"]:
        same(
            row[f],
            statistics.mean(scores[t, row["stage"], row["strategy"]][f] for t in ids)
            if ids
            else None,
        )
complete = [t for t in tasks if all(t in matched[v] for v in stages)]
for row in analysis["ecs"]:
    values = []
    for t in complete:
        ts = [scores[t, v, row["strategy"]]["TF"] for v in stages]
        mu = sum(ts) / 3
        variance = sum((x - mu) ** 2 for x in ts)
        values.append((mu - math.sqrt(variance / 3), mu - math.sqrt(variance / 2)))
    assert row["matched_triplets"] == len(complete)
    for key, i in [("upstream_population", 0), ("paper_sample", 1)]:
        same(row[key], statistics.mean(x[i] for x in values) if values else None)
for row in analysis["recovery_retention"]:
    ids = [
        t["task_id"]
        for t in plan["suite"]["tasks"]
        if t["task_id"] in matched[row["stage"]]
        and t["transitions"][row["stage"]]["label"] == row["subgroup"]
    ]
    assert row["matched_tasks"] == row["matched_cells"] == len(ids)
    same(
        row["delta_vs_no_update_same_stage"],
        statistics.mean(
            scores[t, row["stage"], row["strategy"]]["TF"]
            - scores[t, row["stage"], "no_update"]["TF"]
            for t in ids
        )
        if ids
        else None,
    )
for row in analysis["update_cost"]:
    costs = [
        read(trial / "cells" / c["id"] / "adaptation/adaptation.json")["cost"]
        for c in plan["cells"]
        if c["strategy"] == row["strategy"]
    ]
    assert row["unique_artifacts"] == len(costs)
    for src, dest in [("total_tokens", "tokens"), ("seconds", "seconds"), ("usd", "usd")]:
        vals = [x.get(src) for x in costs]
        same(row[dest + "_total"], sum(vals) if all(x is not None for x in vals) else None)
write(
    out / "artifact-audit.json",
    {
        "checked_cells": len(observations),
        "actual_models": sorted(models),
        "common_protocol_hashes": sorted(protocols),
        "immutable_plan_sources": "passed",
        "original_questions": "passed",
        "same_controls": "passed",
        "knowledge_strategy_semantics": "passed",
        "tool_selection": "Every dispatched call traced to model response; final blocked cell dispatched no tools",
        "judge_records": {"valid": valid_judges, "attempted": judge_attempts, "planned": 135},
        "execution_counts": dict(Counter(x["execution_status"] for x in observations)),
        "observations": observations,
    },
)
write(
    out / "metrics-audit.json",
    {
        "arithmetic": "passed: independently recomputed raw means, matched stage means, population/sample ECS, recovery/retention and update costs without evaluation.py helpers",
        "eligible_cells": len(scores),
        "matched_tasks_by_stage": matched,
        "ecs_task_ids": complete,
        "partial_judge_scores_used": False,
    },
)
write(
    out / "measurement-failures.json",
    {
        "judge_failures": measurement,
        "generation_budget_failures": budget,
        "transport_origin": "unconfirmed; APIConnectionError only",
        "semantic_score_review": "candidate-over-update.json; valid JSON does not establish judge calibration",
    },
)
print(
    "PASS: 27 artifact checks and independent arithmetic; eligible scores",
    len(scores),
    "ECS task IDs",
    complete,
)


def hashes():
    return {
        str(p.relative_to(trial)): sha(p)
        for name in ["cells", "preflight"]
        for p in (trial / name).rglob("*")
        if p.is_file()
    }


before = hashes()
resume = subprocess.run(
    ["./experiment", "run", "--output", str(trial), "--resume"], capture_output=True, text=True
)
assert resume.returncode == 2 and hashes() == before, (resume.returncode, resume.stderr)
assert f"benchmark | 已评分 {summary['scored']}/{summary['planned']}" in resume.stdout, (
    resume.stderr
)
(out / "resume.log").write_text(resume.stdout + resume.stderr)
print("PASS: terminal resume preserved all records and issued no new model/preflight requests")
for name in ["plan.json", "plan.sha256", "summary.json", "runs.csv"]:
    shutil.copyfile(trial / name, out / name)
shutil.copytree(trial / "analysis", out / "analysis", dirs_exist_ok=True)
secrets = [
    v.encode()
    for k, v in os.environ.items()
    if any(s in k for s in ["API_KEY", "AUTH_TOKEN"]) and len(v) > 8
]
archive = out / "raw-trial.tar.gz"
with tarfile.open(archive, "w:gz", compresslevel=9) as tar:
    for folder in [trial, root / "results/raw/final-trial-contracts-20261031"]:
        for p in sorted(folder.rglob("*")):
            if not p.is_file() or p.is_symlink() or p.name.endswith(".lock"):
                continue
            assert not any(s in p.read_bytes() for s in secrets), p
            tar.add(p, arcname=str(p.relative_to(root / "results/raw")), recursive=False)
    for name in plan["files"]:
        if name.startswith((".cache/", "results/raw/")):
            continue
        p = root / name
        assert not any(s in p.read_bytes() for s in secrets), p
        tar.add(p, arcname="implementation/" + name, recursive=False)
with tempfile.TemporaryDirectory(prefix="pe6203-replay-") as tmp:
    with tarfile.open(archive) as tar:
        tar.extractall(tmp, filter="data")
    extracted = Path(tmp) / trial.name
    env = {
        k: v
        for k, v in os.environ.items()
        if not any(s in k for s in ["API_KEY", "AUTH_TOKEN", "BASE_URL"])
    }
    code = 'import socket,sys\ndef forbidden(*a,**k):raise AssertionError("Unexpected network")\nsocket.socket.connect=forbidden\nsocket.socket.connect_ex=forbidden\nsocket.create_connection=forbidden\nfrom pe6203.experiment import main\nraise SystemExit(main(sys.argv[1],["report","--output",sys.argv[2]]))'
    replay = subprocess.run(
        [str(root / ".venv/bin/python"), "-c", code, str(root), str(extracted)],
        env=env,
        capture_output=True,
        text=True,
    )
    assert replay.returncode == 0, replay.stderr
    for name in ["summary.json", "analysis/summary.json"]:
        assert (extracted / name).read_bytes() == (trial / name).read_bytes()
print(
    "PASS: offline archive replay reproduced both summaries byte for byte without credentials/network"
)
write(
    out / "reproduction.json",
    {
        "verified_at": datetime.now(UTC).isoformat(),
        "archive": archive.name,
        "sha256": sha(archive),
        "bytes": archive.stat().st_size,
        "resume": "passed; all cell/preflight hashes unchanged",
        "offline_replay": "passed; socket blocked and credentials removed; byte-identical summary and analysis",
        "replay_command": "Extract raw-trial.tar.gz; ./experiment report --output <extraction>/finalized-trial-20261031",
        "original_driver_console_log": "Temporary /tmp log no longer available; complete per-cell JSONL, MCP stderr, prompts, raw responses and results retained in archive",
    },
)
p = out / "audit-progress.json"
if p.exists():
    p.unlink()

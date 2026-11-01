"""Prepare an isolated extension plan using verified native catalogs, without model calls."""

import argparse
import copy
import json
from datetime import UTC, datetime
from pathlib import Path

from pe6203.baselines import write_adaptation
from pe6203.benchmark import load_task, read_json, source, write_json
from pe6203.experiment import configure_runtime, freeze_files, model_config, sha
from pe6203.runner import credentials, prepare_tools

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent


def prepare(phase):
    protocol = read_json(BASE / "protocol.json")
    group = protocol["schedule"][phase]
    output = ROOT / "results/raw/extensions/magicui-log-dashboard-v1" / phase
    output.mkdir(parents=True, exist_ok=False)
    configure_runtime(ROOT)
    lock, upstream = source(ROOT)
    config = model_config(ROOT, protocol["model_config"])
    config["spend_guard"]["ledger"] = str(output.relative_to(ROOT) / "spend-ledger.json")
    updater = read_json(ROOT / protocol["updater_config"])
    endpoints = {
        role: credentials(settings)[1]
        for role, settings in {
            "agent": config["agent"],
            "judge": config["judge"],
            "updater": updater,
        }.items()
    }
    catalogs = read_json(ROOT / "tests/fixtures/native-argument-routing-catalogs.json")
    code = read_json(
        ROOT / "results/evidence/magicui-artifact-dependencies-20261101/file_roundtrip-catalog.json"
    )["tools"][0]
    reuse = ROOT / "results/evidence/native-argument-routing-updater-20261101"
    for version in ("early", "late"):
        cat = copy.deepcopy(catalogs[version])
        cat["tools"].insert(
            0,
            {
                "tool_id": "mcp-server-code-runner::run-code",
                "server_id": "mcp-server-code-runner",
                "version": version,
                "name": code["name"],
                "parameters": code["inputSchema"],
                "description": code["description"],
                "usage_rules": [],
                "output_schema": code["outputSchema"],
                "routing": {"server_id": "mcp-server-code-runner", "tool_name": code["name"]},
            },
        )
        cat["source"] = (
            "recorded_native_catalogs; code-runner identical released source across stages"
        )
        write_json(output / "catalogs" / str(group["task_id"]) / f"{version}.json", cat)
        write_json(
            output / "catalogs/235" / f"{version}.json",
            read_json(reuse / f"retention-{version}.json"),
        )
    feedback = read_json(ROOT / protocol["feedback"])
    write_json(output / "feedback.json", feedback)
    adaptations = {}
    review = []
    for task in (group["task_id"], 235):
        knowledge = {}
        for strategy in ("selective_patch", "native_argument_routing"):
            directory = output / "adaptations" / f"{task}-late-{strategy}"
            write_adaptation(
                output / "catalogs" / str(task) / "early.json",
                output / "catalogs" / str(task) / "late.json",
                strategy,
                directory,
                {"feedback": feedback["observations"]},
            )
            artifact = read_json(directory / "adaptation.json")
            assert artifact["status"] == "validated"
            knowledge[strategy] = read_json(directory / artifact["output"]["knowledge_path"])
            adaptations[f"{task}-late-{strategy}"] = str(
                (directory / "adaptation.json").relative_to(output)
            )
        sp, candidate = [knowledge[s] for s in ("selective_patch", "native_argument_routing")]
        a, b = [{t["tool_id"]: t for t in k["tools"]} for k in (sp, candidate)]
        delta = [(i, k) for i in a for k in a[i] if a[i][k] != b[i][k]]
        assert len(delta) == (0 if task == 235 else 7)
        assert all(k == "description" and i.startswith("@magicuidesign/mcp::") for i, k in delta)
        ta, ra = prepare_tools(sp["tools"], "selective_patch", "namespaced")
        tb, rb = prepare_tools(candidate["tools"], "native_argument_routing", "namespaced")
        assert ra == rb
        assert [t["function"]["parameters"] for t in ta] == [
            t["function"]["parameters"] for t in tb
        ]
        if task == 235:
            assert sp == candidate == read_json(output / "catalogs/235/early.json")
        review.append(
            {
                "task_id": task,
                "changed_fields": delta,
                "schemas_routes_equal": True,
                "retention_exact_K0": task == 235,
            }
        )
    paths = list((ROOT / "src/pe6203").rglob("*.py")) + list((ROOT / "integration").rglob("*.py"))
    paths += [p for p in BASE.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    paths += [
        ROOT / p
        for p in [
            protocol["updater_config"],
            protocol["feedback"],
            protocol["updater_spec"],
            "configs/benchmark.lock.json",
            "configs/server-profiles.json",
            "uv.lock",
            "pyproject.toml",
            "tests/fixtures/native-argument-routing-catalogs.json",
        ]
    ]
    # Source/runtime hashes frozen by the prior native probes are reused and checked here.
    for filename in (
        "magicui-argument-routing-probes-v1.json",
        "magicui-artifact-dependencies-v1.json",
    ):
        previous = read_json(ROOT / "experiments" / filename)
        for row in previous["source"]:
            if not row["path"].startswith(".cache/"):
                continue
            path = ROOT / row["path"]
            assert sha(path) == row["sha256"]
            paths.append(path)
    paths += list((output / "catalogs").rglob("*.json"))
    paths += [ROOT / ".cache/node-runtime/node_modules/node/bin/node"]
    plan = {
        "schema_version": "experiment-1",
        "kind": "controlled_extension_" + phase,
        "variant": "released_servers_controlled_synthetic_input",
        "created_at": datetime.now(UTC).isoformat(),
        "benchmark_commit": lock["commit"],
        "dataset_revision": lock["dataset_revision"],
        "cells": group["cells"],
        "tasks": [
            load_task(upstream, group["task_id"], BASE / f"task-{phase}.json"),
            load_task(upstream, 235),
        ],
        "config": config,
        "updater": updater,
        "judge_runs": 5,
        "files": freeze_files(ROOT, paths),
        "endpoints": endpoints,
        "formal_evaluation": False,
        "coverage": {},
        "limitations": [
            "Synthetic extension scores must never enter original benchmark aggregate.",
            "Same-coordinator blind review; not an independent human assessment.",
            "Late-only; ECS unavailable without matched Early/Middle scores.",
        ],
        "shared_adaptations": adaptations,
        "availability_preflight": True,
        "max_preflight_calls": 2,
        "stop_after_infrastructure_failures": 2,
    }
    write_json(output / "plan.json", plan)
    (output / "plan.sha256").write_text(sha(output / "plan.json") + "\n")
    write_json(
        output / "knowledge-lock.json",
        {
            "plan_sha256": sha(output / "plan.json"),
            "files": freeze_files(output, list((output / "adaptations").rglob("*.json"))),
        },
    )
    write_json(
        output / "knowledge-review.json",
        {
            "accepted": True,
            "lock_sha256": sha(output / "knowledge-lock.json"),
            "mechanism_spec": "ef97a48 unchanged",
            "checks": review,
            "model_calls": 0,
        },
    )
    print(
        json.dumps(
            {
                "phase": phase,
                "cells": len(group["cells"]),
                "knowledge_review": review,
                "model_calls": 0,
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["development", "validation-a", "validation-b"])
    prepare(parser.parse_args().phase)

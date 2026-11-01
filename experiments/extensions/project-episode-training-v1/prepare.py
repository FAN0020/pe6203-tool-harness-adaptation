"""Freeze exactly four original-SP synthetic training executions; no model calls."""
import copy
from datetime import UTC, datetime
from pathlib import Path

from pe6203.baselines import write_adaptation
from pe6203.benchmark import load_task, read_json, source, write_json
from pe6203.experiment import configure_runtime, freeze_files, model_config, sha
from pe6203.runner import credentials

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
OUT = ROOT / "results/raw/extensions/project-episode-training-v1"


def main():
    spec = read_json(BASE / "protocol.json")
    for name, digest in read_json(BASE / "data-manifest.json").items():
        assert sha(BASE / name) == digest
    OUT.mkdir(parents=True, exist_ok=False)
    configure_runtime(ROOT)
    lock, upstream = source(ROOT)
    config = model_config(ROOT, spec["model_config"])
    config.pop("fixture_dir", None)
    config.pop("task_context", None)
    config["spend_guard"]["ledger"] = str(OUT.relative_to(ROOT) / "spend-ledger.json")
    config["extension_tasks"] = {str(t): str(BASE.relative_to(ROOT) / f"task-{t}.json") for t in (900401, 900402)}
    updater = copy.deepcopy(read_json(ROOT / spec["updater_config"]))
    endpoints = {role: credentials(settings)[1] for role, settings in
                 {"agent": config["agent"], "judge": config["judge"], "updater": updater}.items()}
    catalogs = read_json(ROOT / "tests/fixtures/capability-withdrawal-catalogs.json")
    adaptations = {}
    for t in (900401, 900402):
        for stage in ("early", "late"):
            write_json(OUT / "catalogs" / str(t) / f"{stage}.json", catalogs[stage])
        dest = OUT / "adaptations" / f"{t}-late-selective_patch"
        write_adaptation(OUT / "catalogs" / str(t) / "early.json",
                         OUT / "catalogs" / str(t) / "late.json", "selective_patch", dest)
        assert read_json(dest / "adaptation.json")["status"] == "validated"
        adaptations[f"{t}-late-selective_patch"] = str((dest / "adaptation.json").relative_to(OUT))
    paths = list((ROOT / "src/pe6203").rglob("*.py")) + list((ROOT / "integration").rglob("*.py"))
    paths += [p for p in BASE.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    paths += [ROOT / p for p in (spec["model_config"], spec["updater_config"], "configs/benchmark.lock.json", "configs/server-profiles.json", "uv.lock", "pyproject.toml", "tests/fixtures/capability-withdrawal-catalogs.json", "tests/test_project_episode_projection.py")]
    paths += list((OUT / "catalogs").rglob("*.json"))
    paths += [ROOT / ".cache/node-runtime/node_modules/node/bin/node"]
    paths += list((ROOT / ".cache/mcpevol/iter5/node_modules/@pimzino/agentic-tools-mcp/dist").rglob("*.js"))
    paths += list((ROOT / "results/evidence/project-episode-learning-20261101").glob("*.py"))
    paths += [ROOT / "results/evidence/project-episode-learning-20261101/research-decision.json"]
    # Reuse native/runtime evidence, without rerunning native admission.
    paths += [ROOT / "results/evidence/native-batch-cost-diagnostic-20261101/decision.json"]
    plan = {"schema_version": "experiment-1", "kind": "controlled_extension_adaptation_training",
            "variant": "released_servers_controlled_synthetic_input", "created_at": datetime.now(UTC).isoformat(),
            "benchmark_commit": lock["commit"], "dataset_revision": lock["dataset_revision"],
            "cells": spec["schedule"], "tasks": [load_task(upstream, t, BASE / f"task-{t}.json") for t in (900401, 900402)],
            "config": config, "updater": updater, "judge_runs": 5, "files": freeze_files(ROOT, paths),
            "endpoints": endpoints, "formal_evaluation": False, "coverage": {},
            "limitations": ["Adaptation training only, not candidate performance or original benchmark evidence.", "Same-coordinator artifact review before revealing TF/PE; all methods are SP.", "Late-only; ECS null."],
            "shared_adaptations": adaptations, "availability_preflight": True, "max_preflight_calls": 2,
            "stop_after_infrastructure_failures": 2}
    write_json(OUT / "plan.json", plan)
    (OUT / "plan.sha256").write_text(sha(OUT / "plan.json") + "\n")
    write_json(OUT / "knowledge-lock.json", {"plan_sha256": sha(OUT / "plan.json"), "files": freeze_files(OUT, list((OUT / "adaptations").rglob("*.json")))})
    write_json(OUT / "knowledge-review.json", {"accepted": True, "lock_sha256": sha(OUT / "knowledge-lock.json"), "note": "Original SP on both fixed synthetic tasks; no new candidate, no updater calls; complete unchanged catalogs."})
    print(f"Frozen {len(plan['cells'])} cells, {len(plan['files'])} source/data files; model calls0")


if __name__ == "__main__":
    main()

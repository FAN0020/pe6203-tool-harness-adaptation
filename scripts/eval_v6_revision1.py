"""Frozen full five-task evaluation of the explicit V6-r1 implementation.

One update per task/stage, three independent actor executions. Original tasks,
rubric, Python tests, round limits and repair allowance are retained. No outcome
selection, fallback strategy, or score-based rerun is implemented.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import shutil
import subprocess
from copy import deepcopy
from pathlib import Path

from openai import AsyncOpenAI

from pe6203 import runner, selective_v6
from pe6203.baselines import write_adaptation
from pe6203.benchmark import digest, load_task, read_json, source, write_json
from pe6203.execution_control_v6 import VERSION as EXECUTION_VERSION
from pe6203.experiment import collect_catalogs, configure_runtime
from scripts import eval_five_task_supplement as supplement
from scripts import eval_v3_formal as common
from scripts import eval_v35_three_tasks as paired

TASKS = (133, 235, 283, 430, 90)


class Guard(supplement.Guard):
    def async_client(self, **client_options):
        client = AsyncOpenAI(**client_options)
        original = client.chat.completions.create

        async def guarded(**kwargs):
            artifact = kwargs.get("response_format", {}).get("json_schema", {}).get("name") == "artifact_v1_delivery"
            phase = "agent" if "tools" in kwargs or artifact else "judge"
            number, directory = self.begin(phase, kwargs)
            try:
                response = await original(**kwargs)
            except BaseException as exc:
                self.finish(number, directory, phase, error=exc)
                raise
            self.finish(number, directory, phase, response.model_dump(mode="json"))
            return response

        client.chat.completions.create = guarded
        return client


def prepare(root, out):
    if out.exists():
        raise ValueError("Full V6-r1 study requires a fresh output directory")
    configure_runtime(root)
    lock, upstream = source(root)
    out.mkdir(parents=True)
    asyncio.run(collect_catalogs(root, TASKS, out))
    for name in ("python-protocol.json", "python-task-context.txt"):
        shutil.copy2(root / "outputs/v6-revision1-frozen-inputs" / name, out / name)
    config = read_json(root / "configs/course-benchmark-v1.3.json")
    for role in ("agent", "judge"):
        config[role]["extra_body"] = deepcopy(common.ROUTING)
    config.update(request_retry={"max_retries": 0}, runtime=None,
                  v6_execution_control={"version": EXECUTION_VERSION})
    updater = read_json(root / "configs/course-updater.json")
    updater.update(allow_metadata_api=True, request_retry={"max_retries": 0})
    cells = []
    rng = random.Random(20261103)
    for repeat in (1, 2, 3):
        conditions = [(task, stage) for task in TASKS for stage in common.STAGES]
        rng.shuffle(conditions)
        for task, stage in conditions:
            cells.append({"id": f"{task}-{stage}-v6-r1-r{repeat}", "task_id": task,
                          "stage": stage, "arm": "v6", "strategy": "selective_patch",
                          "repeat": repeat, "seed": 300 + repeat,
                          "adaptation": f"adaptations/{task}/{stage}/v6/adaptation.json"})
    hashes = paired.source_hashes(root)
    # Freeze new modules even when preparing an uncommitted local revision.
    for folder in (root / "src/pe6203", root / "integration"):
        for path in folder.rglob("*.py"):
            hashes[str(path.relative_to(root))] = common.sha(path)
    hashes["scripts/eval_v6_revision1.py"] = common.sha(root / "scripts/eval_v6_revision1.py")
    hashes["scripts/eval_five_task_supplement.py"] = common.sha(root / "scripts/eval_five_task_supplement.py")
    plan = {"schema": "v6-r1-five-task-full-1", "frozen_at": common.now(),
            "implementation_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
            "implementation_revision": selective_v6.IMPLEMENTATION_REVISION,
            "benchmark_commit": lock["commit"],
            "tasks": {str(t): load_task(upstream, t) for t in TASKS},
            "source_files_sha256": hashes,
            "catalogs_sha256": {str(p.relative_to(out)): common.sha(p) for p in out.glob("catalogs/*/*.json")},
            "capability_evidence_sha256": {}, "model": common.MODEL,
            "provider_routing": common.ROUTING, "actor_and_judge": config, "updater": updater,
            "artifact_protocol_sha256": common.sha(out / "python-protocol.json"),
            "artifact_context_sha256": common.sha(out / "python-task-context.txt"),
            "acceptance": deepcopy(selective_v6.ACCEPTANCE),
            "acceptance_sha256": digest(selective_v6.ACCEPTANCE),
            "cost_policy": {"input_per_million": 0.3, "output_per_million": 1.2},
            "pricing_scope": "Reservation rates based on prior pinned DigitalOcean receipts; actual provider usage.cost remains controlling",
            "cell_order": cells, "trajectories_planned": 45, "ratings_per_trajectory": 5,
            "concurrency": 3, "budget_known_usd": 2,
            "budget_basis": "Operational USD2 stop; prior45-run-prorated costs below USD1, unknown costs stop new requests; not a user-imposed budget",
            "pilot": {"cell_id": "133-middle-v6-r1-r1", "gate": "saved trace and result, complete scoring, known pinned receipts; no minimum TF/PE and no score-based resampling"},
            "validity": {"new_revision": True, "old_results_overwritten": False,
                         "reruns": "No trajectory reruns, no update fallback; failed conditions retained",
                         "update_feedback": "No actor answers, artifact test feedback or judge scores into tool knowledge",
                         "artifact": "Original frozen Python protocol/context on133 only, original one repair; other tasks no Python contract",
                         "execution": "Explicit V6-only delivery control within original12generation rounds; no baseline changes",
                         "scope": "Full-system V6-r1, historical controls only; no claim of isolated knowledge-update effect"}}
    write_json(out / "plan.json", plan)
    return plan


def verify_inputs(root, out, plan):
    paired.verify(root, out, plan)
    if common.sha(out / "python-protocol.json") != plan["artifact_protocol_sha256"] or common.sha(out / "python-task-context.txt") != plan["artifact_context_sha256"]:
        raise ValueError("Frozen artifact tests or task interface changed")
    if digest(selective_v6.ACCEPTANCE) != plan["acceptance_sha256"]:
        raise ValueError("Admission acceptance changed")


def adapt_all(out, plan, guard):
    manifest = {}
    for task in TASKS:
        for stage in common.STAGES:
            directory = out / f"adaptations/{task}/{stage}/v6"
            common.CELL.set(f"update-{task}-{stage}-v6")
            try:
                artifact = write_adaptation(out / f"catalogs/{task}/early.json", out / f"catalogs/{task}/{stage}.json",
                                            "selective_patch", directory,
                                            {"selective_mode": "hybrid_v6", "updater": plan["updater"], "cost_policy": plan["cost_policy"]})
                print(json.dumps({"type": "adaptation", "task": task, "stage": stage,
                                  "status": artifact["status"], "cost": artifact["cost"]}), flush=True)
            except Exception as exc:
                write_json(directory / "evaluation-error.json", {"error_type": type(exc).__name__, "detail": str(exc)})
                print(json.dumps({"type": "adaptation_failed", "task": task, "stage": stage, "detail": str(exc)}), flush=True)
            for name in ("adaptation.json", "knowledge.json"):
                p = directory / name
                if p.exists():
                    manifest[str(p.relative_to(out))] = {"sha256": common.sha(p)}
            if guard.stopped:
                raise RuntimeError("Receipt guard stopped adaptation")
    write_json(out / "knowledge-freeze.json", {"frozen_at": common.now(), "files": manifest})


async def actors(root, out, plan, guard, cells):
    semaphore = asyncio.Semaphore(plan["concurrency"])
    freeze = read_json(out / "knowledge-freeze.json")["files"]

    async def one(cell):
        async with semaphore:
            directory = out / "runs" / cell["id"]
            if directory.exists():
                raise ValueError("Existing V6-r1 trajectory cannot be rerun")
            artifact = out / cell["adaptation"]
            if read_json(artifact)["status"] != "validated":
                write_json(out / "blocked-cells" / (cell["id"] + ".json"), {**cell, "status": "adaptation_failed_not_run"})
                return
            if read_json(artifact).get("implementation_revision") != plan["implementation_revision"]:
                raise ValueError("Execution control requires this exact V6-r1 knowledge revision")
            if common.sha(artifact) != freeze[cell["adaptation"]]["sha256"]:
                raise ValueError("Frozen knowledge changed")
            config = {**deepcopy(plan["actor_and_judge"]), "root": str(root), "output_dir": str(directory),
                      "adaptation_path": str(artifact), "evaluation_plan_sha256": common.sha(out / "plan.json")}
            if cell["task_id"] == 133:
                config["artifact_validation"] = read_json(out / "python-protocol.json")
                config["task_context"] = (out / "python-task-context.txt").read_text()
            common.CELL.set(cell["id"])
            print(json.dumps({"type": "start", "cell": cell["id"]}), flush=True)
            _, result = await runner.run_async(cell["task_id"], cell["stage"], "selective_patch", cell["seed"], config)
            print(json.dumps({"type": "finished", "cell": cell["id"], "status": result["status"],
                              "execution": result["execution_status"], "TF": result["TF"], "PE": result["PE"],
                              "artifact": (result.get("artifact_validation") or {}).get("status"),
                              "known_batch_usd": str(guard.known)}), flush=True)

    await asyncio.gather(*(one(c) for c in cells))


def summarize(out, plan):
    previous = paired.ARMS
    try:
        paired.ARMS = ("v6",)
        return paired.summarize(out, plan)
    finally:
        paired.ARMS = previous


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "execute", "summarize"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root, out = args.root.resolve(), args.output.resolve()
    if args.action == "prepare":
        p = prepare(root, out)
        print(json.dumps({"prepared": True, "planned": p["trajectories_planned"]}), flush=True)
        return
    plan = read_json(out / "plan.json")
    if args.action == "summarize":
        print(json.dumps(summarize(out, plan)["by_arm"]), flush=True)
        return
    verify_inputs(root, out, plan)
    if (out / "api").exists():
        raise ValueError("Existing evaluation cannot be resampled")
    common.credential_environment(None)
    guard = Guard(out / "api", plan["budget_known_usd"])
    runner.AsyncOpenAI = guard.async_client
    selective_v6.request_completion = guard.structured_updater
    try:
        adapt_all(out, plan, guard)
        pilot = next(c for c in plan["cell_order"] if c["id"] == plan["pilot"]["cell_id"])
        asyncio.run(actors(root, out, plan, guard, [pilot]))
        result_path = out / "runs" / pilot["id"] / "result.json"
        gate = result_path.exists() and read_json(result_path)["judge_status"] == "complete" and not guard.stopped
        write_json(out / "pilot-gate.json", {"passed": gate, "score_threshold": None, "no_resampling": True})
        if not gate:
            raise RuntimeError("Pilot protocol incomplete; remaining conditions not run")
        asyncio.run(actors(root, out, plan, guard, [c for c in plan["cell_order"] if c != pilot]))
    finally:
        summarize(out, plan)


if __name__ == "__main__":
    main()

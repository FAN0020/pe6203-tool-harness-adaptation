"""Fill task430/task90 gaps for V1/V2/V6, with fresh unchanged NU/FR controls.

Historical three-task records remain separate. This is a supplement, not a
claim that all versions were rerun together on five tasks.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import subprocess
from copy import deepcopy
from pathlib import Path

from openai import OpenAI

from integration import baselines as provider
from pe6203 import runner, selective_v6
from pe6203.baselines import write_adaptation
from pe6203.benchmark import digest, load_task, read_json, source, write_json
from pe6203.execution_v6 import diagnose
from pe6203.experiment import collect_catalogs, configure_runtime
from scripts import eval_v3_formal as common
from scripts import eval_v35_three_tasks as paired

TASKS = (430, 90)
ARMS = ("no_update", "full_rewrite", "v1", "v2", "v6")
MODES = {"v1": "deterministic_v1", "v2": "hybrid_v2", "v6": "hybrid_v6"}


def make_cells():
    cells = []
    rng = random.Random(20261103)
    for repeat in range(1, 4):
        conditions = [(task, stage) for task in TASKS for stage in common.STAGES]
        rng.shuffle(conditions)
        for index, (task, stage) in enumerate(conditions):
            offset = (index + repeat) % len(ARMS)
            arms = ARMS[offset:] + ARMS[:offset]
            for arm in arms:
                cells.append({"id": f"{task}-{stage}-{arm}-r{repeat}", "task_id": task,
                              "stage": stage, "arm": arm, "repeat": repeat, "seed": 100 + repeat,
                              "strategy": arm if arm in ("no_update", "full_rewrite") else "selective_patch",
                              "adaptation": f"adaptations/{task}/{stage}/{arm}/adaptation.json"})
    return cells


class Guard(common.ReceiptGuard):
    def structured_updater(self, messages, settings):
        if not settings["allow_metadata_api"]:
            raise ValueError("Metadata API opt-in missing")
        key, url = runner.credentials(settings)
        kwargs = {"model": common.MODEL, "messages": messages,
                  "temperature": settings["temperature"], "max_tokens": settings["max_tokens"],
                  "response_format": settings["response_format"], "extra_body": common.ROUTING}
        number, directory = self.begin("updater", kwargs)
        try:
            with OpenAI(api_key=key, base_url=url, timeout=settings["timeout"], max_retries=0) as client:
                response = client.chat.completions.create(**kwargs).model_dump(mode="json")
        except BaseException as exc:
            self.finish(number, directory, "updater", error=exc)
            raise
        self.finish(number, directory, "updater", response=response)
        return response


def prepare(root, out):
    if out.exists():
        raise ValueError("Use a fresh output directory")
    configure_runtime(root)
    lock, upstream = source(root)
    tasks = {str(t): load_task(upstream, t) for t in TASKS}
    out.mkdir(parents=True)
    asyncio.run(collect_catalogs(root, TASKS, out))
    config = read_json(root / "configs/course-benchmark-v1.3.json")
    for role in ("agent", "judge"):
        config[role]["extra_body"] = deepcopy(common.ROUTING)
    config.update(request_retry={"max_retries": 0}, runtime=None)
    updater = read_json(root / "configs/course-updater.json")
    updater.update(allow_metadata_api=True, request_retry={"max_retries": 0})
    hashes = paired.source_hashes(root)
    name = "scripts/eval_five_task_supplement.py"
    hashes[name] = common.sha(root / name)
    plan = {"schema": "five-task-missing-cells-supplement-1", "frozen_at": common.now(),
            "implementation_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
            "benchmark_commit": lock["commit"], "tasks": tasks,
            "source_files_sha256": hashes,
            "catalogs_sha256": {str(p.relative_to(out)): common.sha(p) for p in out.glob("catalogs/*/*.json")},
            "capability_evidence_sha256": {}, "model": common.MODEL,
            "provider_routing": common.ROUTING, "actor_and_judge": config,
            "updater": updater, "cell_order": make_cells(), "trajectories_planned": 90,
            "ratings_per_trajectory": 5, "concurrency": 4, "budget_known_usd": 2,
            "budget_basis": "Operational stop at USD2; prorated historical 108-run actual charge USD1.2777. Unknowns stop new requests; not a user-specified limit.",
            "knowledge": {"modes": MODES, "non_cumulative": "Each stage starts from Early K0",
                          "freezing": "One update per condition, reused across three independent actors",
                          "v1_identity": "Historical course V1.3 core; AST-equivalent to archived implementation excluding module docstring",
                          "v6_evidence": "Catalog-only on these new tasks; no task-derived probes"},
            "validity": {"scope": "Two newly added tasks; do not treat historical merged scores as a concurrent five-task experiment",
                         "controls": "No Update and Full Rewrite unchanged; frozen Early K0 checked",
                         "artifact": "Neither task requests Python; no Python artifact loop is applied to any arm",
                         "failures": "No resampling or overwrite; preserve failures and charges",
                         "time": "Task90 uses live date-dependent network responses; no reference answer substitution",
                         "v4": "excluded by owner instruction"}}
    write_json(out / "plan.json", plan)
    return plan


def adapt_all(out, plan, guard):
    manifest = {}
    for task in TASKS:
        for stage in common.STAGES:
            for arm in ARMS:
                directory = out / f"adaptations/{task}/{stage}/{arm}"
                common.CELL.set(f"update-{task}-{stage}-{arm}")
                context = {"updater": plan["updater"]}
                if arm in MODES:
                    context["selective_mode"] = MODES[arm]
                strategy = arm if arm in ("no_update", "full_rewrite") else "selective_patch"
                try:
                    artifact = write_adaptation(out / f"catalogs/{task}/early.json",
                                                out / f"catalogs/{task}/{stage}.json",
                                                strategy, directory, context)
                    if arm == "no_update" and read_json(directory / "knowledge.json") != read_json(out / f"catalogs/{task}/early.json"):
                        raise ValueError("No Update did not retain K0")
                    print(json.dumps({"type": "adaptation", "task": task, "stage": stage,
                                      "arm": arm, "status": artifact["status"], "cost": artifact["cost"]}), flush=True)
                except Exception as exc:
                    write_json(directory / "evaluation-error.json",
                               {"status": "failed", "error_type": type(exc).__name__, "detail": str(exc)})
                    print(json.dumps({"type": "adaptation_failed", "task": task, "stage": stage,
                                      "arm": arm, "detail": str(exc)}), flush=True)
                for name in ("adaptation.json", "knowledge.json"):
                    p = directory / name
                    if p.exists():
                        manifest[str(p.relative_to(out))] = {"sha256": common.sha(p)}
                if guard.stopped:
                    raise RuntimeError("Receipt guard stopped updates")
    write_json(out / "knowledge-freeze.json", {"frozen_at": common.now(), "files": manifest})


def diagnose_v6(out, plan):
    for cell in plan["cell_order"]:
        if cell["arm"] != "v6":
            continue
        run = out / "runs" / cell["id"]
        if not (run / "result.json").exists():
            continue
        artifact = out / cell["adaptation"]
        knowledge = read_json(artifact.parent / "knowledge.json")
        injected = read_json(run / "knowledge.json")["tools"] if (run / "knowledge.json").exists() else None
        trace = read_json(run / "raw_trace.json")
        result = read_json(run / "result.json")
        diagnosis = diagnose({"knowledge_sha256": digest(knowledge)}, knowledge, injected,
                             trace.get("events", []), result, name_policy="namespaced")
        write_json(run / "v6-post-run-diagnosis.json", diagnosis)


def summarize(out, plan):
    original = paired.ARMS
    try:
        paired.ARMS = ARMS
        return paired.summarize(out, plan)
    finally:
        paired.ARMS = original


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "execute", "summarize"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root, out = args.root.resolve(), args.output.resolve()
    if args.action == "prepare":
        plan = prepare(root, out)
        print(json.dumps({"prepared": True, "planned": plan["trajectories_planned"]}), flush=True)
        return
    plan = read_json(out / "plan.json")
    if args.action == "execute":
        paired.verify(root, out, plan)
        if (out / "api").exists() or (out / "knowledge-freeze.json").exists():
            raise ValueError("Existing execution cannot be rerun")
        common.credential_environment(None)
        guard = Guard(out / "api", plan["budget_known_usd"])
        runner.AsyncOpenAI = guard.async_client
        provider._request_completion = guard.updater
        selective_v6.request_completion = guard.structured_updater
        try:
            adapt_all(out, plan, guard)
            asyncio.run(common.actors(root, out, plan, guard))
            diagnose_v6(out, plan)
        finally:
            summarize(out, plan)
    else:
        print(json.dumps(summarize(out, plan)["by_arm"]), flush=True)


if __name__ == "__main__":
    main()

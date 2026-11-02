"""Frozen 4-task x 3-stage x 3-arm x 3-repeat V3 knowledge-only experiment.

Runs actual released MCP tools and real model/judge requests. Evaluator-only
routing/accounting instrumentation leaves both arms' actor policy unchanged.
Every trajectory runs once; bounded judge-format recovery is predeclared.
"""

from __future__ import annotations

import argparse
import asyncio
import contextvars
import hashlib
import json
import os
import random
import subprocess
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from openai import AsyncOpenAI, OpenAI

from integration import baselines as provider
from pe6203 import runner
from pe6203.baselines import write_adaptation
from pe6203.benchmark import read_json, source, write_json
from pe6203.capability import fingerprint
from pe6203.costs import provider_usd

TASKS = (430, 133, 90, 235)
STAGES = ("early", "middle", "late")
MODEL = "deepseek/deepseek-v4.1-flash-1017"
ROUTING = {
    "provider": {"only": ["DigitalOcean"], "allow_fallbacks": False, "require_parameters": True},
    "reasoning": {"enabled": False},
}
CELL = contextvars.ContextVar("evaluation_cell", default="preflight")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def now():
    return datetime.now(UTC).isoformat()


def credential_environment(path):
    # Read dotenv data without executing shell commands or printing values.
    values = {}
    for line in Path(path).read_text().splitlines() if path else []:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.removeprefix("export ").split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    key = os.environ.get("OPENROUTER_API_KEY") or values.get("OPENROUTER_API_KEY")
    if not key:
        raise ValueError("OPENROUTER_API_KEY is required in the private environment file")
    for role in ("AGENT", "JUDGE"):
        os.environ[f"{role}_API_KEY"] = key
        os.environ[f"{role}_BASE_URL"] = "https://openrouter.ai/api/v1"


class ReceiptGuard:
    def __init__(self, out, limit):
        self.out = Path(out)
        self.limit = Decimal(str(limit))
        self.known = Decimal("0")
        self.stopped = False
        self.counter = 0
        self.inflight = set()
        self.out.mkdir(parents=True, exist_ok=True)
        ledger = self.out / "receipts.jsonl"
        self.ledger = ledger
        self.rows = []
        if ledger.exists():
            for line in ledger.read_text().splitlines():
                row = json.loads(line)
                self.rows.append(row)
                self.counter = max(self.counter, row["request_number"])
                if row.get("usd") is not None:
                    self.known += Decimal(str(row["usd"]))
                if row.get("stop_reason"):
                    self.stopped = True
        requests = {p.parent.name for p in self.out.glob("request-*/request.json")}
        outcomes = {p.parent.name for p in self.out.glob("request-*/outcome.json")}
        if requests - outcomes:
            self.stopped = True
            raise ValueError("Interrupted API request has unknown billing; reconcile before resume")

    def begin(self, phase, kwargs):
        if self.stopped or self.known >= self.limit:
            raise RuntimeError("Receipt/budget guard stopped new requests")
        if (
            kwargs["model"] != MODEL
            or kwargs.get("extra_body", {}).get("provider") != ROUTING["provider"]
        ):
            raise ValueError("Frozen model/provider routing mismatch")
        self.counter += 1
        number = self.counter
        directory = self.out / f"request-{number:05}"
        directory.mkdir()
        write_json(
            directory / "request.json",
            {
                "request_number": number,
                "cell": CELL.get(),
                "phase": phase,
                "started_at": now(),
                "body": kwargs,
            },
        )
        self.inflight.add(number)
        return number, directory

    def finish(self, number, directory, phase, response=None, error=None):
        row = {
            "request_number": number,
            "cell": CELL.get(),
            "phase": phase,
            "finished_at": now(),
            "usd": None,
        }
        if response is not None:
            write_json(directory / "response.json", response)
            usage = response.get("usage") or {}
            row.update(
                id=response.get("id"),
                model=response.get("model"),
                provider=response.get("provider"),
                usage=usage,
                usd=provider_usd(usage),
            )
            if row["usd"] is None:
                row["stop_reason"] = "unknown_provider_charge"
            elif row["provider"] != "DigitalOcean" or row["model"] != MODEL:
                row["stop_reason"] = "unexpected_provider_or_model"
        else:
            row.update(error_type=type(error).__name__, stop_reason="request_failed_usage_unknown")
        if row["usd"] is not None:
            self.known += Decimal(str(row["usd"]))
        if row.get("stop_reason"):
            self.stopped = True
        row["cumulative_known_usd"] = str(self.known)
        write_json(directory / "outcome.json", row)
        with self.ledger.open("a") as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        self.rows.append(row)
        self.inflight.discard(number)

    def async_client(self, **client_options):
        client = AsyncOpenAI(**client_options)
        original = client.chat.completions.create

        async def guarded(**kwargs):
            phase = "agent" if "tools" in kwargs else "judge"
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

    def updater(self, messages, settings):
        if not settings["allow_metadata_api"]:
            raise ValueError("Metadata API opt-in missing")
        key, url = runner.credentials(settings)
        kwargs = dict(
            model=MODEL,
            messages=messages,
            temperature=settings["temperature"],
            max_tokens=settings["max_tokens"],
            response_format={"type": "json_object"},
            extra_body=ROUTING,
        )
        number, directory = self.begin("updater", kwargs)
        try:
            with OpenAI(
                api_key=key, base_url=url, timeout=settings["timeout"], max_retries=0
            ) as client:
                response = client.chat.completions.create(**kwargs).model_dump(mode="json")
        except BaseException as exc:
            self.finish(number, directory, "updater", error=exc)
            raise
        self.finish(number, directory, "updater", response=response)
        return response


def freeze(root, out):
    preflight = read_json(out / "preflight.json")
    if preflight["status"] != "passed":
        raise ValueError("MCP/source preflight has not passed")
    for stage, environment in preflight["runtime"].items():
        for task, catalog in environment["catalogs"].items():
            path = out / "metadata" / task / stage / "catalog.json"
            if sha(path) != catalog["catalog_sha256"]:
                raise ValueError("MCP catalog changed after preflight")
    lock, upstream = source(root)
    config = read_json(root / "configs/course-benchmark-v1.3.json")
    for role in ("agent", "judge"):
        config[role]["extra_body"] = ROUTING
    config["request_retry"] = {"max_retries": 0}
    config["comparison_scope"] = "knowledge_update_only_same_actor_no_artifact_repair"
    config["runtime"] = None
    updater = read_json(root / "configs/course-updater.json")
    updater.update(allow_metadata_api=True, request_retry={"max_retries": 0})
    criteria = {
        "430": [
            "Explains declarative programming and contrast with imperative updates accurately.",
            "Includes concrete SwiftUI examples using View/body and data-driven UI state.",
            "Tool observations support retrieved facts; Swift compilation is not tested here.",
        ],
        "133": [
            "Explains expression validation and safe mathematical operation handling in Python.",
            "Gives relevant OWASP-aligned input/resource/security guidance.",
            "Does not claim its generated code is validated merely because remote math/template tools ran.",
            "No fixed Python function, JSON artifact, or code deliverable is added to the original task.",
        ],
        "90": [
            "Provides detailed 青眼白龙 card information supported by actual tool observations.",
            "Supplies a retrievable card image link or image from the actual tools.",
            "Reports the live daily LeetCode challenge with date/identifier from actual tool evidence.",
            "Live network failures and date-dependent content are retained; no offline answer substitution.",
        ],
        "235": [
            "Calls map/area/column chart tools and covers all three requested charts.",
            "Preserves the supplied province/month/category sales values and unit scale.",
            "Distinguishes returned chart specifications/links from actually rendered chart artifacts.",
        ],
    }
    evidence_hashes = {}
    for task in TASKS:
        for stage in STAGES:
            catalog = read_json(out / "metadata" / str(task) / stage / "catalog.json")
            evidence = {
                "version": "capability-evidence-v1",
                "entries": [
                    {
                        "tool_id": t["tool_id"],
                        "tool_fingerprint": fingerprint(t),
                        "kind": "catalog",
                        "quote": t["description"][:4000],
                    }
                    for t in catalog["tools"]
                    if t["description"].strip()
                ],
            }
            path = out / "capability-evidence" / str(task) / (stage + ".json")
            if path.exists() and read_json(path) != evidence:
                raise ValueError("Frozen capability evidence changed")
            if not path.exists():
                write_json(path, evidence)
            evidence_hashes[str(path.relative_to(out))] = sha(path)
    pairs = []
    rng = random.Random(20261103)
    for repeat in range(1, 4):
        cells = [(task, stage) for task in TASKS for stage in STAGES]
        rng.shuffle(cells)
        for index, (task, stage) in enumerate(cells):
            arms = ["no_update", "full_rewrite", "selective_patch"]
            offset = (index + repeat) % 3
            arms = arms[offset:] + arms[:offset]
            for arm in arms:
                pairs.append(
                    {
                        "id": f"{task}-{stage}-{arm}-r{repeat}",
                        "task_id": task,
                        "stage": stage,
                        "strategy": arm,
                        "repeat": repeat,
                        "seed": 100 + repeat,
                        "adaptation": f"adaptations/{task}/{stage}/{arm}/adaptation.json",
                    }
                )
    files = [
        Path(p)
        for p in subprocess.check_output(
            ["git", "ls-files", "src", "integration", "configs"], cwd=root, text=True
        ).splitlines()
    ]
    files += [Path("scripts/eval_v3_formal.py")]
    identities = {str(p): sha(root / p) for p in files if (root / p).is_file()}
    prompt_files = [
        "src/custom/prompt/eval_error_prompt.py",
        "src/custom/analysis/answer/evaluation.py",
        "src/custom/utils/test_utils.py",
    ]
    plan = {
        "schema": "v3-formal-knowledge-only-1",
        "frozen_at": now(),
        "implementation_commit": preflight["implementation_commit"],
        "preflight_sha256": sha(out / "preflight.json"),
        "source_files_sha256": identities,
        "upstream_prompt_files_sha256": {p: sha(upstream / p) for p in prompt_files},
        "model": MODEL,
        "provider_routing": ROUTING,
        "base_url": "https://openrouter.ai/api/v1",
        "actor_and_judge": config,
        "updater": updater,
        "budget_known_usd": 12,
        "concurrency": 4,
        "cell_order": pairs,
        "trajectories_planned": 108,
        "ratings_per_trajectory": 5,
        "tasks": preflight["tasks"],
        "capability_evidence_sha256": evidence_hashes,
        "task_success_criteria": criteria,
        "knowledge": {
            "K0": "live Early tools/list; no custom rules added",
            "V3": "hybrid_v3 / hybrid_v3_program_first_v1 / program_first_light_screen_local_review_v1",
            "independent_evidence_bundle": None,
            "scope": "catalog-only V3 with frozen literal capability quotes; source/probe and Python repair paths are not evaluated",
            "freezing": "one adaptation per task/stage/arm, reused unchanged across 3 actor repeats",
            "non_cumulative": "Middle and Late both adapt directly from Early K0",
        },
        "cost_policy": {
            "deployment": "updater once per task/stage plus actual actor calls; no judge cost",
            "single_task": "one complete update cost + mean actor cost",
            "repeat_cohort": "one complete update cost + sum of 3 actor costs",
            "evaluation": "judge calls separate; failed calls and failed cells retained",
            "cache": "provider caching uncontrolled; report usage and billed USD separately",
            "unknown": "null, never zero; stop new requests; already in-flight requests retained",
        },
        "validity": {
            "actor_repair": "same MCP-feedback recovery allowed in both; no added code testing/repair",
            "seeds": "repeat IDs and judge dimension order only; model seed not sent",
            "judge_recovery": "5 first-valid slots; <=2 attempts each; no SDK/HTTP retries",
            "reruns": "no trajectory reruns or strategy fallback; any missing cell remains missing",
            "delivery": "completed means final-answer termination, not independently proven task success",
            "data_access": "questions only to actors; no benchmark questions/answers/scores into updater",
            "generalization": "4 selected diagnostic tasks, not full 201-task benchmark; descriptive small-sample results",
        },
    }
    target = out / "plan.json"
    if target.exists():
        old = read_json(target)
        if any(old[k] != plan[k] for k in ("source_files_sha256", "preflight_sha256")):
            raise ValueError("Frozen source/input changed; do not reuse this experiment")
        return old
    write_json(target, plan)
    return plan


def adapt_all(root, out, plan, guard):
    for task in TASKS:
        old = out / "metadata" / str(task) / "early/catalog.json"
        for stage in STAGES:
            target = out / "metadata" / str(task) / stage / "catalog.json"
            for arm in ("no_update", "full_rewrite", "selective_patch"):
                directory = out / "adaptations" / str(task) / stage / arm
                if (directory / "adaptation.json").exists():
                    continue
                if guard.stopped:
                    return
                CELL.set(f"update-{task}-{stage}-{arm}")
                context = {"updater": plan["updater"]}
                if arm == "selective_patch":
                    context.update(
                        selective_mode="hybrid_v3",
                        capability_evidence=read_json(
                            out / "capability-evidence" / str(task) / (stage + ".json")
                        ),
                    )

                try:
                    artifact = write_adaptation(old, target, arm, directory, context)
                    if arm == "no_update" and read_json(directory / "knowledge.json") != read_json(
                        old
                    ):
                        raise ValueError("No Update did not retain exact K0")
                    print(
                        json.dumps(
                            {
                                "type": "adaptation",
                                "task": task,
                                "stage": stage,
                                "arm": arm,
                                "status": artifact["status"],
                                "cost": artifact["cost"],
                            }
                        ),
                        flush=True,
                    )
                except Exception as exc:
                    print(
                        json.dumps(
                            {
                                "type": "adaptation",
                                "task": task,
                                "stage": stage,
                                "arm": arm,
                                "status": "failed",
                                "error_type": type(exc).__name__,
                                "detail": str(exc),
                            }
                        ),
                        flush=True,
                    )
    manifest = {}
    for task in TASKS:
        for stage in STAGES:
            for arm in ("no_update", "full_rewrite", "selective_patch"):
                p = out / "adaptations" / str(task) / stage / arm / "adaptation.json"
                if p.exists():
                    artifact = read_json(p)
                    manifest[str(p.relative_to(out))] = {
                        "sha256": sha(p),
                        "status": artifact["status"],
                    }
                    if artifact["status"] == "validated":
                        knowledge = p.parent / "knowledge.json"
                        manifest[str(knowledge.relative_to(out))] = {"sha256": sha(knowledge)}
    write_json(out / "knowledge-freeze.json", {"frozen_at": now(), "files": manifest})


async def actors(root, out, plan, guard):
    semaphore = asyncio.Semaphore(plan["concurrency"])
    knowledge = read_json(out / "knowledge-freeze.json")["files"]

    async def one(cell):
        async with semaphore:
            output = out / "runs" / cell["id"]
            if (output / "result.json").exists():
                return
            if output.exists():
                raise ValueError(f"Interrupted trajectory {cell['id']}; no automatic rerun")
            artifact = out / cell["adaptation"]
            if not artifact.exists() or read_json(artifact)["status"] != "validated":
                write_json(
                    out / "blocked-cells" / f"{cell['id']}.json",
                    {**cell, "status": "adaptation_failed_not_run"},
                )
                return
            if guard.stopped:
                return
            if sha(artifact) != knowledge[cell["adaptation"]]["sha256"]:
                raise ValueError("Adaptation changed after freezing")
            config = {
                **plan["actor_and_judge"],
                "root": str(root),
                "output_dir": str(output),
                "adaptation_path": str(artifact),
                "evaluation_cell": cell["id"],
                "evaluation_plan_sha256": sha(out / "plan.json"),
            }
            CELL.set(cell["id"])
            print(json.dumps({"type": "start", "cell": cell["id"], "at": now()}), flush=True)
            _, result = await runner.run_async(
                cell["task_id"], cell["stage"], cell["strategy"], cell["seed"], config
            )
            print(
                json.dumps(
                    {
                        "type": "finished",
                        "cell": cell["id"],
                        "status": result["status"],
                        "execution": result["execution_status"],
                        "TF": result["TF"],
                        "PE": result["PE"],
                        "agent_usd": result["cost"]["agent"].get("usd"),
                        "known_batch_usd": str(guard.known),
                    }
                ),
                flush=True,
            )

    await asyncio.gather(*(one(cell) for cell in plan["cell_order"]))


def progress(out, plan, guard):
    results = []
    for cell in plan["cell_order"]:
        p = out / "runs" / cell["id"] / "result.json"
        if p.exists():
            results.append({**cell, **read_json(p)})
    summary = {
        "generated_at": now(),
        "planned": 108,
        "saved": len(results),
        "execution_status": dict(Counter(r["execution_status"] for r in results)),
        "judge_status": dict(Counter(r["judge_status"] for r in results)),
        "api_requests": len(guard.rows),
        "known_usd": str(guard.known),
        "unknown_charge_requests": sum(r.get("usd") is None for r in guard.rows),
        "guard_stopped": guard.stopped,
    }
    write_json(out / "progress.json", summary)
    print(json.dumps(summary), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=Path("results/raw/v3-formal-20261103"))
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    out = args.output.resolve()
    plan = freeze(root, out)
    print(
        json.dumps({"type": "frozen", "plan_sha256": sha(out / "plan.json"), "planned": 108}),
        flush=True,
    )
    if not args.execute:
        return
    if (out / "knowledge-freeze.json").exists() or (out / "api").exists():
        raise ValueError("Use a fresh evaluation directory; existing executions are never rerun")
    credential_environment(args.env_file)
    guard = ReceiptGuard(out / "api", plan["budget_known_usd"])
    runner.AsyncOpenAI = guard.async_client
    provider._request_completion = guard.updater
    try:
        adapt_all(root, out, plan, guard)
        if not guard.stopped:
            asyncio.run(actors(root, out, plan, guard))
    finally:
        progress(out, plan, guard)


if __name__ == "__main__":
    main()

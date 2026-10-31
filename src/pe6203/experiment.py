"""Reproducible development matrices and reviewed course benchmark suites."""

import argparse
import asyncio
import csv
import hashlib
import itertools
import json
import os
import random
import sys
import tempfile
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from .baselines import write_adaptation
from .benchmark import load_task, read_json, source, write_json
from .evaluation import judge_scores
from .judge import ecs
from .runner import credentials, resume_judging, run
from .spend_guard import complete_sync
from .spend_guard import stopped as spend_stopped
from .transport import sessions, snapshot

STAGES = ("early", "middle", "late")
STRATEGIES = ("no_update", "full_rewrite", "selective_patch")
MODEL = "deepseek/deepseek-v4.1-flash-1017"


def configure_runtime(root):
    node = Path(root) / ".cache/node-runtime/node_modules/node/bin/node"
    if node.is_file():
        os.environ.setdefault("MCPEVOL_NODE", str(node.resolve()))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def freeze_files(root, paths):
    root = Path(root).resolve()
    return {
        str(
            p.resolve().relative_to(root) if p.resolve().is_relative_to(root) else p.resolve()
        ): sha(p)
        for p in sorted(map(Path, paths))
    }


def verify_files(root, hashes):
    for name, expected in hashes.items():
        p = Path(root) / name
        if not p.is_file() or sha(p) != expected:
            raise ValueError(f"Frozen input changed: {name}; prepare a new experiment")


def make_cells(tasks, stages, strategies, repeats):
    from .patch_variants import VARIANTS

    for values, allowed in [
        (tasks, None),
        (stages, STAGES),
        (strategies, (*STRATEGIES, *VARIANTS)),
    ]:
        if (
            not values
            or len(values) != len(set(values))
            or (allowed and not set(values) <= set(allowed))
        ):
            raise ValueError("Need distinct supported tasks/stages/strategies")
    if type(repeats) is not int or repeats < 1 or any(type(t) is not int for t in tasks):
        raise ValueError("Repeat count must be positive and task IDs must be integers")
    result = [
        {"id": f"task{t}-{v}-{s}-r{r}", "task_id": t, "version": v, "strategy": s, "seed": r}
        for t, v, s, r in itertools.product(tasks, stages, strategies, range(repeats))
    ]
    random.Random(0).shuffle(result)
    return result


def model_config(root, path=None):
    if path:
        config = read_json(Path(root) / path)
    else:
        local = Path(root) / "configs/local.smoke-no-reasoning.json"
        config = read_json(
            local if local.exists() else Path(root) / "configs/full-catalog-smoke.json"
        )
        for role in ("agent", "judge"):
            if config[role]["model"].startswith("REPLACE_"):
                config[role]["model"] = MODEL
        config["judge"].setdefault("extra_body", {"reasoning": {"enabled": False}})
    for field in ("root", "output_dir", "knowledge_path", "adaptation_path", "update_cost"):
        config.pop(field, None)
    if config.get("judge_runs") != 5:
        raise ValueError("Experiment protocol requires exactly five judge attempts")
    for role in ("agent", "judge"):
        if "api_key" in config[role] or "base_url" in config[role]:
            raise ValueError("Use credential environment variable names, never inline secrets")
    config["tool_name_policy"] = "namespaced"
    config.setdefault("request_retry", {"max_retries": 1, "backoff_seconds": 2})
    config["judge"].setdefault("extra_body", {}).setdefault(
        "response_format", {"type": "json_object"}
    )
    return config


async def collect_catalogs(root, tasks, directory):
    lock, upstream = source(root)
    for task_id in tasks:
        task = load_task(upstream, task_id)
        for version in STAGES:
            print(f"读取工具目录 task {task_id} / {version}", flush=True)
            with tempfile.TemporaryDirectory(prefix="pe6203-catalog-") as tmp:
                async with sessions(
                    root, version, task["servers"], Path(tmp), Path(tmp) / "stderr.log"
                ) as clients:
                    catalog = await snapshot(clients, version, lock["commit"])
            write_json(directory / "catalogs" / str(task_id) / f"{version}.json", catalog)


def prepare(
    root,
    output,
    tasks,
    stages=STAGES,
    strategies=STRATEGIES,
    repeats=1,
    config_path=None,
    updater_path=None,
    netlify=False,
    source_url=None,
    suite_path=None,
):
    root, output = Path(root).resolve(), Path(output).resolve()
    suite = read_json(root / suite_path) if suite_path else None
    if suite:
        if set(stages) != set(STAGES) or set(strategies) != set(STRATEGIES):
            raise ValueError("Benchmark requires all three stages and all three strategies")
        suite_tasks = [t["task_id"] for t in suite["tasks"]]
        if tasks is not None and tasks != suite_tasks:
            raise ValueError("Use the fixed suite task set without overrides")
        if config_path or updater_path or netlify or source_url:
            raise ValueError("Use the reviewed suite configuration; changes require a new suite")
        tasks = suite_tasks
        config_path, updater_path = suite["config_path"], suite["updater_config_path"]
    tasks = tasks if tasks is not None else [139]
    configure_runtime(root)
    cells = make_cells(tasks, stages, strategies, repeats)
    config = model_config(root, config_path)
    updater = read_json(root / (updater_path or "configs/full-rewrite-updater.template.json"))
    updater.setdefault("request_retry", config["request_retry"])
    from .baselines import updater_settings

    updater_settings({"updater": updater})
    if 223 in tasks and not netlify:
        raise ValueError("Task 223 requires --netlify for the configured publishing variant")
    if netlify and tasks != [223]:
        raise ValueError("Keep Netlify task 223 separate from the released-server benchmark")
    if source_url and not netlify:
        raise ValueError("A frozen research source is only used by the Netlify variant")
    if netlify:
        from .netlify import site_id

        config["runtime"] = {"publish_backend": "netlify", "site_id": site_id(root)}
        config["tool_timeout_seconds"] = max(config.get("tool_timeout_seconds", 30), 180)
        if not source_url:
            raise ValueError(
                "Provide --source-url: a research listing to freeze for all comparisons"
            )
    output.mkdir(parents=True, exist_ok=False)
    if netlify:
        from .netlify import capture_source

        frozen = capture_source(source_url, output / "source")
        config["runtime"]["source_manifest"] = str(output / "source/manifest.json")
        config["task_context"] = (
            f"Experiment research source: {frozen['url']}. Use this source for the latest papers "
            f"as of {frozen['captured_at']}. The source is frozen for reproducible comparisons. "
            "Publishing uses a Netlify draft URL through the supplied deployment interface."
        )
    asyncio.run(collect_catalogs(root, tasks, output))
    lock, upstream = source(root)
    if suite:
        from .benchmark_suite import validate_suite

        validate_suite(suite, output, lock)
    from .selective import diff_catalogs

    coverage = {}
    for task_id in tasks:
        catalogs = {v: read_json(output / "catalogs" / str(task_id) / f"{v}.json") for v in STAGES}
        coverage[str(task_id)] = {}
        for version in STAGES[1:]:
            diff = diff_catalogs(catalogs["early"], catalogs[version])
            write_json(output / "diffs" / str(task_id) / f"{version}.json", diff)
            fields = {f for row in diff["changed"] for f in row["changed_fields"]}
            coverage[str(task_id)][version] = {
                "catalog_change_types": (["TOOL"] if diff["added"] or diff["removed"] else [])
                + (["PARAM"] if "parameters" in fields else [])
                + (["DESC"] if "description" in fields else []),
                "task_relevance": "unreviewed",
                "unchanged_tools": diff["unchanged_count"],
            }
    paths = list((root / "src/pe6203").rglob("*.py")) + list((root / "integration").rglob("*.py"))
    paths += [
        root / p
        for p in (
            "configs/benchmark.lock.json",
            "configs/server-profiles.json",
            "uv.lock",
            "pyproject.toml",
        )
    ]
    if netlify:
        paths += [root / "tools/netlify/package.json", root / "tools/netlify/package-lock.json"]
    if suite:
        paths += [root / suite_path, root / config_path, root / updater_path]
        paths += [root / p for p in suite.get("evidence_files", [])]
    paths += list(output.rglob("*.json")) + list((output / "source").glob("*.html"))
    node = Path(os.environ.get("MCPEVOL_NODE", ""))
    if node.is_file():
        paths.append(node)
    if config.get("fixture_dir"):
        fixture = root / config["fixture_dir"]
        if not fixture.is_dir() or any(p.is_symlink() for p in fixture.rglob("*")):
            raise ValueError("Fixture must exist and contain no symlinks")
        paths += [p for p in fixture.rglob("*") if p.is_file()]
    roles = {"agent": config["agent"], "judge": config["judge"], "updater": updater}
    endpoints = {role: os.environ.get(value["base_url_env"]) for role, value in roles.items()}
    plan = {
        "schema_version": "experiment-1",
        "kind": "benchmark" if suite else "development",
        "variant": "netlify_frozen_source" if netlify else "released_servers",
        "created_at": datetime.now(UTC).isoformat(),
        "benchmark_commit": lock["commit"],
        "dataset_revision": lock["dataset_revision"],
        "cells": cells,
        "tasks": [load_task(upstream, t) for t in tasks],
        "config": config,
        "updater": updater,
        "judge_runs": 5,
        "files": freeze_files(root, paths),
        "endpoints": endpoints,
        "coverage": coverage,
        "formal_evaluation": bool(suite),
        "limitations": (
            suite["limitations"]
            if suite
            else [
                "Development subset; task-level change/retention labels need review",
                "Under/over-update causal examples and independent holdout remain required",
                "Selective Patch is deterministic; Full Rewrite is an LLM description rewrite",
            ]
        )
        + [f"{repeats} trajectory repeat(s); five judge ratings are not independent task repeats"],
        "retry_policy": (
            "Identical model request: one retry on connection/429/5xx, respecting Retry-After up to 60s. "
            "Judge: five slots, at most two logical attempts per slot, first valid rating only; "
            "durable request/response/outcome records and judge-only resume; all failed costs retained. "
            "No agent-trajectory, tool-call or low-score retries."
            if config.get("judge_recovery")
            else "Retry identical model requests once on connection errors, 429 or 5xx; respect Retry-After up to 60s. Log failed requests with unknown usage. No tool-call, trajectory, invalid-output or low-score retries."
        ),
        "availability_preflight": True,
        "stop_after_infrastructure_failures": 2,
    }
    if suite:
        plan["suite"] = suite
    write_json(output / "plan.json", plan)
    (output / "plan.sha256").write_text(sha(output / "plan.json") + "\n")
    write_json(root / "configs/local.experiment.json", {"output": str(output)})
    print(f"已准备 {len(cells)} 条轨迹 / {5 * len(cells)} 次 judge；尚未调用模型。\n{output}")
    return plan


def check_plan(root, output, plan):
    if sha(output / "plan.json") != (output / "plan.sha256").read_text().strip():
        raise ValueError("Frozen plan changed; prepare a new experiment")
    verify_files(root, plan["files"])
    if plan.get("shared_adaptations") and (output / "experiment.json").exists():
        from .strategy_search import check_knowledge

        check_knowledge(output)
    source(root)
    roles = {
        "agent": plan["config"]["agent"],
        "judge": plan["config"]["judge"],
        "updater": plan["updater"],
    }
    for role, settings in roles.items():
        if role == "updater" and not any(
            c["strategy"] in ("full_rewrite", "linked_notes", "feedback_notes", "workflow_notes")
            and c["version"] != "early"
            for c in plan["cells"]
        ):
            continue
        _, endpoint = credentials(settings)
        if endpoint != plan["endpoints"][role]:
            raise ValueError(
                f"{role} endpoint changed; prepare a new experiment after configuring .env"
            )
    if plan["config"].get("runtime", {}).get("publish_backend") == "netlify":
        from .netlify import check_setup

        check_setup(root, plan["config"]["runtime"]["site_id"])


@contextmanager
def writer_lock(output):
    with (Path(output) / ".writer.lock").open("a+b") as stream:
        try:
            if os.name == "nt":
                import msvcrt

                stream.seek(0)
                stream.write(b"0")
                stream.flush()
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise ValueError("This experiment is already running in another process") from exc
        try:
            yield
        finally:
            if os.name == "nt":
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


def run_experiment(root, output, resume=False, limit=None):
    with writer_lock(output):
        return _run_experiment(root, output, resume, limit)


def pending_judging(directory, config):
    if "judge_recovery" not in config or not (directory / "execution-checkpoint.json").exists():
        return False
    result = read_json(directory / "result.json") if (directory / "result.json").exists() else {}
    return result.get("status") != "evaluated" and result.get("judge_recovery", {}).get(
        "resumable", True
    )


def _run_experiment(root, output, resume=False, limit=None):
    root, output = Path(root).resolve(), Path(output).resolve()
    configure_runtime(root)
    plan = read_json(output / "plan.json")
    check_plan(root, output, plan)
    if plan.get("shared_adaptations"):
        from .strategy_search import check_knowledge

        check_knowledge(output)
    ledger_path = output / "experiment.json"
    if ledger_path.exists() and not resume:
        raise ValueError("Experiment already started; use run --resume")
    ledger = read_json(ledger_path) if ledger_path.exists() else {"cells": {}}
    if spend_stopped(plan["config"].get("spend_guard")):
        raise ValueError("Spend ledger stopped; no preflight or new cell is permitted")
    if plan.get("availability_preflight") and any(
        ledger["cells"].get(c["id"], {}).get("status") in (None, "running")
        or pending_judging(output / "cells" / c["id"] / "run", plan["config"])
        for c in plan["cells"]
    ):
        availability_preflight(plan, output)
    executed = 0
    consecutive_transport_failures = 0
    ledger.pop("stop_reason", None)
    for cell in plan["cells"]:
        directory = output / "cells" / cell["id"]
        item = ledger["cells"].get(cell["id"], {})
        recovering = resume and pending_judging(directory / "run", plan["config"])
        if item.get("status") not in (None, "running") or recovering:
            verify_files(output, item.get("files", {}))
        if item.get("status") not in (None, "running") and not recovering:
            continue
        if limit is not None and executed >= limit:
            break
        adaptation = adaptation_path(output, plan, cell)
        result_path = directory / "run/result.json"
        if recovering:
            print(f"[{executed + 1}] {cell['id']}：仅恢复缺失评分，保留原执行", flush=True)
            _, result = resume_judging(directory / "run")
            item["status"] = result["status"]
            executed += 1
        elif result_path.exists():
            result = read_json(result_path)
            item["status"] = result["status"]
        elif (directory / "run").exists():
            item["status"] = "interrupted"
        else:
            ledger["cells"][cell["id"]] = item = {"status": "running"}
            write_json(ledger_path, ledger)
            print(f"[{executed + 1}] {cell['id']}：更新知识 → 执行 → 5 次评分", flush=True)
            if not adaptation.exists() and not adaptation.parent.exists():
                if plan.get("shared_adaptations"):
                    raise ValueError("Frozen shared adaptation missing")
                try:
                    write_adaptation(
                        output / "catalogs" / str(cell["task_id"]) / "early.json",
                        output / "catalogs" / str(cell["task_id"]) / f"{cell['version']}.json",
                        cell["strategy"],
                        adaptation.parent,
                        {"updater": {**plan["updater"], "allow_metadata_api": True}},
                    )
                except (ValueError, KeyError, OSError, TypeError):
                    # The updater saves errors, response and incurred cost; never retry it silently.
                    if not adaptation.exists():
                        raise
            if not adaptation.exists():
                item["status"] = "interrupted"
            elif read_json(adaptation)["status"] != "validated":
                item["status"] = "adaptation_failed"
            else:
                _, result = run(
                    cell["task_id"],
                    cell["version"],
                    cell["strategy"],
                    cell["seed"],
                    {
                        **plan["config"],
                        "root": str(root),
                        "output_dir": str(directory / "run"),
                        "adaptation_path": str(adaptation),
                    },
                )
                item["status"] = result["status"]
            executed += 1
        # Preserve byte identities for all scoring, execution, and update evidence.
        item["files"] = freeze_files(
            output,
            [
                p
                for p in directory.rglob("*")
                if p.is_file() and "workspace" not in p.relative_to(directory).parts
            ],
        )
        ledger["cells"][cell["id"]] = item
        temporary = ledger_path.with_suffix(".tmp")
        write_json(temporary, ledger)
        temporary.replace(ledger_path)
        summarize(output)
        print(f"  {item['status']}", flush=True)
        if spend_stopped(plan["config"].get("spend_guard")):
            ledger["stop_reason"] = "spend_guard"
            write_json(ledger_path, ledger)
            print("费用保护已停止后续单元；保留请求、未知费用与现有结果。", flush=True)
            break
        if result_path.exists() and read_json(result_path).get("judge_recovery", {}).get("paused"):
            ledger["stop_reason"] = "judge_transport_outage"
            write_json(ledger_path, ledger)
            print("评分阶段连续连接故障，已保存评分槽；网络恢复后 --resume。", flush=True)
            break
        transport_failure = (
            result_path.exists()
            and read_json(result_path).get("failure_category") == "model_transport"
        )
        audit_path = adaptation.parent / "updater-audit.json"
        if not result_path.exists() and audit_path.exists():
            audit = read_json(audit_path)
            transport_failure = audit.get("error_type") in (
                "APIConnectionError",
                "APITimeoutError",
                "RateLimitError",
                "InternalServerError",
            )
        consecutive_transport_failures = (
            consecutive_transport_failures + 1 if transport_failure else 0
        )
        if consecutive_transport_failures >= plan.get("stop_after_infrastructure_failures", 2):
            ledger["stop_reason"] = "consecutive_model_transport_failures"
            write_json(ledger_path, ledger)
            print(
                "连续模型连接故障，已停止；其余单元保持未运行。检查网络后可 --resume；失败轨迹保留。",
                flush=True,
            )
            break
    return ledger


def availability_preflight(plan, output):
    """Check real credentials/model endpoints before allocating any benchmark cells."""
    import time

    from openai import OpenAI

    from integration.model_api import model_id

    from .request_retry import request_sync

    path = Path(output) / "preflight" / f"{datetime.now(UTC):%Y%m%dT%H%M%S%f}.json"
    records = []
    prior_calls = sum(len(read_json(p)) for p in (Path(output) / "preflight").glob("*.json"))
    maximum_calls = plan.get("max_preflight_calls")
    if maximum_calls is not None and prior_calls >= maximum_calls:
        raise ValueError("Approved preflight call limit reached")
    for role in ("agent", "judge", "updater"):
        settings = plan[role] if role == "updater" else plan["config"][role]
        key, url = credentials(settings)
        resolved = model_id(settings["model"], url)
        # A common updater endpoint/key/model was already checked as the agent.
        if (
            role == "updater"
            and settings["api_key_env"] == plan["config"]["agent"]["api_key_env"]
            and url == plan["endpoints"]["agent"]
            and resolved == plan["config"]["agent"]["model"]
        ):
            continue
        if maximum_calls is not None and prior_calls + len(records) >= maximum_calls:
            raise ValueError("Approved preflight call limit reached")
        item = {"role": role, "model": resolved, "retries": []}
        records.append(item)
        started = time.monotonic()
        try:
            with OpenAI(api_key=key, base_url=url, timeout=30, max_retries=0) as client:
                response = request_sync(
                    lambda: complete_sync(
                        client,
                        plan["config"].get("spend_guard"),
                        model=resolved,
                        messages=[{"role": "user", "content": 'Return JSON: {"ok":true}'}],
                        temperature=0,
                        max_completion_tokens=32,
                        extra_body={
                            "reasoning": {"enabled": False},
                            "response_format": {"type": "json_object"},
                        },
                    ),
                    plan["config"].get("request_retry"),
                    item["retries"].append,
                )
            item["usage"] = response.usage.model_dump() if response.usage else None
            item["actual_provider"] = getattr(response, "provider", None)
            item["actual_model"] = response.model
            item["response_id"] = response.id
            if spend_stopped(plan["config"].get("spend_guard")):
                raise ValueError("Preflight response stopped the spend/provider guard")
            item["status"] = "reachable"
        except Exception as exc:
            item.update(status="failed", error_type=type(exc).__name__)
            raise ValueError(
                f"{role} API 预检失败，未启动新单元；修复连接/凭据后重新 run。见 {path}"
            ) from None
        finally:
            item["seconds"] = time.monotonic() - started
            write_json(path, records)


def summarize(output):
    output = Path(output)
    if (output / "experiment.json").exists():
        for item in read_json(output / "experiment.json")["cells"].values():
            verify_files(output, item.get("files", {}))
    plan = read_json(output / "plan.json")
    if (output / "plan.sha256").exists() and sha(output / "plan.json") != (
        output / "plan.sha256"
    ).read_text().strip():
        raise ValueError("Frozen plan changed")
    rows, costs = [], {role: [] for role in ("update", "agent", "judge")}
    seen_updates = set()
    for cell in plan["cells"]:
        directory = output / "cells" / cell["id"]
        result = (
            read_json(directory / "run/result.json")
            if (directory / "run/result.json").exists()
            else {}
        )
        artifact_path = adaptation_path(output, plan, cell)
        adaptation = read_json(artifact_path) if artifact_path.exists() else {}
        eval_path = directory / "run/EVAL" / f"{cell['task_id']}.json"
        values, issue = (
            judge_scores(read_json(eval_path))
            if eval_path.exists()
            else (None, "missing_five_judge_records")
        )
        if result.get("judge_status") != "complete":
            values = None
        row = {
            **cell,
            "status": result.get(
                "status", "adaptation_failed" if adaptation.get("status") == "failed" else "pending"
            ),
            "execution_status": result.get("execution_status", "not_started"),
            "TF": values["TF"] if values else None,
            "PE": values["PE"] if values else None,
            "score_issue": issue,
            "tool_errors": 0,
            "update_tokens": adaptation.get("cost", {}).get("total_tokens"),
        }
        events = directory / "run/events.jsonl"
        if events.exists():
            row["tool_errors"] = sum(
                bool(e.get("result", {}).get("isError"))
                for e in (json.loads(line) for line in events.read_text().splitlines())
                if e.get("type") == "tool_result"
            )
        rows.append(row)
        for role in costs:
            if role == "update":
                if artifact_path in seen_updates:
                    continue
                seen_updates.add(artifact_path)
            cost = adaptation.get("cost") if role == "update" else result.get("cost", {}).get(role)
            if cost is not None:
                costs[role].append(cost)
    aggregate_cost = {
        role: {
            key: (
                sum(c[key] for c in items) if all(c.get(key) is not None for c in items) else None
            )
            for key in ("total_tokens", "usd", "seconds")
        }
        for role, items in costs.items()
    }
    ecs_rows = []
    for t, s, r in sorted({(c["task_id"], c["strategy"], c["seed"]) for c in plan["cells"]}):
        scores = {
            row["version"]: row["TF"]
            for row in rows
            if (row["task_id"], row["strategy"], row["seed"]) == (t, s, r)
        }
        ecs_rows.append({"task_id": t, "strategy": s, "repeat": r, **ecs(scores)})
    matched = 0
    for task, stage, repeat in {(r["task_id"], r["version"], r["seed"]) for r in rows}:
        group = [
            r for r in rows if (r["task_id"], r["version"], r["seed"]) == (task, stage, repeat)
        ]
        if {r["strategy"] for r in group if r["TF"] is not None} == {
            c["strategy"] for c in plan["cells"]
        }:
            matched += 1
    summary = {
        "kind": plan.get("kind", "development"),
        "variant": plan.get("variant"),
        "formal_evaluation": plan.get("formal_evaluation", False),
        "planned": len(rows),
        "scored": sum(r["TF"] is not None for r in rows),
        "completed_execution": sum(r["execution_status"] == "completed" for r in rows),
        "matched_three_strategy_groups": matched,
        "matched_all_strategy_groups": matched,
        "rows": rows,
        "ecs": ecs_rows,
        "cost": aggregate_cost,
        "recovery_retention": None,
        "limitations": plan.get("limitations", []),
    }
    if plan.get("suite"):
        from .benchmark_suite import analyze

        analysis = analyze(output, plan)
        summary["recovery_retention"] = analysis["recovery_retention"]
        summary["main_results"] = analysis["main_results"]
        summary["matched_ecs"] = analysis["ecs"]
        summary["update_cost_by_strategy"] = analysis["update_cost"]
        summary["analysis_path"] = "analysis/summary.json"
    write_json(output / "summary.json", summary)
    with (output / "runs.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else ["id"])
        writer.writeheader()
        writer.writerows(rows)
    return summary


def adaptation_path(output, plan, cell):
    key = f"{cell['task_id']}-{cell['version']}-{cell['strategy']}"
    if plan.get("shared_adaptations"):
        return Path(output) / plan["shared_adaptations"][key]
    return Path(output) / "cells" / cell["id"] / "adaptation/adaptation.json"


def report(output):
    summary = summarize(output)
    print(
        f"{summary['kind']} | 已评分 {summary['scored']}/{summary['planned']} | 执行完成 {summary['completed_execution']} | 三策略匹配组 {summary['matched_three_strategy_groups']}"
    )
    print(f"{'任务/阶段/策略':60} {'TF':>6} {'PE':>6}  执行状态")
    for row in summary["rows"]:
        print(f"{row['id']:60} {str(row['TF']):>6} {str(row['PE']):>6}  {row['execution_status']}")
    for row in summary["ecs"]:
        print(
            f"ECS task{row['task_id']} {row['strategy']} r{row['repeat']}: {row['upstream_population']}"
        )
    if summary.get("recovery_retention"):
        for row in summary["recovery_retention"]:
            if row["strategy"] == "no_update":
                continue
            print(
                f"{row['stage']} {row['strategy']} {row['subgroup']}: ΔTF={row['delta_vs_no_update_same_stage']} (matched tasks={row['matched_tasks']})"
            )
        print("公平匹配统计、缺失记录与分策略费用：analysis/；单条 ECS 仅为诊断值。")
    print(f"结果：{Path(output).resolve() / 'summary.json'}；逐条轨迹：runs.csv / cells/")
    return summary


def latest(root):
    p = Path(root) / "configs/local.experiment.json"
    if not p.exists():
        raise ValueError("No prepared experiment; run ./experiment prepare first")
    return Path(read_json(p)["output"])


def check(root, api=False):
    from .cli import doctor

    configure_runtime(root)
    status = doctor(root)
    print(json.dumps({k: status[k] for k in ("node", "credentials", "stages_installed")}, indent=2))
    if api:
        from openai import OpenAI

        config = model_config(root)
        evidence = []
        evidence_path = (
            Path(root) / "results/raw" / f"api-check-{datetime.now(UTC):%Y%m%dT%H%M%S%f}.json"
        )
        for role in ("agent", "judge"):
            settings = config[role]
            key, url = credentials(settings)
            with OpenAI(api_key=key, base_url=url, timeout=30, max_retries=0) as client:
                response = client.chat.completions.create(
                    model=settings["model"],
                    messages=[{"role": "user", "content": "Reply OK."}],
                    temperature=settings["temperature"],
                    max_completion_tokens=32,
                    **({"extra_body": settings["extra_body"]} if "extra_body" in settings else {}),
                )
            evidence.append(
                {
                    "role": role,
                    "model": settings["model"],
                    "usage": response.usage.model_dump() if response.usage else None,
                }
            )
            write_json(evidence_path, evidence)
            print(f"{role}: API request succeeded")
    return status


def papers_workflow(root, source_url=None, repeats=1, prepare_only=False):
    from .netlify import setup_wizard

    setup_wizard(root)
    config = model_config(root)
    for role in ("agent", "judge"):
        credentials(config[role])
    print("Agent 自动选择抓取/发布工具与参数；三策略共用同一个来源快照。")
    if not source_url:
        source_url = (
            input("论文列表 HTTPS URL [https://huggingface.co/papers?q=Embodied+AI]: ").strip()
            or "https://huggingface.co/papers?q=Embodied+AI"
        )
    output = Path(root) / "results/raw" / f"papers-{datetime.now(UTC):%Y%m%dT%H%M%S%f}"
    prepare(
        root,
        output,
        [223],
        repeats=repeats,
        netlify=True,
        source_url=source_url,
        config_path="configs/course-benchmark-v1.3.json",
        updater_path="configs/course-updater.json",
    )
    if not prepare_only:
        print("开始调用模型；将创建 Netlify draft 网页并保存全部轨迹。", flush=True)
        run_experiment(root, output)
        report(output)
    return output


def menu(root):
    while True:
        print(
            "\nPE6203 实验台\n1 环境检查  2 准备 task139 开发实验  3 准备论文网页实验\n4 运行/继续最近实验（调用 API）  5 查看结果  6 Netlify 设置\n7 准备固定课程 benchmark（133/235/283）  0 退出"
        )
        choice = input("选择 [0]: ").strip() or "0"
        if choice == "0":
            return 0
        try:
            if choice == "1":
                check(root)
            elif choice == "3":
                repeats = int(input("每组重复次数 [1]: ").strip() or "1")
                papers_workflow(root, repeats=repeats)
            elif choice == "2":
                repeats = int(input("每组重复次数 [1，正式建议 3]: ").strip() or "1")
                paper = choice == "3"
                url = input("要冻结的研究论文列表 URL: ").strip() if paper else None
                output = (
                    Path(root) / "results/raw" / f"experiment-{datetime.now(UTC):%Y%m%dT%H%M%S%f}"
                )
                prepare(
                    root,
                    output,
                    [223 if paper else 139],
                    repeats=repeats,
                    netlify=paper,
                    source_url=url,
                )
            elif choice == "4":
                output = latest(root)
                plan = read_json(output / "plan.json")
                print(f"计划 {len(plan['cells'])} 条轨迹，每条 5 次 judge；失败和低分不自动重跑。")
                run_experiment(root, output, resume=True)
                report(output)
            elif choice == "5":
                report(latest(root))
            elif choice == "6":
                from .netlify import setup

                action = input("install / login / link / status [status]: ").strip() or "status"
                setup(root, action)
            elif choice == "7":
                repeats = int(input("每组重复次数 [3；预算有限可填 1]: ").strip() or "3")
                output = (
                    Path(root) / "results/raw" / f"benchmark-{datetime.now(UTC):%Y%m%dT%H%M%S%f}"
                )
                prepare(
                    root,
                    output,
                    None,
                    repeats=repeats,
                    suite_path="experiments/benchmark-v1.3.json",
                )
        except (ValueError, OSError, KeyError) as exc:
            print(f"未完成：{exc}")


def main(root, arguments):
    if arguments and arguments[0] == "search":
        from .strategy_search import main as search_main

        return search_main(root, arguments[1:])
    parser = argparse.ArgumentParser(
        prog="pe6203 experiment",
        description="三策略开发实验；prepare 不调用模型，run 会调用模型并保留全部结果",
    )
    sub = parser.add_subparsers(dest="action")
    sub.add_parser("search", help="文献补丁研究：prepare → build → review → run → report")
    p = sub.add_parser("check", help="检查依赖；--api 额外调用真实模型")
    p.add_argument("--api", action="store_true")
    p = sub.add_parser("prepare", help="固定任务、配置、工具目录与源码 hashes")
    p.add_argument("--tasks", type=int, nargs="+")
    p.add_argument(
        "--suite", type=Path, help="Reviewed benchmark suite, e.g. experiments/benchmark-v1.json"
    )
    p.add_argument("--stages", choices=STAGES, nargs="+", default=list(STAGES))
    p.add_argument("--strategies", choices=STRATEGIES, nargs="+", default=list(STRATEGIES))
    p.add_argument("--repeats", type=int, help="Default: 3 for a suite, 1 for development")
    p.add_argument("--config", type=Path)
    p.add_argument("--updater-config", type=Path)
    p.add_argument("--output", type=Path)
    p.add_argument("--netlify", action="store_true")
    p.add_argument("--source-url", help="task223: freeze this public research listing HTML")
    p = sub.add_parser("run", help="执行已准备矩阵；会调用 API")
    p.add_argument("--output", type=Path)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--limit", type=int, help="本次最多执行多少个尚未运行的单元")
    p = sub.add_parser("report", help="重新核对五次评分并生成 CSV/JSON")
    p.add_argument("--output", type=Path)
    p = sub.add_parser("netlify", help="用户自行登录并选择专用实验站点")
    p.add_argument("operation", choices=["install", "login", "link", "switch", "status", "verify"])
    p.add_argument("--workspace", type=Path, help="verify：只核验此运行 workspace 下已有部署")
    p = sub.add_parser("papers", help="网页实验向导：依赖→用户登录→站点→来源→运行")
    p.add_argument("--source-url")
    p.add_argument("--repeats", type=int, default=1)
    p.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args(arguments)
    root = Path(root).resolve()
    configure_runtime(root)
    try:
        if args.action is None:
            return menu(root)
        if args.action == "check":
            check(root, args.api)
        elif args.action == "prepare":
            output = (
                args.output
                or root / "results/raw" / f"experiment-{datetime.now(UTC):%Y%m%dT%H%M%S%f}"
            )
            prepare(
                root,
                output,
                args.tasks,
                args.stages,
                args.strategies,
                args.repeats if args.repeats is not None else (3 if args.suite else 1),
                args.config,
                args.updater_config,
                args.netlify,
                args.source_url,
                args.suite,
            )
        elif args.action == "run":
            if args.limit is not None and args.limit < 1:
                raise ValueError("--limit must be positive")
            output = args.output or latest(root)
            ledger = run_experiment(root, output, args.resume, args.limit)
            report(output)
            return 2 if any(c["status"] != "evaluated" for c in ledger["cells"].values()) else 0
        elif args.action == "report":
            report(args.output or latest(root))
        elif args.action == "papers":
            if args.repeats < 1:
                raise ValueError("--repeats must be positive")
            papers_workflow(root, args.source_url, args.repeats, args.prepare_only)
        else:
            from .netlify import setup, verify_deployment

            if args.operation == "verify":
                if not args.workspace:
                    raise ValueError("netlify verify requires --workspace <run/workspace>")
                audits = sorted((args.workspace / "deployments").glob("*/deployment.json"))
                if not audits:
                    raise ValueError("No recorded deployments in this workspace")
                for audit in audits:
                    print(verify_deployment(audit))
                return 0
            return setup(root, args.operation)
        return 0
    except KeyboardInterrupt:
        print("已停止；保留现有轨迹。使用 run --resume 查看并继续未运行单元。", file=sys.stderr)
        return 130
    except Exception as exc:
        # Do not print provider exception bodies, which can echo credentials.
        print(
            str(exc)
            if isinstance(exc, (ValueError, FileNotFoundError, FileExistsError))
            else f"{type(exc).__name__}: see saved artifacts; check credentials/network",
            file=sys.stderr,
        )
        return 2

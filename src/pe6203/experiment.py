"""Small, reproducible development matrices over the shared benchmark runner."""

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
from .runner import credentials, run
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
    for values, allowed in [(tasks, None), (stages, STAGES), (strategies, STRATEGIES)]:
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
):
    root, output = Path(root).resolve(), Path(output).resolve()
    configure_runtime(root)
    cells = make_cells(tasks, stages, strategies, repeats)
    config = model_config(root, config_path)
    updater = read_json(root / (updater_path or "configs/full-rewrite-updater.template.json"))
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
        "kind": "development",
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
        "formal_evaluation": False,
        "limitations": [
            "Development subset; task-level change/retention labels need review",
            "Under/over-update causal examples and independent holdout remain required",
            "One run per cell by default; use --repeats 3 for repeated trajectories",
            "Selective Patch is deterministic; Full Rewrite is an LLM description rewrite",
        ],
        "retry_policy": "No automatic retry of failed, interrupted, or low-score attempts",
    }
    write_json(output / "plan.json", plan)
    (output / "plan.sha256").write_text(sha(output / "plan.json") + "\n")
    write_json(root / "configs/local.experiment.json", {"output": str(output)})
    print(f"已准备 {len(cells)} 条轨迹 / {5 * len(cells)} 次 judge；尚未调用模型。\n{output}")
    return plan


def check_plan(root, output, plan):
    if sha(output / "plan.json") != (output / "plan.sha256").read_text().strip():
        raise ValueError("Frozen plan changed; prepare a new experiment")
    verify_files(root, plan["files"])
    source(root)
    roles = {
        "agent": plan["config"]["agent"],
        "judge": plan["config"]["judge"],
        "updater": plan["updater"],
    }
    for role, settings in roles.items():
        if role == "updater" and not any(
            c["strategy"] == "full_rewrite" and c["version"] != "early" for c in plan["cells"]
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


def _run_experiment(root, output, resume=False, limit=None):
    root, output = Path(root).resolve(), Path(output).resolve()
    configure_runtime(root)
    plan = read_json(output / "plan.json")
    check_plan(root, output, plan)
    ledger_path = output / "experiment.json"
    if ledger_path.exists() and not resume:
        raise ValueError("Experiment already started; use run --resume")
    ledger = read_json(ledger_path) if ledger_path.exists() else {"cells": {}}
    executed = 0
    for cell in plan["cells"]:
        directory = output / "cells" / cell["id"]
        item = ledger["cells"].get(cell["id"], {})
        if item.get("status") not in (None, "running"):
            verify_files(output, item.get("files", {}))
            continue
        if limit is not None and executed >= limit:
            break
        adaptation, result_path = (
            directory / "adaptation/adaptation.json",
            directory / "run/result.json",
        )
        if result_path.exists():
            result = read_json(result_path)
            item["status"] = result["status"]
        elif (directory / "run").exists():
            item["status"] = "interrupted"
        else:
            ledger["cells"][cell["id"]] = item = {"status": "running"}
            write_json(ledger_path, ledger)
            print(f"[{executed + 1}] {cell['id']}：更新知识 → 执行 → 5 次评分", flush=True)
            if not adaptation.exists() and not adaptation.parent.exists():
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
    return ledger


def summarize(output):
    output = Path(output)
    if (output / "experiment.json").exists():
        for item in read_json(output / "experiment.json")["cells"].values():
            verify_files(output, item.get("files", {}))
    plan = read_json(output / "plan.json")
    rows, costs = [], {role: [] for role in ("update", "agent", "judge")}
    for cell in plan["cells"]:
        directory = output / "cells" / cell["id"]
        result = (
            read_json(directory / "run/result.json")
            if (directory / "run/result.json").exists()
            else {}
        )
        adaptation = (
            read_json(directory / "adaptation/adaptation.json")
            if (directory / "adaptation/adaptation.json").exists()
            else {}
        )
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
        if {r["strategy"] for r in group if r["TF"] is not None} == set(STRATEGIES):
            matched += 1
    summary = {
        "kind": "development",
        "variant": plan.get("variant"),
        "formal_evaluation": False,
        "planned": len(rows),
        "scored": sum(r["TF"] is not None for r in rows),
        "completed_execution": sum(r["execution_status"] == "completed" for r in rows),
        "matched_three_strategy_groups": matched,
        "rows": rows,
        "ecs": ecs_rows,
        "cost": aggregate_cost,
        "recovery_retention": None,
        "limitations": plan.get("limitations", []),
    }
    write_json(output / "summary.json", summary)
    with (output / "runs.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else ["id"])
        writer.writeheader()
        writer.writerows(rows)
    return summary


def report(output):
    summary = summarize(output)
    print(
        f"开发实验 | 已评分 {summary['scored']}/{summary['planned']} | 执行完成 {summary['completed_execution']} | 三策略匹配组 {summary['matched_three_strategy_groups']}"
    )
    print(f"{'任务/阶段/策略':60} {'TF':>6} {'PE':>6}  执行状态")
    for row in summary["rows"]:
        print(f"{row['id']:60} {str(row['TF']):>6} {str(row['PE']):>6}  {row['execution_status']}")
    for row in summary["ecs"]:
        print(
            f"ECS task{row['task_id']} {row['strategy']} r{row['repeat']}: {row['upstream_population']}"
        )
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


def menu(root):
    while True:
        print(
            "\nPE6203 实验台\n1 环境检查  2 准备 task139 三策略实验  3 准备论文网页实验\n4 运行/继续最近实验（调用 API）  5 查看结果  6 Netlify 设置  0 退出"
        )
        choice = input("选择 [0]: ").strip() or "0"
        if choice == "0":
            return 0
        try:
            if choice == "1":
                check(root)
            elif choice in ("2", "3"):
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
        except (ValueError, OSError, KeyError) as exc:
            print(f"未完成：{exc}")


def main(root, arguments):
    parser = argparse.ArgumentParser(
        prog="pe6203 experiment",
        description="三策略开发实验；prepare 不调用模型，run 会调用模型并保留全部结果",
    )
    sub = parser.add_subparsers(dest="action")
    p = sub.add_parser("check", help="检查依赖；--api 额外调用真实模型")
    p.add_argument("--api", action="store_true")
    p = sub.add_parser("prepare", help="固定任务、配置、工具目录与源码 hashes")
    p.add_argument("--tasks", type=int, nargs="+", default=[139])
    p.add_argument("--stages", choices=STAGES, nargs="+", default=list(STAGES))
    p.add_argument("--strategies", choices=STRATEGIES, nargs="+", default=list(STRATEGIES))
    p.add_argument("--repeats", type=int, default=1)
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
    p.add_argument("operation", choices=["install", "login", "link", "status"])
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
                args.repeats,
                args.config,
                args.updater_config,
                args.netlify,
                args.source_url,
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
        else:
            from .netlify import setup

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

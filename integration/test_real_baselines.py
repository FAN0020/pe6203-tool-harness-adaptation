"""Task 139 baseline pilot reusing the pinned upstream ChatModel execution loop.

Usage: uv run python -m integration.test_real_baselines --version middle --dry-run
Remove --dry-run for paid agent and judge requests. No credentials are stored.
"""

import argparse
import ast
import asyncio
import copy
import hashlib
import json
import logging
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

from openai import AsyncOpenAI

from integration.baselines import AdaptationError
from integration.export_baseline_knowledge import adapt_for_runner
from integration.model_api import model_id, nonthinking_options
from integration.project_paths import pilot_config_path, task139_metadata_path
from pe6203 import runner
from pe6203.benchmark import load_task, read_json, source, write_json
from pe6203.report import render_saved_report
from pe6203.transport import check_arguments


class DeepSeekClient(AsyncOpenAI):
    """Translate the existing runner's token limit and fix non-thinking mode."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        original = self.chat.completions.create

        async def create(**payload):
            if "max_completion_tokens" in payload:
                payload["max_tokens"] = payload.pop("max_completion_tokens")
            payload["model"] = model_id(payload["model"], self.base_url)
            payload["extra_body"] = nonthinking_options(self.base_url)
            return await original(**payload)

        self.chat.completions.create = create


def load_upstream_class(path):
    """Load the original class unchanged, excluding unused heavyweight imports.

    __init__ and retry methods are bypassed below; run_with_server is executed
    from the actual pinned source. No upstream file is edited.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    selected = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ChatModel"]
    if len(selected) != 1:
        raise ValueError("Expected one upstream ChatModel class")
    namespace = {
        "asyncio": asyncio,
        "json": json,
        "uuid": uuid,
        "logger": logging.getLogger("upstream.ChatModel"),
    }
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), "exec"), namespace)
    return namespace["ChatModel"], namespace


async def upstream_agent_loop(
    client, clients, tools, routes, question, workspace, config, seed, emit
):
    """Bridge the upstream synchronous loop to existing async stdio sessions."""
    _, upstream = source(config["root"])
    path = upstream / "src/custom/agents/SimpleOpenAIAgent.py"
    agent_class, namespace = load_upstream_class(path)
    records = read_json(config["knowledge_path"])["tools"]
    by_name = {record["name"]: record for record in records}
    for tool in tools:
        record = by_name[tool["function"]["name"]]
        extra = {"usage_rules": record["usage_rules"], "output_schema": record.get("output_schema")}
        tool["function"]["description"] += "\nTool metadata: " + json.dumps(
            extra, ensure_ascii=False
        )
    main_loop = asyncio.get_running_loop()
    usages, failures = [], []
    round_count = 0
    timeout = config["request_timeout_seconds"]
    # Build this table exclusively from supplied frozen knowledge, never live discovery.
    wire_routes = {f"{r['server_id']}_1mcp_{name}": r for name, r in routes.items()}

    async def call_tool(name, arguments, url):
        route = wire_routes[name]
        check_arguments(arguments, workspace)
        try:
            result = await asyncio.wait_for(
                clients[route["server_id"]].call_tool(route["tool_name"], arguments),
                config.get("tool_timeout_seconds", 30),
            )
        except Exception as exc:
            emit(
                {
                    "type": "tool_error",
                    "name": name,
                    "arguments": arguments,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            raise
        emit(
            {
                "type": "tool_result",
                "name": name,
                "arguments": arguments,
                "result": result.model_dump(mode="json", exclude_none=True),
            }
        )
        return result

    async def dispatch_tool(name, arguments, url):
        # Upstream asyncio.run executes in the worker; MCP remains on its owning loop.
        future = asyncio.run_coroutine_threadsafe(call_tool(name, arguments, url), main_loop)
        return await asyncio.wrap_future(future)

    namespace["call_tool_with_1mcp"] = dispatch_tool
    model = object.__new__(agent_class)
    model.tools = copy.deepcopy(tools)
    model.tool_server_map = {name: route["server_id"] for name, route in routes.items()}
    model.url = "stdio://frozen-routes"
    model.max_round = config["max_rounds"]
    model.messages = [
        {
            "role": "system",
            "content": (
                "You are an AI agent connected to MCP tools. Complete the user's task using "
                "the supplied tools. Do not ask follow-up questions or invent successful results. "
                "Use only the supplied frozen schemas. "
                f"All workingDirectory arguments must be exactly: {workspace}"
            ),
        }
    ]

    def complete(**payload):
        nonlocal round_count
        if round_count >= config["max_rounds"]:
            failures.append("max_rounds")
            raise RuntimeError("Maximum agent rounds reached")
        round_count += 1
        settings = {
            k: config["agent"][k] for k in ("model", "temperature", "max_completion_tokens")
        }
        if config.get("send_model_seed", False):
            settings["seed"] = seed

        async def request():
            emit(
                {
                    "type": "agent_request",
                    "round": round_count,
                    "messages": copy.deepcopy(payload["messages"]),
                    "tools": payload["tools"],
                }
            )
            response = await client.chat.completions.create(**payload, **settings)
            usages.append(response.usage.model_dump() if response.usage else {})
            emit(
                {"type": "agent_response", "round": round_count, "response": response.model_dump()}
            )
            return response

        future = asyncio.run_coroutine_threadsafe(request(), main_loop)
        try:
            return future.result(timeout=timeout + 5)
        except Exception as exc:
            future.cancel()
            failures.append(f"{type(exc).__name__}: {exc}")
            raise

    model.complete_with_retry = complete  # One attempt: no hidden upstream retries.
    emit(
        {
            "type": "upstream_agent_bridge",
            "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "transport": "stdio",
            "thinking": "disabled",
            "prompt": "workspace_prompt",
            "observation_truncation": "upstream_500_characters",
            "automatic_retries": 0,
        }
    )
    answer, messages, stopped, exceeded = await asyncio.to_thread(model.run_with_server, question)
    status = (
        "failed"
        if failures and failures[-1] != "max_rounds"
        else ("completed" if stopped else "max_rounds" if exceeded or failures else "incomplete")
    )
    if status == "failed":
        raise RuntimeError(f"Upstream agent failed: {failures[-1]}")
    return {
        "answer": answer,
        "messages": messages,
        "status": status,
        "usage": runner.usage_total(usages),
        "rounds": round_count,
    }


def make_config(root, version, seed, judge_model):
    config = read_json(pilot_config_path(root))
    config.update(
        root=str(root),
        version=version,
        seed=seed,
        execution_backend="pinned_upstream_ChatModel_stdio_bridge",
        thinking_mode="disabled",
        pilot_only=True,
        tool_name_policy="native_unique",
    )
    config["agent"]["model"] = "deepseek-flash"
    config["judge"]["model"] = judge_model
    return config


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", choices=["middle", "late"], default="middle")
    parser.add_argument("--strategy", choices=["both", "no_update", "full_rewrite"], default="both")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--judge-model", default="deepseek-flash")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate metadata and plan only; no LLM or agent calls",
    )
    parser.add_argument(
        "--allow-metadata-api",
        action="store_true",
        help="Allow paid Full Rewrite requests containing the public tool metadata",
    )
    args = parser.parse_args()
    if not args.dry_run and args.strategy != "no_update" and not args.allow_metadata_api:
        parser.error(
            "Full Rewrite sends public tool metadata to the model; add --allow-metadata-api"
        )
    lock, upstream = source(root)
    task = load_task(upstream, 139)
    old = read_json(task139_metadata_path(root, "early"))
    new = read_json(task139_metadata_path(root, args.version))
    if old["benchmark_commit"] != lock["commit"] or new["version"] != args.version:
        raise ValueError("Metadata provenance mismatch")
    if {t["server_id"] for t in old["tools"]} != set(task["servers"]):
        raise ValueError("Metadata must cover the complete official task server set")
    path = upstream / "src/custom/agents/SimpleOpenAIAgent.py"
    load_upstream_class(path)
    config = make_config(root, args.version, args.seed, args.judge_model)
    config["updater"] = {
        "model": "deepseek-flash",
        "temperature": 0.0,
        "max_tokens": 16384,
        "timeout": 120,
        "api_key_env": "AGENT_API_KEY",
        "base_url_env": "AGENT_BASE_URL",
        "allow_metadata_api": args.allow_metadata_api,
    }
    for role in ("agent", "judge", "updater"):
        endpoint = os.environ.get(config[role]["base_url_env"], "")
        config[role]["model"] = model_id(config[role]["model"], endpoint)
    if not args.dry_run:
        for role in ("agent", "judge"):
            runner.credentials(config[role])
        for version in ("early", args.version):
            directory = lock["stages"][version]["directory"]
            for server, entry in lock["servers"].items():
                if not (
                    root / ".cache/mcpevol" / directory / "node_modules" / server / entry
                ).is_file():
                    raise FileNotFoundError(f"Bootstrap missing: {version}/{server}")
        node = root / ".cache/node-runtime/node_modules/node/bin/node"
        if node.is_file():
            os.environ.setdefault("MCPEVOL_NODE", str(node))
    output = (
        args.output
        or root
        / "results/raw"
        / ("baseline-pilot-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ"))
    ).resolve()
    output.mkdir(parents=True, exist_ok=False)
    strategies = ["no_update", "full_rewrite"] if args.strategy == "both" else [args.strategy]
    summary = {
        "task_id": 139,
        "target_version": args.version,
        "dry_run": args.dry_run,
        "formal_method_ready": False,
        "full_rewrite_method": "llm_full_rewrite",
        "config": config,
        "runs": [],
    }
    original_loop, original_client = runner.agent_loop, runner.AsyncOpenAI
    runner.agent_loop, runner.AsyncOpenAI = upstream_agent_loop, DeepSeekClient
    try:
        for strategy in strategies:
            folder = output / strategy
            folder.mkdir()
            if args.dry_run:
                from integration.export_baseline_knowledge import validate_envelope

                validate_envelope(old)
                validate_envelope(new)
                runner.prepare_tools(old["tools"], "no_update")
                runner.prepare_tools(new["tools"], "full_rewrite")
                item = {
                    "strategy": strategy,
                    "status": "dry_run_plan_only",
                    "planned_tool_count": len(
                        old["tools"] if strategy == "no_update" else new["tools"]
                    ),
                    "llm_rewrite_executed": False,
                    "TF": None,
                    "PE": None,
                    "ECS": None,
                }
                summary["runs"].append(item)
                write_json(output / "summary.json", summary)
                continue
            try:
                print(f"Adapting {strategy} ...", file=sys.stderr, flush=True)
                knowledge, record = adapt_for_runner(
                    old,
                    new,
                    strategy,
                    context={
                        "updater": config["updater"],
                        "audit_path": str(folder / "update-audit.json"),
                    },
                )
            except AdaptationError as exc:
                item = {
                    "strategy": strategy,
                    "status": "adaptation_failed",
                    "TF": None,
                    "PE": None,
                    "ECS": None,
                    "update_cost": exc.audit["update_cost"],
                    "error_type": exc.audit["error_type"],
                }
                summary["runs"].append(item)
                write_json(output / "summary.json", summary)
                continue
            runner.prepare_tools(knowledge["tools"], strategy)
            write_json(folder / "knowledge.json", knowledge)
            write_json(folder / "adaptation.json", record)
            current = copy.deepcopy(config)
            cost = record["update_cost"]
            current.update(
                knowledge_path=str(folder / "knowledge.json"),
                output_dir=str(folder / "execution"),
                update_cost={
                    "tokens": (
                        cost["input_tokens"] + cost["output_tokens"]
                        if cost["input_tokens"] is not None and cost["output_tokens"] is not None
                        else None
                    ),
                    "seconds": 0 if strategy == "no_update" else cost["elapsed_seconds"],
                    "usd": cost["api_cost_usd"],
                },
            )
            write_json(folder / "config.json", current)
            print(
                f"Running task 139 / {args.version} / {strategy} ...", file=sys.stderr, flush=True
            )
            _, result = runner.run(139, args.version, strategy, args.seed, current)
            item = {k: result[k] for k in ("strategy", "status", "TF", "PE", "ECS", "errors")}
            item["execution_dir"] = str(folder / "execution")
            summary["runs"].append(item)
            write_json(output / "summary.json", summary)
            if args.format == "text":
                report_path = folder / "execution/report.txt"
                if report_path.is_file():
                    print(report_path.read_text(encoding="utf-8"), end="", flush=True)
    finally:
        runner.agent_loop, runner.AsyncOpenAI = original_loop, original_client
    report = render_saved_report([output], output=output / "report.txt")
    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    elif args.dry_run or any(r["status"] == "adaptation_failed" for r in summary["runs"]):
        print(report, end="")
    print(f"Results: {output}", file=sys.stderr)
    if not args.dry_run and any(r["status"] != "evaluated" for r in summary["runs"]):
        raise SystemExit(2)


if __name__ == "__main__":
    main()

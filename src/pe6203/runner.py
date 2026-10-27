import asyncio
import copy
import hashlib
import json
import os
import random
import re
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from openai import AsyncOpenAI

from .benchmark import digest, load_task, read_json, source, write_json
from .costs import provider_usd, sum_usd
from .judge import aggregate_scores, official_prompt, parse_scores
from .report import write_report
from .transport import check_arguments, server_profiles, sessions, snapshot


def prepare_fixture(directory, workspace):
    directory, workspace = Path(directory).resolve(), Path(workspace).resolve()
    if not directory.is_dir() or workspace.is_relative_to(directory):
        raise ValueError("Fixture directory must exist and be separate from the run workspace")
    paths = sorted(directory.rglob("*"))
    if any(p.is_symlink() for p in paths):
        raise ValueError("Fixture symlinks are not allowed")
    files = []
    for path in paths:
        if path.is_file():
            relative = path.relative_to(directory)
            destination = workspace / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
            files.append(
                {
                    "path": str(relative),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
    return {"files": files, "manifest_sha256": digest(files)}


def credentials(config):
    values = []
    for field in ("api_key_env", "base_url_env"):
        name = config[field]
        value = os.environ.get(name)
        if not value:
            raise ValueError(f"Configure {name} before a real model run")
        values.append(value)
    url = urlparse(values[1])
    if (
        url.scheme not in ("https", "http")
        or not url.hostname
        or url.username
        or url.password
        or url.query
        or url.fragment
    ):
        raise ValueError("Model base URL must be an explicit HTTP(S) endpoint without credentials")
    return tuple(values)


def redact(text, secrets):
    for secret in secrets:
        if secret:
            text = text.replace(secret, "[REDACTED]")
    return text


def protocol_hash(config, endpoints):
    operational = {
        "root",
        "output_dir",
        "knowledge_path",
        "update_cost",
        "adaptation_path",
    }
    return digest(
        {
            "settings": {k: v for k, v in config.items() if k not in operational},
            "endpoints": endpoints,
        }
    )


def prepare_tools(records, strategy, name_policy="native_unique"):
    if strategy not in (
        "no_update",
        "full_rewrite",
        "selective_patch",
        "current_metadata_smoke",
    ):
        raise ValueError(f"Unknown strategy label: {strategy}")
    tools, routes = [], {}
    if name_policy not in ("native_unique", "namespaced"):
        raise ValueError(f"Unknown tool name policy: {name_policy}")
    for record in records:
        if strategy == "no_update" and record["version"] != "early":
            raise ValueError("No Update must retain an early snapshot")
        name = record["name"]
        if name_policy == "namespaced":
            identity = record["server_id"] + "::" + name
            suffix = hashlib.sha256(identity.encode()).hexdigest()[:12]
            name = re.sub(r"[^a-zA-Z0-9_-]", "_", name)[:50] + "__" + suffix
        if name in routes:
            raise ValueError(f"Duplicate model-facing tool name: {name}")
        description = record["description"]
        if record.get("usage_rules"):
            description += "\nUsage rules:\n" + json.dumps(
                record["usage_rules"], ensure_ascii=False
            )
        if record.get("output_schema") is not None:
            description += "\nOutput schema:\n" + json.dumps(
                record["output_schema"], ensure_ascii=False
            )
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": copy.deepcopy(record["parameters"]),
                },
            }
        )
        routes[name] = copy.deepcopy(record["routing"])
    if not tools:
        raise ValueError("Frozen knowledge contains no tools")
    return tools, routes


def usage_total(usages):
    total = {
        key: sum(u[key] for u in usages)
        if usages and all(type(u.get(key)) is int and u[key] >= 0 for u in usages)
        else None
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
    }
    charges = [provider_usd(usage) for usage in usages]
    total["usd"] = sum_usd(charges)
    total["known_usd"] = sum_usd(value for value in charges if value is not None)
    total["usd_source"] = "provider_usage.cost" if total["usd"] is not None else None
    return total


async def agent_loop(client, clients, tools, routes, question, workspace, config, seed, emit):
    system = (
        "You are an AI agent connected to MCP tools. Complete the user's task using "
        "the supplied tools. Do not ask the user follow-up questions. Use only the tools "
        "and schemas supplied to you. Do not invent successful tool results. "
        f"All workingDirectory arguments must be exactly: {workspace}"
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": question},
    ]
    answer, status, usages = "", "max_rounds", []
    emit({"type": "initial_messages", "messages": copy.deepcopy(messages)})
    settings = {k: config["agent"][k] for k in ("model", "temperature", "max_completion_tokens")}
    if "extra_body" in config["agent"]:
        settings["extra_body"] = copy.deepcopy(config["agent"]["extra_body"])
    if config.get("send_model_seed", False):
        settings["seed"] = seed
    for turn in range(config["max_rounds"]):
        try:
            response = await client.chat.completions.create(
                messages=messages, tools=tools, **settings
            )
        except BaseException as exc:
            emit({"type": "agent_error", "round": turn + 1, "error_type": type(exc).__name__})
            raise
        usages.append(response.usage.model_dump() if response.usage else {})
        emit(
            {
                "type": "agent_response",
                "round": turn + 1,
                "response": response.model_dump(),
            }
        )
        message = response.choices[0].message.model_dump(exclude_none=True)
        messages.append(message)
        calls = message.get("tool_calls", [])
        if not calls:
            answer = message.get("content") or ""
            status = "completed" if answer else "empty_answer"
            break
        for call in calls:
            try:
                name = call["function"]["name"]
                if name not in routes:
                    raise ValueError(f"Tool {name} is not in frozen knowledge")
                args = json.loads(call["function"]["arguments"])
                if not isinstance(args, dict):
                    raise ValueError("Tool arguments must be a JSON object")
                check_arguments(args, workspace)
                route = routes[name]
                result = await asyncio.wait_for(
                    clients[route["server_id"]].call_tool(route["tool_name"], args),
                    config.get("tool_timeout_seconds", 30),
                )
                payload = result.model_dump(mode="json", exclude_none=True)
            except Exception as exc:
                payload = {"isError": True, "error": f"{type(exc).__name__}: {exc}"}
            tool_message = {
                "role": "tool",
                "tool_call_id": call["id"],
                "content": json.dumps(payload, ensure_ascii=False),
            }
            messages.append(tool_message)
            emit(
                {
                    "type": "tool_result",
                    "round": turn + 1,
                    "call": call,
                    "result": payload,
                }
            )
    return {
        "answer": answer,
        "messages": messages,
        "status": status,
        "usage": usage_total(usages),
        "rounds": turn + 1,
    }


async def run_async(task_id, version, strategy, seed, config):
    """Return (raw_trace, benchmark_result); never discover replacement tools for the agent."""
    config = copy.deepcopy(config)
    root = Path(config.get("root", ".")).resolve()
    output = Path(config["output_dir"]).resolve()
    output.mkdir(parents=True, exist_ok=False)  # Preserve previous runs, including failures.
    workspace = output / "workspace"
    workspace.mkdir()
    started = time.monotonic()
    secrets, events = [], []
    recorded_usages = {"agent": [], "judge": []}
    result = {
        "schema_version": "1.0",
        "task_id": task_id,
        "version": version,
        "strategy": strategy,
        "seed": seed,
        "status": "blocked",
        "execution_status": "not_started",
        "judge_status": "not_started",
        "TF": None,
        "PE": None,
        "ECS": None,
        "ecs_inputs": {version: None},
        "errors": [],
        "config": config,
        "config_sha256": digest(config),
        "cost": {
            "agent": {"total_tokens": None},
            "judge": {"total_tokens": None},
            "update": config.get("update_cost"),
            "usd": None,
        },
        "started_at": datetime.now(UTC).isoformat(),
    }

    def clean(value):
        return json.loads(redact(json.dumps(value, ensure_ascii=False), secrets))

    def emit(event):
        role = {
            "agent_response": "agent",
            "agent_error": "agent",
            "judge_result": "judge",
        }.get(event.get("type"))
        if role:
            # Retain billed responses even if a later parse, tool call or request fails.
            recorded_usages[role].append((event.get("response") or {}).get("usage") or {})
            result["cost"][role] = usage_total(recorded_usages[role])
        event = clean({"elapsed_seconds": round(time.monotonic() - started, 6), **event})
        events.append(event)
        with (output / "events.jsonl").open("a") as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")

    trace = {"idx": task_id, "answer": "", "trajectory_messages": []}
    try:
        for key in (
            "max_rounds",
            "judge_runs",
            "request_timeout_seconds",
            "run_timeout_seconds",
        ):
            if type(config[key]) not in (float, int) or config[key] <= 0:
                raise ValueError(f"{key} must be positive")
        if type(config["max_rounds"]) is not int or type(config["judge_runs"]) is not int:
            raise ValueError("Round and judge-run counts must be integers")
        lock, upstream = source(root)
        task = load_task(upstream, task_id)
        if version not in lock["stages"]:
            raise ValueError(f"Unknown version: {version}")
        trace.update(task)
        profiles = server_profiles(root, lock)
        unsupported = sorted(set(task["servers"]) - set(profiles))
        if unsupported:
            raise ValueError(f"Missing reviewed runtime profiles: {', '.join(unsupported)}")
        if config.get("fixture_dir"):
            result["fixture"] = prepare_fixture(root / config["fixture_dir"], workspace)
            write_json(output / "fixture-manifest.json", result["fixture"])
        if config.get("adaptation_path"):
            artifact_path = root / config["adaptation_path"]
            artifact = read_json(artifact_path)
            if (
                artifact.get("status") != "validated"
                or artifact.get("strategy") != strategy
                or artifact.get("target_stage") != version
                or artifact.get("benchmark_commit") != lock["commit"]
            ):
                raise ValueError("Adaptation artifact does not match this run")
            adapted_path = artifact_path.parent / artifact["output"]["knowledge_path"]
            if (
                hashlib.sha256(adapted_path.read_bytes()).hexdigest()
                != artifact["output"]["knowledge_file_sha256"]
            ):
                raise ValueError("Adaptation knowledge file hash mismatch")
            config["knowledge_path"] = str(adapted_path.resolve())
            config["update_cost"] = copy.deepcopy(artifact["cost"])
            result["cost"]["update"] = copy.deepcopy(artifact["cost"])
            result["adaptation_file_sha256"] = hashlib.sha256(
                artifact_path.read_bytes()
            ).hexdigest()
            result["adaptation_method"] = artifact["cost"]["method"]
            write_json(output / "adaptation.json", artifact)
        result["config_sha256"] = digest(config)
        knowledge_path = Path(config["knowledge_path"])
        knowledge = read_json(
            knowledge_path if knowledge_path.is_absolute() else root / knowledge_path
        )
        if knowledge["benchmark_commit"] != lock["commit"]:
            raise ValueError("Knowledge snapshot benchmark commit mismatch")
        records = knowledge["tools"]
        # Vanilla should use the current stage's tool knowledge.
        # Selective Patch is allowed to retain unchanged older records.
        if strategy == "current_metadata_smoke" and (
            knowledge.get("version") != version
            or any(record.get("version") != version for record in records)
        ):
            raise ValueError(
                "Vanilla/current_metadata_smoke requires the knowledge envelope "
                "and every tool record to match the selected stage"
            )
        tools, routes = prepare_tools(
            records, strategy, config.get("tool_name_policy", "native_unique")
        )
        if any(r["server_id"] not in task["servers"] for r in routes.values()):
            raise ValueError("Knowledge routes outside the fixed task server set")
        result.update(
            {
                "benchmark_commit": lock["commit"],
                "dataset_revision": lock["dataset_revision"],
                "knowledge_sha256": digest(knowledge),
                "knowledge_version": knowledge["version"],
                "agent_model": config["agent"]["model"],
                "judge_model": config["judge"]["model"],
                "tool_name_policy": config.get("tool_name_policy", "native_unique"),
                "model_tool_routes": routes,
            }
        )
        write_json(output / "knowledge.json", knowledge)
        agent_key, agent_url = credentials(config["agent"])
        secrets.append(agent_key)
        judge_key, judge_url = credentials(config["judge"])
        secrets.append(judge_key)
        result["model_endpoints"] = {"agent": agent_url, "judge": judge_url}
        result["protocol_sha256"] = protocol_hash(config, result["model_endpoints"])
        emit({"type": "preflight_complete", "task_id": task_id, "version": version})
        async with asyncio.timeout(config["run_timeout_seconds"]):
            async with sessions(
                root,
                version,
                task["servers"],
                workspace,
                output / "mcp.stderr.log",
                config.get("tool_timeout_seconds", 30),
            ) as clients:
                # Current metadata is stored for evaluation only. It is never merged into tools.
                current = await snapshot(clients, version, lock["commit"])
                write_json(output / "environment-metadata.json", current)
                result["execution_status"] = "running"
                async with AsyncOpenAI(
                    api_key=agent_key,
                    base_url=agent_url,
                    timeout=config["request_timeout_seconds"],
                    max_retries=0,
                ) as agent:
                    outcome = await agent_loop(
                        agent,
                        clients,
                        tools,
                        routes,
                        task["question"],
                        workspace,
                        config,
                        seed,
                        emit,
                    )
                trace.update(
                    {
                        "answer": outcome["answer"],
                        "trajectory_messages": outcome["messages"],
                        "stop": outcome["status"] == "completed",
                        "exceeded": outcome["status"] == "max_rounds",
                        "involved_tools": tools,
                    }
                )
                result["execution_status"] = outcome["status"]
                result["cost"]["agent"] = outcome["usage"]
                write_json(output / "ANSWER" / f"{task_id}.json", clean(trace))
                rng, scores, judge_runs = random.Random(seed), [], []
                result["judge_status"] = "running"
                async with AsyncOpenAI(
                    api_key=judge_key,
                    base_url=judge_url,
                    timeout=config["request_timeout_seconds"],
                    max_retries=0,
                ) as judge:
                    for index in range(config["judge_runs"]):
                        order = rng.sample([0, 1, 2], 3)
                        prompt = official_prompt(
                            upstream,
                            task,
                            current["tools"],
                            outcome["messages"],
                            outcome["answer"],
                            order,
                        )
                        (output / f"judge-prompt-{index + 1}.txt").write_text(
                            redact(prompt, secrets)
                        )
                        item = {"dimension_order": order}
                        try:
                            response = await judge.chat.completions.create(
                                messages=[{"role": "user", "content": prompt}],
                                **{
                                    k: config["judge"][k]
                                    for k in (
                                        "model",
                                        "temperature",
                                        "max_completion_tokens",
                                        "extra_body",
                                    )
                                    if k in config["judge"]
                                },
                            )
                            item["response"] = response.model_dump()
                            item["result"] = parse_scores(response.choices[0].message.content or "")
                            scores.append(item["result"])
                        except asyncio.CancelledError:
                            item["error"] = "CancelledError: Judge request cancelled"
                            judge_runs.append(item)
                            emit({"type": "judge_result", "run": index + 1, **item})
                            raise
                        except Exception as exc:
                            item["error"] = f"{type(exc).__name__}: {exc}"
                        judge_runs.append(item)
                        emit({"type": "judge_result", "run": index + 1, **item})
                aggregate = aggregate_scores(scores, config["judge_runs"])
                write_json(
                    output / "EVAL" / f"{task_id}.json",
                    clean(
                        {
                            **trace,
                            "eval_result": {"runs": judge_runs, "aggregate": aggregate},
                        }
                    ),
                )
                result.update(
                    {
                        "TF": aggregate["task_fulfillment_mean"],
                        "PE": aggregate["planning_and_efficiency_mean"],
                        "judge_status": "complete" if aggregate["complete"] else "incomplete",
                        "status": "evaluated" if aggregate["complete"] else "judge_incomplete",
                        "ecs_inputs": {version: aggregate["task_fulfillment_mean"]},
                    }
                )
                result["cost"]["judge"] = usage_total(recorded_usages["judge"])
    except Exception as exc:
        for stage in ("execution_status", "judge_status"):
            if result[stage] == "running":
                result[stage] = "failed"
        result["errors"].append({"type": type(exc).__name__, "message": str(exc)})
        result["status"] = "timeout" if isinstance(exc, TimeoutError) else "blocked"
        emit({"type": "run_error", "error": result["errors"][-1]})
    finally:
        # Only publish a run total when all three stages report known amounts.
        result["cost"]["usd"] = sum_usd(
            (result["cost"].get(stage) or {}).get("usd") for stage in ("update", "agent", "judge")
        )
        result["cost"]["usd_source"] = (
            "sum_of_recorded_stage_usd" if result["cost"]["usd"] is not None else None
        )
        result["seconds"] = round(time.monotonic() - started, 6)
        # Events survive interruptions during the agent loop, before a final ANSWER exists.
        trace["events"] = events
        write_json(output / "raw_trace.json", clean(trace))
        write_json(output / "result.json", clean(result))
        try:
            write_report([output], output / "report.txt")
        except Exception as exc:
            (output / "report-error.txt").write_text(
                redact(f"{type(exc).__name__}: {exc}", secrets), encoding="utf-8"
            )
    return clean(trace), clean(result)


def run(task_id, version, strategy, seed, config):
    return asyncio.run(run_async(task_id, version, strategy, seed, config))

import asyncio
import copy
import json
import os
import random
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from openai import AsyncOpenAI

from .benchmark import digest, load_task, read_json, source, write_json
from .judge import aggregate_scores, official_prompt, parse_scores
from .report import write_report
from .transport import check_arguments, sessions, snapshot


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
    operational = {"root", "output_dir", "knowledge_path", "update_cost"}
    return digest(
        {
            "settings": {k: v for k, v in config.items() if k not in operational},
            "endpoints": endpoints,
        }
    )


def prepare_tools(records, strategy):
    if strategy not in ("no_update", "full_rewrite", "selective_patch", "current_metadata_smoke"):
        raise ValueError(f"Unknown strategy label: {strategy}")
    tools, routes = [], {}
    for record in records:
        if strategy == "no_update" and record["version"] != "early":
            raise ValueError("No Update must retain an early snapshot")
        name = record["name"]
        if name in routes:
            raise ValueError(f"Duplicate model-facing tool name: {name}")
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": record["description"],
                    "parameters": copy.deepcopy(record["parameters"]),
                },
            }
        )
        routes[name] = copy.deepcopy(record["routing"])
    if not tools:
        raise ValueError("Frozen knowledge contains no tools")
    return tools, routes


def usage_total(usages):
    return {
        key: sum(u[key] for u in usages)
        if usages and all(isinstance(u.get(key), int) for u in usages)
        else None
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
    }


async def agent_loop(client, clients, tools, routes, question, workspace, config, seed, emit):
    system = (
        "You are an AI agent connected to MCP tools. Complete the user's task using "
        "the supplied tools. Do not ask the user follow-up questions. Use only the tools "
        "and schemas supplied to you. Do not invent successful tool results. "
        f"All workingDirectory arguments must be exactly: {workspace}"
    )
    messages = [{"role": "system", "content": system}, {"role": "user", "content": question}]
    answer, status, usages = "", "max_rounds", []
    emit({"type": "initial_messages", "messages": copy.deepcopy(messages)})
    settings = {k: config["agent"][k] for k in ("model", "temperature", "max_completion_tokens")}
    if config.get("send_model_seed", False):
        settings["seed"] = seed
    for turn in range(config["max_rounds"]):
        response = await client.chat.completions.create(messages=messages, tools=tools, **settings)
        message = response.choices[0].message.model_dump(exclude_none=True)
        usages.append(response.usage.model_dump() if response.usage else {})
        emit({"type": "agent_response", "round": turn + 1, "response": response.model_dump()})
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
            emit({"type": "tool_result", "round": turn + 1, "call": call, "result": payload})
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
        event = clean({"elapsed_seconds": round(time.monotonic() - started, 6), **event})
        events.append(event)
        with (output / "events.jsonl").open("a") as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")

    trace = {"idx": task_id, "answer": "", "trajectory_messages": []}
    try:
        for key in ("max_rounds", "judge_runs", "request_timeout_seconds", "run_timeout_seconds"):
            if type(config[key]) not in (float, int) or config[key] <= 0:
                raise ValueError(f"{key} must be positive")
        if type(config["max_rounds"]) is not int or type(config["judge_runs"]) is not int:
            raise ValueError("Round and judge-run counts must be integers")
        lock, upstream = source(root)
        task = load_task(upstream, task_id)
        if task_id != lock["smoke_task_id"]:
            raise ValueError(
                "This handoff validates task 139 only; review new servers before expanding"
            )
        if version not in lock["stages"]:
            raise ValueError(f"Unknown version: {version}")
        trace.update(task)
        knowledge_path = Path(config["knowledge_path"])
        knowledge = read_json(
            knowledge_path if knowledge_path.is_absolute() else root / knowledge_path
        )
        if knowledge["benchmark_commit"] != lock["commit"]:
            raise ValueError("Knowledge snapshot benchmark commit mismatch")
        records = knowledge["tools"]
        tools, routes = prepare_tools(records, strategy)
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
                rng, scores, judge_runs, usages = random.Random(seed), [], [], []
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
                                    for k in ("model", "temperature", "max_completion_tokens")
                                },
                            )
                            item["response"] = response.model_dump()
                            usages.append(response.usage.model_dump() if response.usage else {})
                            item["result"] = parse_scores(response.choices[0].message.content or "")
                            scores.append(item["result"])
                        except Exception as exc:
                            item["error"] = f"{type(exc).__name__}: {exc}"
                        judge_runs.append(item)
                        emit({"type": "judge_result", "run": index + 1, **item})
                aggregate = aggregate_scores(scores, config["judge_runs"])
                write_json(
                    output / "EVAL" / f"{task_id}.json",
                    clean({**trace, "eval_result": {"runs": judge_runs, "aggregate": aggregate}}),
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
                result["cost"]["judge"] = usage_total(usages)
    except Exception as exc:
        for stage in ("execution_status", "judge_status"):
            if result[stage] == "running":
                result[stage] = "failed"
        result["errors"].append({"type": type(exc).__name__, "message": str(exc)})
        result["status"] = "timeout" if isinstance(exc, TimeoutError) else "blocked"
        emit({"type": "run_error", "error": result["errors"][-1]})
    finally:
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

"""Official prompt, strict score parsing, and explicitly named ECS conventions."""

import ast
import asyncio
import json
import math
import os
import re
import statistics
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCORE_KEYS = ("task_fulfillment", "grounding", "planning_and_efficiency")

CONCISE_CONTRACT = (
    "\n\nResponse format only (the rubric above is unchanged): Return exactly one JSON object. "
    "Include the integer scores task_fulfillment, grounding, planning_and_efficiency, "
    "and the rubric's rationale fields. Each rationale must be one short sentence, "
    "at most 40 words, retaining the required counts and defect rates. "
    "No repeated analysis, markdown or additional prose."
)


def measurement_prompt(original, messages):
    """Append checkable input facts without changing the benchmark rubric or assigning issues."""
    calls = [call for message in messages for call in message.get("tool_calls", [])]
    observations = [message for message in messages if message.get("role") == "tool"]
    answered = {message.get("tool_call_id") for message in observations}
    errors = 0
    for message in observations:
        try:
            payload = json.loads(message.get("content", ""))
        except (ValueError, TypeError):
            continue
        errors += bool(isinstance(payload, dict) and payload.get("isError"))
    counts = {
        "tool_call_proposals": len(calls),
        "tool_result_observations": len(observations),
        "unanswered_proposals": sum(c.get("id") not in answered for c in calls),
        "tool_error_results": errors,
        "proposals_per_tool": dict(Counter(c["function"]["name"] for c in calls)),
    }
    return (
        original
        + "\n\n# Recorded trajectory counts (input facts, not scores)\n"
        + json.dumps(counts, ensure_ascii=False, indent=2)
        + "\nThese counts enumerate each call in batched tool_calls individually. "
        "Errors are not automatically redundant; apply the original rubric to identify issues. "
        "Use consistent issue/total counts and percentages in the rationale." + CONCISE_CONTRACT
    )


def save_once(path, value):
    """Publish a complete immutable record; an interrupted temporary file is not evidence."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ValueError(f"Refusing to overwrite evidence: {path.name}")
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def _rating(response):
    try:
        choice = response["choices"][0]
        if choice.get("finish_reason") != "stop":
            raise ValueError("Judge response did not finish normally")
        return {"response": response, "result": parse_scores(choice["message"]["content"] or "")}
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        return {
            "response": response,
            "error": f"{type(exc).__name__}: invalid judge output",
            "failure_category": "judge_format",
            "retryable": True,
        }


async def evaluate_slots(client, output, prompts, config, emit):
    """First valid rating per slot; append-only attempts and bounded, resumable recovery."""
    from .benchmark import digest, read_json
    from .request_retry import failure_details, request_async

    output = Path(output)
    policy = config["judge_recovery"]
    maximum = policy["max_attempts"]
    stop_after = policy["stop_after_transport_failures"]
    if type(maximum) is not int or not 1 <= maximum <= 2 or stop_after != 2:
        raise ValueError("Judge recovery requires 1–2 attempts and a two-failure circuit breaker")
    manifest = {
        "prompts": prompts,
        "judge": config["judge"],
        "recovery": policy,
        "request_retry": config.get("request_retry"),
    }
    manifest_path = output / "judge-plan.json"
    if manifest_path.exists():
        if digest(read_json(manifest_path)) != digest(manifest):
            raise ValueError("Frozen judge inputs changed; prepare a new experiment")
    else:
        save_once(manifest_path, manifest)
    histories = [[] for _ in prompts]

    def restore(index):
        history = []
        for number in range(1, maximum + 1):
            directory = output / "judge-attempts" / f"slot-{index + 1}-attempt-{number}"
            if not (directory / "request.json").exists():
                break
            outcome = directory / "outcome.json"
            if not outcome.exists():
                if (directory / "response.json").exists():
                    item = _rating(read_json(directory / "response.json"))
                else:
                    item = {
                        "error": "Interrupted request; usage unknown",
                        "retryable": True,
                        "failure_category": "interrupted",
                    }
                save_once(outcome, {"slot": index + 1, "attempt": number, **item})
            history.append(read_json(outcome))
        return history

    def eligible(history):
        return (
            len(history) < maximum
            and not any("result" in a for a in history)
            and (not history or history[-1].get("retryable", False))
        )

    for index in range(len(prompts)):
        histories[index] = restore(index)
    fatal = any(h and h[-1].get("failure_category") == "model_request" for h in histories)
    consecutive, paused = 0, False
    for _ in range(maximum):
        if fatal or paused:
            break
        for index, prompt in enumerate(prompts):
            history = histories[index]
            if not eligible(history):
                continue
            number = len(history) + 1
            directory = output / "judge-attempts" / f"slot-{index + 1}-attempt-{number}"
            settings = {
                k: config["judge"][k]
                for k in ("model", "temperature", "max_completion_tokens", "extra_body")
                if k in config["judge"]
            }
            save_once(
                directory / "request.json",
                {
                    "slot": index + 1,
                    "attempt": number,
                    "prompt_sha256": digest(prompt),
                    "settings": settings,
                    "started_at": datetime.now(UTC).isoformat(),
                },
            )

            def on_retry(event):
                event = {"recorded_at": datetime.now(UTC).isoformat(), **event}
                save_once(directory / f"retry-{event['failed_attempt']}.json", event)
                emit(
                    {
                        "type": "request_retry",
                        "role": "judge",
                        "run": index + 1,
                        "attempt": number,
                        **event,
                    }
                )

            try:
                response = await request_async(
                    lambda: client.chat.completions.create(
                        messages=[{"role": "user", "content": prompt}], **settings
                    ),
                    config.get("request_retry"),
                    on_retry,
                )
            except asyncio.CancelledError:
                save_once(
                    directory / "outcome.json",
                    {
                        "slot": index + 1,
                        "attempt": number,
                        "error": "CancelledError",
                        "retryable": True,
                        "failure_category": "interrupted",
                    },
                )
                raise
            except Exception as exc:
                transient = failure_details(exc)["failure_category"] == "model_transport"
                item = {
                    "error": f"{type(exc).__name__}: model request failed",
                    "failure_category": "model_transport" if transient else "model_request",
                    "retryable": transient,
                }
                fatal = not transient
            else:
                packed = response.model_dump()
                save_once(directory / "response.json", packed)
                emit({"type": "judge_response_saved", "run": index + 1, "attempt": number})
                item = _rating(packed)
            item = {
                "slot": index + 1,
                "attempt": number,
                "finished_at": datetime.now(UTC).isoformat(),
                **item,
            }
            save_once(directory / "outcome.json", item)
            history.append(item)
            emit({"type": "judge_result", "run": index + 1, **item})
            consecutive = (
                consecutive + 1 if item.get("failure_category") == "model_transport" else 0
            )
            paused = consecutive >= stop_after
            if paused or fatal:
                break
    runs, attempts, usages = [], [], []
    for index, history in enumerate(histories):
        runs.append(
            next(
                (a for a in history if "result" in a),
                history[-1] if history else {"slot": index + 1, "error": "not_attempted"},
            )
        )
        attempts.extend(history)
        for item in history:
            directory = output / "judge-attempts" / f"slot-{index + 1}-attempt-{item['attempt']}"
            usages.extend({} for _ in directory.glob("retry-*.json"))
            usages.append(item.get("response", {}).get("usage") or {})
    return {
        "runs": runs,
        "attempts": attempts,
        "usages": usages,
        "aggregate": aggregate_scores([r["result"] for r in runs if "result" in r], len(prompts)),
        "paused": paused,
        "resumable": not fatal and any(eligible(h) for h in histories),
    }


def parse_scores(raw):
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    result = json.loads(text)
    if not isinstance(result, dict):
        raise ValueError("Judge response must be an object")
    for key in SCORE_KEYS:
        value = result.get(key)
        if type(value) is not int or not 1 <= value <= 10:
            raise ValueError(f"Invalid or missing judge score: {key}")
    return result


def aggregate_scores(scores, expected):
    return {
        "successful_runs": len(scores),
        "total_runs": expected,
        "complete": len(scores) == expected,
        **{
            key + "_mean": statistics.mean(s[key] for s in scores) if scores else None
            for key in SCORE_KEYS
        },
    }


def ecs(scores):
    values = [scores.get(stage) for stage in ("early", "middle", "late")]
    valid = all(type(x) in (float, int) and math.isfinite(x) and 1 <= x <= 10 for x in values)
    return {
        "upstream_population": statistics.mean(values) - statistics.pstdev(values)
        if valid
        else None,
        "paper_sample": statistics.mean(values) - statistics.stdev(values) if valid else None,
        "complete": valid,
        "tf_by_version": scores,
    }


def official_prompt(upstream, task, records, messages, answer, dimension_order):
    path = upstream / "src/custom/prompt/eval_error_prompt.py"
    namespace = {"json": json, "Any": Any, "Dict": dict, "List": list}
    # Execute the pinned, audited prompt module without writing into the checkout.
    exec(compile(path.read_text(), str(path), "exec"), namespace)
    # The upstream evaluator imports a missing mutation module and connects to a
    # hard-coded MCP URL at import time. Load only its unmodified pure formatting
    # functions, avoiding those unrelated import-time effects.
    for relative, names in [
        (
            "src/custom/analysis/answer/evaluation.py",
            {"messages_to_string", "truncate_tool_content"},
        ),
        ("src/custom/utils/test_utils.py", {"format_tools_to_string"}),
    ]:
        source_path = upstream / relative
        tree = ast.parse(source_path.read_text())
        selected = [
            node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names
        ]
        if len(selected) != len(names):
            raise ValueError("Pinned upstream judge formatting functions are missing")
        exec(
            compile(ast.Module(body=selected, type_ignores=[]), str(source_path), "exec"), namespace
        )
    descriptions = ""
    for server, tool_names in task["servers"].items():
        descriptions += f"Tools for Server - {server}: \n"
        tools = [
            {
                "name": r["name"],
                "description": r["description"],
                "inputSchema": r["parameters"],
                "outputSchema": r.get("output_schema"),
            }
            for r in records
            if r["server_id"] == server and r["name"] in tool_names
        ]
        if tools:
            descriptions += namespace["format_tools_to_string"](tools) + "\n"
        descriptions += "\n"
    trajectory = namespace["truncate_tool_content"](messages)[2:]
    return namespace["build_mcp_bench_judge_prompt"](
        task["question"],
        descriptions,
        namespace["messages_to_string"](trajectory),
        answer,
        dimension_order=tuple(dimension_order),
    )

"""Official prompt, strict score parsing, and explicitly named ECS conventions."""

import ast
import json
import math
import re
import statistics
from typing import Any

SCORE_KEYS = ("task_fulfillment", "grounding", "planning_and_efficiency")


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

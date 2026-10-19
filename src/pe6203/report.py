"""Offline reports from recorded runs or reviewed evidence; never invoke models."""

import json
from collections import Counter
from html import escape
from pathlib import Path

from .benchmark import read_json
from .terminal_report import render_report


def optional_json(path, default):
    return read_json(path) if path.is_file() else default


def load_run(path):
    path = Path(path)
    if path.is_dir():
        result = read_json(path / "result.json")
        trace = optional_json(path / "raw_trace.json", {})
        events = trace.get("events", [])
        bundle = {
            "result": result,
            "question": trace.get("question", ""),
            "answer": trace.get("answer", ""),
            "event_counts": {"tool_result": 0, **dict(Counter(e["type"] for e in events))},
            "tool_results": [e for e in events if e["type"] == "tool_result"],
            "judge_runs": [e for e in events if e["type"] == "judge_result"],
        }
        if not (path / "raw_trace.json").is_file():
            bundle.pop("event_counts")
            bundle.pop("tool_results")
            bundle.pop("judge_runs")
        tasks = optional_json(path / "workspace/.agentic-tools-mcp/tasks/tasks.json", {})
        graph_path = path / "workspace/knowledge.jsonl"
        graph = (
            [json.loads(line) for line in graph_path.read_text().splitlines() if line.strip()]
            if graph_path.is_file()
            else []
        )
        bundle["persisted_state"] = {"project_and_tasks": tasks, "knowledge_graph": graph}
    else:
        bundle = read_json(path)
        if "task_id" in bundle and "status" in bundle:
            bundle = {"result": bundle}
        result = bundle.get("result", {})
    if "task_id" not in result or "status" not in result:
        raise ValueError(f"Not a run directory or reviewed run evidence: {path.name}")
    events = bundle.get("tool_results", bundle.get("tool_errors", []))
    routes = result.get("model_tool_routes", {})
    calls = []
    for event in events:
        function = event["call"]["function"]
        try:
            arguments = json.loads(function["arguments"])
        except (ValueError, TypeError):
            arguments = function.get("arguments")
        calls.append(
            {
                "round": event.get("round"),
                "seconds": event.get("elapsed_seconds"),
                "name": routes.get(function["name"], {}).get("tool_name", function["name"]),
                "arguments": arguments,
                "error": bool(event["result"].get("isError")),
                "output": event["result"],
            }
        )
    judges = []
    for item in bundle.get("judge_runs", []):
        choice = (item.get("response", {}).get("choices") or [{}])[0]
        judges.append(
            {
                "scores": item.get("result"),
                "error": item.get("error"),
                "finish_reason": item.get("finish_reason", choice.get("finish_reason")),
            }
        )
    state = bundle.get("persisted_state", {})
    tasks = state.get("project_and_tasks", {})
    graph = state.get("knowledge_graph", [])
    counts = dict(bundle.get("state_checks", {}))
    if tasks:
        counts.update(
            project_count=len(tasks.get("projects", [])), task_count=len(tasks.get("tasks", []))
        )
    if graph:
        counts.update(
            entity_count=sum(x.get("type") == "entity" for x in graph),
            relation_count=sum(x.get("type") == "relation" for x in graph),
        )
    tool_count = bundle.get("event_counts", {}).get("tool_result")
    if tool_count is None and "tool_results" in bundle:
        tool_count = len(calls)
    config = result.get("config", {})
    data = {
        "label": path.stem if path.is_file() else path.name,
        "task_id": result["task_id"],
        "version": result.get("version"),
        "strategy": result.get("strategy"),
        "seed": result.get("seed"),
        "status": result["status"],
        "execution_status": result.get("execution_status"),
        "judge_status": result.get("judge_status"),
        "started_at": result.get("started_at"),
        "seconds": result.get("seconds"),
        "model": result.get("agent_model", config.get("agent", {}).get("model")),
        "judge_model": result.get("judge_model", config.get("judge", {}).get("model")),
        "protocol": result.get("protocol_sha256"),
        "scores": {key: result.get(key) for key in ("TF", "PE", "ECS")},
        "cost": result.get("cost", {}),
        "errors": result.get("errors", []),
        "question": bundle.get("question", ""),
        "answer": bundle.get("answer", ""),
        "scope": bundle.get("scope", "运行记录；是否为正式实验请核对冻结协议"),
        "audit_note": bundle.get("audit_note"),
        "tool_count": tool_count,
        "tool_errors": sum(c["error"] for c in calls) if tool_count is not None else None,
        "trace_complete": len(calls) == tool_count,
        "calls": calls,
        "judges": judges,
        "judge_records_available": "judge_runs" in bundle,
        "judge_expected": config.get("judge_runs"),
        "state_counts": counts,
        "projects": tasks.get("projects", []),
        "tasks": tasks.get("tasks", []),
        "graph": graph,
        "source": path.name,
    }
    # Include selected observation fields only, not arbitrary config/hidden model reasoning.
    text = json.dumps(data, ensure_ascii=False)
    root = config.get("root")
    if root and root != "/":
        text = text.replace(str(root), "<REPO>")
    return json.loads(text)


def render_saved_report(inputs, *, format_name="text", expanded=False, output=None):
    runs = [load_run(path) for path in inputs]
    if not runs:
        raise ValueError("Provide at least one run")
    protocols = {r["protocol"] for r in runs if r["protocol"]}
    data = {"runs": runs, "protocols_differ": len(protocols) > 1}
    if format_name == "text":
        rendered = render_report(data, expanded=expanded)
    elif format_name == "json":
        rendered = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    elif format_name == "html":
        # Preserve the optional offline export, using the same readable text as CLI.
        inert = json.dumps(data, ensure_ascii=False)
        inert = inert.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
        rendered = (
            '<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            "<title>PE6203 · Benchmark 运行报告</title>"
            "<style>body{margin:2rem;line-height:1.6}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>"
            f"<pre>{escape(render_report(data, expanded=True))}</pre>"
            f'<script id="report-data" type="application/json">{inert}</script></html>\n'
        )
    else:
        raise ValueError(f"Unknown report format: {format_name}")
    if output is not None:
        output = Path(output)
        suffix = {"text": ".txt", "json": ".json", "html": ".html"}[format_name]
        if output.suffix.lower() != suffix:
            raise ValueError(f"Report output must be a new {suffix} file")
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as stream:
            stream.write(rendered)
    return rendered


def write_report(inputs, output):
    inputs = list(inputs)
    output = Path(output)
    format_name = "html" if output.suffix.lower() == ".html" else "text"
    render_saved_report(inputs, format_name=format_name, output=output)
    return {"report": str(output.resolve()), "runs": len(inputs)}

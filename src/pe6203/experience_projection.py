"""Closed-schema operation feedback for the fixed synthetic training pool.

Source facts, expected answers, final prose and reasoning are never exported.
This is deliberately narrower than GEPA's official MCP reflective dataset.
"""

import json
import re

PROPERTIES = {"artifact", "facts", "calculations", "decision", "coverage", "render", "delivery"}
NATIVE_TOOLS = {
    "read_pdf",
    "get_slidev_usage",
    "check_environment",
    "create_slidev",
    "load_slidev",
    "make_cover",
    "add_page",
    "set_page",
    "get_page",
    "get_all_slides",
    "get_slide_structure",
    "create_bulk_slides",
    "apply_theme",
    "add_animation",
    "add_component",
    "review_slides",
    "websearch",
    "start_slidev",
    "search_npm_packages",
    "search_slidev_themes",
    "export_slidev",
}


def project_episode(episode_id, trace, routes, properties):
    if trace.get("task_id") not in (900201, 900202) or not re.fullmatch(r"E0[1-4]", episode_id):
        raise ValueError("Only frozen generic episodes may enter reflection")
    if set(properties) - PROPERTIES or any(
        v not in ("pass", "fail", "unknown") for v in properties.values()
    ):
        raise ValueError("Feedback must use property enums, never answers")
    status = trace.get("execution_status")
    if status not in {
        "completed",
        "output_truncated",
        "max_rounds",
        "error",
        "timeout",
        "not_started",
    }:
        raise ValueError("Unrecognized execution status")
    calls = []
    for event in trace["events"]:
        if event.get("type") != "tool_result":
            continue
        call = event["call"]["function"]
        name = routes.get(call["name"], {}).get("tool_name")
        if name not in NATIVE_TOOLS:
            raise ValueError("Unrecognized native tool")
        try:
            args = json.loads(call["arguments"])
        except (TypeError, ValueError):
            args = {}
        if not isinstance(args, dict):
            args = {}
        safe = {}
        if type(args.get("index")) is int and 0 <= args["index"] <= 100:
            safe["index"] = args["index"]
        for key, allowed in {
            "layout": {"default", "center", "cover", "two-cols", "section"},
            "themeName": {"dark", "default"},
        }.items():
            if isinstance(args.get(key), str) and args[key] in allowed:
                safe[key] = args[key]
        calls.append(
            {
                "event_id": f"{episode_id}-C{len(calls) + 1:02}",
                "native_tool": name,
                "argument_keys": sorted(
                    set(args)
                    & {
                        "content",
                        "path",
                        "index",
                        "layout",
                        "themeName",
                        "slides",
                        "title",
                        "author",
                        "url",
                    }
                ),
                "safe_values": safe,
                "content_characters": len(args["content"])
                if isinstance(args.get("content"), str)
                else 0,
                "native_is_error": bool(event["result"].get("isError", False)),
            }
        )
    return {
        "episode": episode_id,
        "execution_status": status,
        "calls": calls,
        "properties": dict(properties),
    }


def training_gate(rows):
    if len(rows) != 4 or {r["episode"] for r in rows} != {f"E{i:02}" for i in range(1, 5)}:
        raise ValueError("Exactly the four frozen episodes are required")
    positives = [
        r["episode"] for r in rows if r["normal_completion"] is True and r["core_pass"] is True
    ]
    failures = [
        r["episode"] for r in rows if r["normal_completion"] is False or r["core_pass"] is False
    ]
    return {
        "admit_reflection": bool(positives and failures),
        "positive_episodes": positives,
        "failed_episodes": failures,
        "additional_sampling_allowed": False,
    }

"""Attach frozen, generic native programs only after evidence and contract gates.

This is program-valued static knowledge, not Voyager's executor or curriculum.
No benchmark questions, answers, task traces, or runtime files are inputs.
"""
from copy import deepcopy
import json
from pathlib import Path

from .native_argument_routing import expected_routing
from .selective import validate_adaptation

SPEC = Path(__file__).resolve().parents[2] / "experiments/verified-component-memory-v1.json"
KIND = "verified_component_program_v1"
SERVER = "@magicuidesign/mcp"


def expected_memory(base, target, feedback):
    memory_rows = [r for r in feedback if isinstance(r, dict)
                   and isinstance(r.get("result"), dict) and r["result"].get("kind") == KIND]
    other_rows = [r for r in feedback if r not in memory_rows]
    knowledge, log = expected_routing(base, target, other_rows)
    if not log:
        return knowledge, []
    programs = json.loads(SPEC.read_text())["programs"]
    expected = [{"stage": "late", "server": SERVER, "tool": p["tool"],
                 "args": {}, "result": {"kind": KIND, **p}} for p in programs]
    if len(memory_rows) != len(expected) or any(row not in memory_rows for row in expected):
        raise ValueError("Missing or unverified program memory evidence")
    tools = {t["tool_id"]: t for t in knowledge["tools"]}
    by_id = {c["tool_id"]: c for c in log}
    for program in programs:
        tool_id = SERVER + "::" + program["tool"]
        before = tools[tool_id]["description"]
        after = before + "\nVerified program memory:\n" + json.dumps(program, ensure_ascii=False)
        tools[tool_id]["description"] = after
        log.append({"operation": "attach_verified_program", "tool_id": tool_id,
                    "path": "description", "before": before, "after": after,
                    "basis": by_id[tool_id]["basis"],
                    "evidence": program["environment_proof_sha256"],
                    "program_sha256": program["content_sha256"]})
    return knowledge, log


def validate_memory(candidate, old, target, base, feedback):
    expected, log = expected_memory(base, target, feedback)
    if candidate != expected:
        return {"errors": ["Candidate differs from the frozen program memory delta"],
                "checks": {"operations": len(log)}}
    restored = deepcopy(candidate)
    originals = {t["tool_id"]: t for t in base["knowledge"]["tools"]}
    for tool in restored["tools"]:
        tool["description"] = originals[tool["tool_id"]]["description"]
    result = validate_adaptation(restored, old, target, base["diff"])
    result["checks"]["program_memory_operations"] = len(log)
    return result

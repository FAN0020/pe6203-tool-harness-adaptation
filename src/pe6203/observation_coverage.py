"""Compile source/native observation projections into change-local static knowledge.

No actor state, tools, response filtering, planner or runtime hooks are added.
"""

import hashlib
from copy import deepcopy

from .selective import canonical

HOST = "@pimzino/agentic-tools-mcp::create_project"
CERTIFICATES = {
    "middle": "3b3945c6246ef43357c340d98a32701217421e63b045cf845b29f7f479fae664",
    "late": "fb7ad21126c2efacdc896b8d1dbe38b42a2786dc36f8810952869c8a00150d6e",
}


def digest(x):
    return hashlib.sha256(canonical(x).encode()).hexdigest()


def projection_gap(required, observed):
    return sorted(set(required) - set(observed))


def render_contract(cert):
    operators = cert["operators"]
    union = sorted(
        {field for op in operators for field in op["exact"] if field.startswith("task.")}
    )
    get = next(op for op in operators if op["tool"] == "get_task")
    lines = [
        "OBSERVATION CONTRACT: exact fields and validity of returned evidence, not extra task requirements."
    ]
    for op in operators:
        lines.append(op["tool"] + " => " + ",".join(op["exact"]) + ". " + op["conditions"])
    lines.append("Unobservable by get_task: " + ",".join(projection_gap(union, get["exact"])) + ".")
    lines.extend(cert["freshness"][k] for k in ("accept", "invalidate", "completion"))
    return "\n".join(lines)


def compile_knowledge(base, target, feedback):
    knowledge = deepcopy(base["knowledge"])
    changed = {r["tool_id"] for r in base["diff"]["changed"] + base["diff"]["added"]}
    if base["status"] == "no_change" or HOST not in changed:
        return knowledge, []
    stage = target["version"]
    if stage not in CERTIFICATES:
        raise ValueError("Unverified stage")
    rows = [
        r
        for r in feedback
        if r.get("stage") == stage
        and r.get("server") == "@pimzino/agentic-tools-mcp"
        and r.get("tool") == "create_project"
    ]
    if len(rows) != 1 or digest(rows[0]["result"]) != CERTIFICATES[stage]:
        raise ValueError("Exact source/native observation certificate required")
    cert = rows[0]["result"]
    native = {t["tool_id"]: t for t in target["tools"]}
    for identity, expected in cert["contracts"].items():
        if identity not in native or digest(native[identity]) != expected:
            raise ValueError("Certified producer/observation contract changed")
    host = next(t for t in knowledge["tools"] if t["tool_id"] == HOST)
    host["description"] += "\n\n" + render_contract(cert)
    return knowledge, [
        {
            "operation": "compile_observation_coverage",
            "tool_id": HOST,
            "field": "description",
            "evidence": CERTIFICATES[stage],
        }
    ]

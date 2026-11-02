"""Source/native-certified ready-link knowledge; no change to actor execution."""

import hashlib
from copy import deepcopy

from .selective import canonical

PRODUCER = "@pimzino/agentic-tools-mcp::create_project"
CERTIFICATES = {
    "middle": "8b6879be130da731d607e1f8cbe8503dddd7a0755824c878374a460c103fd7f1",
    "late": "ba2bc33464b7c6dd42274aa4ec8f4436cd8518b558e24ed70b7f8b040f85e069",
}


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def compile_knowledge(base, target, feedback):
    knowledge = deepcopy(base["knowledge"])
    changed = {r["tool_id"] for r in base["diff"]["changed"] + base["diff"]["added"]}
    if base["status"] == "no_change" or PRODUCER not in changed:
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
        raise ValueError("Exact source/native ready-link certificate required")
    cert = rows[0]["result"]
    native = {t["tool_id"]: t for t in target["tools"]}
    for identity, expected in cert["contracts"].items():
        if identity not in native or digest(native[identity]) != expected:
            raise ValueError("Native producer or consumer contract changed")
    host = next(t for t in knowledge["tools"] if t["tool_id"] == PRODUCER)
    host["description"] += "\n\n" + cert["description_suffix"]
    return knowledge, [
        dict(
            operation="append_certified_ready_link",
            tool_id=PRODUCER,
            field="description",
            evidence=CERTIFICATES[stage],
        )
    ]

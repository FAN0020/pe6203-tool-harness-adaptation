"""Static source-certified record/link dataflow on an actually changed project producer."""

import hashlib
from copy import deepcopy

from .selective import canonical

PRODUCER = "@pimzino/agentic-tools-mcp::create_project"
CERTIFICATES = {
    "middle": "4a96b1b30b9ec791f3ef1fd4a835e3a49b22446bb69c4770ebbb19ae57e10b9b",
    "late": "e3f13f4a8d5093e3280726fd2ec728964cf105461d7fe0c72716e5efe8a57563",
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
        raise ValueError("Exact source/native dependency-cut certificate required")
    cert = rows[0]["result"]
    native = {t["tool_id"]: t for t in target["tools"]}
    for identity, expected in cert["contracts"].items():
        if identity not in native or digest(native[identity]) != expected:
            raise ValueError("Native producer or consumer contract changed")
    tool = next(t for t in knowledge["tools"] if t["tool_id"] == PRODUCER)
    tool["description"] += "\n\n" + cert["description_suffix"]
    return knowledge, [
        {
            "operation": "append_certified_dependency_dataflow",
            "tool_id": PRODUCER,
            "field": "description",
            "evidence": CERTIFICATES[stage],
        }
    ]

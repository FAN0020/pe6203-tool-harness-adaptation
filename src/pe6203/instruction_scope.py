"""Source-derived contract views for changed thinking metadata; static knowledge only."""

import hashlib
from copy import deepcopy

from .selective import canonical

SERVER = "@modelcontextprotocol/server-sequential-thinking"
HOSTS = {
    SERVER + "::" + n for n in ["sequentialthinking", "parallel-thinking", "convergent-synthesis"]
}
CERTIFICATES = {
    "middle": "124f6373b11c449431b9bc81ba8e6653a2a4429fb28d6ae6b610cb927d31bd28",
    "late": "721e3e66ce1d42bc28cf64b60780b4d8a85ea995f56a4fa18040d3660fda35d3",
}


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def compile_knowledge(base, target, feedback, quoted=False):
    knowledge = deepcopy(base["knowledge"])
    changed = {r["tool_id"] for r in base["diff"]["changed"] + base["diff"]["added"]}
    if base["status"] == "no_change" or not changed.intersection(HOSTS):
        return knowledge, []
    stage = target["version"]
    rows = [
        r
        for r in feedback
        if r.get("stage") == stage
        and r.get("server") == SERVER
        and r.get("tool") == "__instruction_scope__"
    ]
    if (
        stage not in CERTIFICATES
        or len(rows) != 1
        or digest(rows[0]["result"]) != CERTIFICATES[stage]
    ):
        raise ValueError("Exact reviewed instruction-scope certificate required")
    native = {t["tool_id"]: t for t in target["tools"]}
    edits = rows[0]["result"]["edits"]
    if {e["tool_id"] for e in edits} != changed.intersection(HOSTS):
        raise ValueError("Certificate must exactly cover applicable changed hosts")
    changes = []
    for edit in edits:
        tid = edit["tool_id"]
        if digest(native[tid]) != edit["record_sha256"]:
            raise ValueError("Unknown native contract")
        tool = next(t for t in knowledge["tools"] if t["tool_id"] == tid)
        if tool["description"] != edit["before"]:
            raise ValueError("Unexpected SP base description")
        tool["description"] = edit["quoted" if quoted else "after"]
        changes.append(
            dict(
                operation="quote_vendor_narrative" if quoted else "retract_vendor_narrative",
                tool_id=tid,
                field="description",
                evidence=CERTIFICATES[stage],
            )
        )
    return knowledge, changes

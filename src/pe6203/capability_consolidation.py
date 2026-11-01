"""Consolidate a changed syntax capability into a certified existing native mode.

Only static model knowledge changes. Native tools, actor dispatch, schemas of
retained tools, and unrelated records are preserved. This is a bounded manual
source certificate, not a generic JavaScript equivalence prover.
"""

import hashlib
from copy import deepcopy

from .selective import canonical

CERTIFICATE_SHA256 = "e5d327d73ddd3909158dde03c2f335d4e116be6d8fb009eaf182c165f7c5da7b"


def compile_knowledge(base, target, feedback):
    knowledge = deepcopy(base["knowledge"])
    if base["status"] == "no_change" or not any(
        t["server_id"] == "math-mcp" for t in target["tools"]
    ):
        return knowledge, []
    rows = [r for r in feedback if r.get("server") == "syntax_capability_certificate"]
    if len(rows) != 1:
        raise ValueError("Missing unique syntax capability certificate")
    certificate = rows[0]["result"]
    if hashlib.sha256(canonical(certificate).encode()).hexdigest() != CERTIFICATE_SHA256:
        raise ValueError("Unreviewed equivalence certificate")
    matches = [r for r in certificate["certificates"] if r["stage"] == target["version"]]
    if len(matches) != 1:
        raise ValueError("Uncertified release")
    row = matches[0]
    changed = {r["tool_id"] for r in base["diff"]["changed"] + base["diff"]["added"]}
    native = {t["tool_id"]: t for t in target["tools"]}
    by = {t["tool_id"]: t for t in knowledge["tools"]}
    if row["from"] not in changed or row["from"] not in by or row["to"] not in by:
        raise ValueError(
            "Consolidation needs actual changed capability and retained representative"
        )
    for identity, expected in row["record_hashes"].items():
        if (
            identity not in native
            or hashlib.sha256(canonical(native[identity]).encode()).hexdigest() != expected
        ):
            raise ValueError("Unknown native capability record")
    before = deepcopy(by[row["from"]])
    knowledge["tools"] = [t for t in knowledge["tools"] if t["tool_id"] != row["from"]]
    by[row["to"]]["usage_rules"].append(row["note"])
    return knowledge, [
        {
            "operation": "consolidate_equivalent_capability",
            "tool_id": row["from"],
            "representative": row["to"],
            "before": before,
            "evidence": CERTIFICATE_SHA256,
        },
        {
            "operation": "annotate_certified_representative_mode",
            "tool_id": row["to"],
            "after": row["note"],
            "mapping": row["mapping"],
            "evidence": CERTIFICATE_SHA256,
        },
    ]

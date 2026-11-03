"""Withdraw certified failed capabilities from static model-facing knowledge.

Native registration, validation, argument dispatch and actor execution are untouched.
This bounded certificate is not a general proof of arbitrary tool unavailability.
"""

import hashlib
from copy import deepcopy

from .selective import canonical

CERTIFICATE_SHA256 = "8e6c55699beefbcd6286c6a09f2f04f886a6afd1766fdda8e6799c035fc2714f"


def compile_knowledge(base, target, feedback, *, withdraw):
    knowledge = deepcopy(base["knowledge"])
    if base["status"] == "no_change" or not any(
        t["server_id"] == "@pimzino/agentic-tools-mcp" for t in target["tools"]
    ):
        return knowledge, []
    if target["version"] != "late":
        return knowledge, []
    rows = [
        r
        for r in feedback
        if r.get("server") == "capability_certificate" and r.get("stage") == "late"
    ]
    if len(rows) != 1:
        raise ValueError("Missing unique capability certificate")
    cert = rows[0]["result"]
    if hashlib.sha256(canonical(cert).encode()).hexdigest() != CERTIFICATE_SHA256:
        raise ValueError("Unreviewed capability certificate")
    changed = {r["tool_id"] for r in base["diff"]["changed"] + base["diff"]["added"]}
    by = {t["tool_id"]: t for t in knowledge["tools"]}
    native = {t["tool_id"]: t for t in target["tools"]}
    withdrawn = set()
    changes = []
    for row in cert["certificates"]:
        identity = row["tool_id"]
        if identity not in changed or identity not in by:
            raise ValueError("Withdrawal requires an actual changed capability")
        if hashlib.sha256(canonical(native[identity]).encode()).hexdigest() != row["record_sha256"]:
            raise ValueError("Unknown native record for withdrawal")
        if withdraw:
            withdrawn.add(identity)
            changes.append(
                {
                    "operation": "withdraw_failed_capability",
                    "tool_id": identity,
                    "before": deepcopy(by[identity]),
                    "evidence": CERTIFICATE_SHA256,
                }
            )
        else:
            by[identity]["usage_rules"].append(row["warning"])
            changes.append(
                {
                    "operation": "warn_failed_capability",
                    "tool_id": identity,
                    "after": row["warning"],
                    "evidence": CERTIFICATE_SHA256,
                }
            )
    for row in cert["reference_edits"]:
        identity = row["tool_id"]
        if identity not in by or by[identity]["description"] != row["before"]:
            raise ValueError("Unknown explicit recommendation for withdrawn capability")
        by[identity]["description"] = row["after"]
        changes.append(
            {
                "operation": "remove_dependent_recommendation",
                **deepcopy(row),
                "evidence": CERTIFICATE_SHA256,
            }
        )
    knowledge["tools"] = [t for t in knowledge["tools"] if t["tool_id"] not in withdrawn]
    return knowledge, changes

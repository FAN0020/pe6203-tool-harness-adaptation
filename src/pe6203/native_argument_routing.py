"""Reconcile only native-probe-verified MagicUI routing descriptions."""

import hashlib
from copy import deepcopy

from .native_argument_routing_spec import (
    ANNOTATIONS,
    FACTS,
    FINGERPRINT_FIELDS,
    SERVER,
    TRIGGERS,
)
from .selective import canonical, validate_adaptation


def expected_routing(base, target, feedback):
    """Keep SP unless the observed Late tool additions/changes are present."""
    knowledge = deepcopy(base["knowledge"])
    changes = {c["tool_id"]: c for c in base["diff"]["changed"] + base["diff"]["added"]}
    if target["version"] != "late" or not set(TRIGGERS).intersection(changes):
        return knowledge, []
    if not ANNOTATIONS.keys() <= changes.keys():
        raise ValueError("Unverified native argument routing bundle or missing alternative")
    observed = [
        row for row in feedback
        if isinstance(row, dict) and row.get("stage") == "late"
        and row.get("server") == SERVER
        and f"{SERVER}::{row.get('tool')}" in FACTS
    ]
    if (len(observed) != len(FACTS)
            or {f"{SERVER}::{row['tool']}" for row in observed} != FACTS.keys()
            or any(row.get("result") != FACTS[f"{SERVER}::{row['tool']}"] for row in observed)):
        raise ValueError("Missing verified native argument routing observations")
    tools = {t["tool_id"]: t for t in knowledge["tools"]}
    log = []
    for tool_id, annotation in ANNOTATIONS.items():
        tool = tools[tool_id]
        fingerprint = hashlib.sha256(canonical({
            field: tool[field] for field in FINGERPRINT_FIELDS
        }).encode()).hexdigest()
        if fingerprint != annotation["native_contract_sha256"]:
            raise ValueError("Unverified native argument routing contract: " + tool_id)
        before = tool["description"]
        tool["description"] = annotation["after"]
        log.append({
            "operation": "reconcile_native_argument_routing", "tool_id": tool_id,
            "path": "description", "before": before, "after": annotation["after"],
            "basis": [changes[tool_id]["change_id"]],
            "evidence": "frozen_native_argument_loss_and_category_probes",
        })
    return knowledge, log


def validate_routing(candidate, old, target, base, feedback):
    """Allow exactly the frozen description delta; retain all ordinary SP gates."""
    expected, log = expected_routing(base, target, feedback)
    if candidate != expected:
        return {"errors": ["Candidate differs from the native routing description allowlist"],
                "checks": {"annotation_count": len(log)}}
    restored = deepcopy(candidate)
    tools = {t["tool_id"]: t for t in restored["tools"]}
    for entry in log:
        tools[entry["tool_id"]]["description"] = entry["before"]
    result = validate_adaptation(restored, old, target, base["diff"])
    result["checks"]["annotation_count"] = len(log)
    return result

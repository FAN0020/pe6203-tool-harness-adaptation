"""Intern exact same-host parameter descriptions as one-hop declaration references.

This preserves recoverable documentation, not a proof that an LLM will resolve
the references. Structural schemas, tool availability and execution stay intact.
"""

from collections import defaultdict
from copy import deepcopy
from hashlib import sha256

from .selective import adapt_result, canonical


def digest(value):
    return sha256(canonical(value).encode()).hexdigest()


def compile_knowledge(old, target):
    from .runner import prepare_tools

    base = adapt_result(old, target)
    if base["knowledge"] is None:
        raise ValueError("Invalid base selective patch")
    knowledge = deepcopy(base["knowledge"])
    changed = {r["tool_id"] for r in base["diff"]["changed"] + base["diff"]["added"]}
    if not changed:
        return knowledge, []
    records = knowledge["tools"]
    model_tools, _ = prepare_tools(records, "selective_patch", "namespaced")
    names = {r["tool_id"]: t["function"]["name"] for r, t in zip(records, model_tools, strict=True)}
    groups = defaultdict(list)
    for record in records:
        schema = record["parameters"]
        for field, prop in schema.get("properties", {}).items():
            if (
                not isinstance(prop, dict)
                or not isinstance(prop.get("description"), str)
                or not prop["description"].strip()
            ):
                continue
            # Include the full property, presence requirement, name and host.
            # Equal strings on different contracts do not establish equivalence.
            key = (record["server_id"], field, canonical(prop), field in schema.get("required", []))
            groups[key].append((record, field, deepcopy(prop)))
    edits = []
    for group in groups.values():
        if len(group) < 2:
            continue
        # Prefer a wholly unchanged record, then the first in frozen tool order.
        anchors = [r for r in group if r[0]["tool_id"] not in changed] or group
        anchor, field, original = anchors[0]
        reference = f"Identical requirements to {names[anchor['tool_id']]}.{field} (declaration reference only)."
        if len(reference) >= len(original["description"]):
            continue
        for record, param, prop in group:
            if record["tool_id"] == anchor["tool_id"] or record["tool_id"] not in changed:
                continue
            record["parameters"]["properties"][param]["description"] = reference
            edits.append(
                {
                    "operation": "intern_exact_parameter_description",
                    "tool_id": record["tool_id"],
                    "parameter": param,
                    "before": prop["description"],
                    "after": reference,
                    "anchor_tool_id": anchor["tool_id"],
                    "anchor_function": names[anchor["tool_id"]],
                    "property_sha256": digest(prop),
                    "required": param in record["parameters"].get("required", []),
                }
            )
    if expand_references(knowledge, edits) != base["knowledge"]:
        raise ValueError("Reference expansion does not recover exact SP knowledge")
    return knowledge, edits


def expand_references(knowledge, edits):
    result = deepcopy(knowledge)
    by = {t["tool_id"]: t for t in result["tools"]}
    modified = {(e["tool_id"], e["parameter"]) for e in edits}
    if len(modified) != len(edits):
        raise ValueError("Duplicate edited field")
    for edit in edits:
        try:
            tool = by[edit["tool_id"]]
            anchor = by[edit["anchor_tool_id"]]
            field = edit["parameter"]
            prop = tool["parameters"]["properties"][field]
            witness = anchor["parameters"]["properties"][field]
        except KeyError as exc:
            raise ValueError("Missing reference target") from exc
        if (anchor["tool_id"], field) in modified:
            raise ValueError("References must have unmodified one-hop anchors")
        if (
            tool["server_id"] != anchor["server_id"]
            or digest(witness) != edit["property_sha256"]
            or witness["description"] != edit["before"]
        ):
            raise ValueError("Reference contract drift")
        if (field in tool["parameters"].get("required", [])) != edit["required"] or (
            field in anchor["parameters"].get("required", [])
        ) != edit["required"]:
            raise ValueError("Presence requirement differs")
        if prop["description"] != edit["after"]:
            raise ValueError("Reference field differs")
        prop["description"] = witness["description"]
        if prop != witness:
            raise ValueError("Structural property differs")
    return result

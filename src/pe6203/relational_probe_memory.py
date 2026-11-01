"""State-linked native evidence on a directly changed producer, without recipes.

LLM chooses probes, host binds receipt-verified IDs and records shared state.
The compiler adds observed transitions, never LLM-inferred general guarantees.
"""

import json
import re
from copy import deepcopy

from jsonschema import ValidationError, validators

from .active_contract_probing import PROJECT

ROOT_ID = PROJECT + "::create_project"
ALLOWED = {
    "create_project",
    "get_project",
    "create_task",
    "get_task",
    "update_task",
    "list_tasks",
    "review_project_status",
    "review_workspace_health",
    "get_next_task_recommendation",
}
IDENTITY_KEYS = {"id", "projectId", "parentId", "dependsOn"}


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)


def validate_sequence(data, payload):
    if data["server"] != PROJECT or ROOT_ID not in data["changed_ids"]:
        raise ValueError("Sequence requires the directly changed project producer")
    if not isinstance(payload, dict) or set(payload) != {"steps"}:
        raise ValueError("Expected steps only")
    steps = payload["steps"]
    if not isinstance(steps, list) or not 2 <= len(steps) <= 4:
        raise ValueError("Exactly two to four connected calls required")
    tools = {t["name"]: t for t in data["target"]["tools"]}
    available = {"$WORKSPACE"}
    for index, step in enumerate(steps, 1):
        if not isinstance(step, dict) or set(step) != {"id", "tool", "arguments", "question"}:
            raise ValueError("Invalid step fields")
        if step["id"] != f"P{index}" or step["tool"] not in ALLOWED or step["tool"] not in tools:
            raise ValueError("Invalid sequential ID or local tool alias")
        if index == 1 and step["tool"] != "create_project":
            raise ValueError("First call must test the changed producer")
        if not isinstance(step["question"], str) or not 1 <= len(step["question"]) <= 600:
            raise ValueError("Missing bounded operational question")
        args = step["arguments"]
        if not isinstance(args, dict) or len(json.dumps(args, allow_nan=False)) > 4096:
            raise ValueError("Invalid or oversized arguments")
        if args.get("workingDirectory") != "$WORKSPACE":
            raise ValueError("Workspace must use the isolated host binding")
        refs = {s for s in strings(args) if s.startswith("$")}
        if refs - available:
            raise ValueError("Unknown or forward reference")
        identity_refs = {
            s
            for key, value in args.items()
            if key in IDENTITY_KEYS
            for s in strings(value)
            if s in available - {"$WORKSPACE"}
        }
        if index > 1 and not identity_refs:
            raise ValueError("Every consumer must use an earlier exported entity ID")
        schema = tools[step["tool"]]["parameters"]
        try:
            validators.validator_for(schema)(schema).validate(args)
        except ValidationError as exc:
            raise ValueError("Native schema violation: " + exc.message) from exc
        if step["tool"] == "create_project":
            available.add(f"$P{index}.project_id")
        elif step["tool"] == "create_task":
            available.add(f"$P{index}.task_id")
    return deepcopy(steps)


def bind_arguments(value, bindings):
    if isinstance(value, str):
        if value.startswith("$") and value not in bindings:
            raise ValueError("Unbound native reference: " + value)
        return bindings.get(value, value)
    if isinstance(value, list):
        return [bind_arguments(item, bindings) for item in value]
    if isinstance(value, dict):
        return {key: bind_arguments(item, bindings) for key, item in value.items()}
    return value


def exported_ids(step_id, row):
    result = row.get("result", {})
    if result.get("isError") or row.get("native_exception"):
        return {}
    returned = json.dumps(result.get("content", []), ensure_ascii=False)
    out = {}
    for collection, suffix in [("projects", "project_id"), ("tasks", "task_id")]:
        before = {r["id"] for r in row["before_state"].get(collection, [])}
        new = [r for r in row["after_state"].get(collection, []) if r["id"] not in before]
        if len(new) == 1 and new[0]["id"] and new[0]["id"] in returned:
            out[f"${step_id}.{suffix}"] = new[0]["id"]
    return out


def clean(value):
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items() if k not in {"createdAt", "updatedAt"}}
    if isinstance(value, list):
        return [clean(v) for v in value]
    return value


def state_delta(before, after):
    out = {}
    for collection in ("projects", "tasks", "subtasks"):
        a = {r["id"]: clean(r) for r in before.get(collection, [])}
        b = {r["id"]: clean(r) for r in after.get(collection, [])}
        if len(a) != len(before.get(collection, [])) or len(b) != len(after.get(collection, [])):
            raise ValueError("Duplicate persisted identifiers")
        changes = {
            "added": [b[k] for k in b if k not in a],
            "removed": [a[k] for k in a if k not in b],
            "changed": [
                {"before": a[k], "after": b[k]} for k in sorted(a.keys() & b.keys()) if a[k] != b[k]
            ],
        }
        if any(changes.values()):
            out[collection] = changes
    return out


def observation_note(data, proposal, rows):
    steps = validate_sequence(data, proposal)
    if len(rows) != len(steps):
        raise ValueError("Every scheduled step needs a native observation")
    substitutions = {}
    for collection in ("projects", "tasks", "subtasks"):
        for index, record in enumerate(rows[0]["before_state"].get(collection, []), 1):
            substitutions[record["id"]] = f"$fixture.{collection}{index}"
    bound = {"$WORKSPACE": "$WORKSPACE"}
    observations = []
    for index, (step, row) in enumerate(zip(steps, rows, strict=True)):
        if row["id"] != step["id"] or row.get("not_executed"):
            raise ValueError("Unexecuted or mismatched step")
        if index and row["before_state"] != rows[index - 1]["after_state"]:
            raise ValueError("Broken session state continuity")
        # Verifies that every dependent reference was actually exportable.
        bind_arguments(step["arguments"], bound)
        exports = exported_ids(step["id"], row)
        bound.update(exports)
        substitutions.update({actual: token for token, actual in exports.items()})
        observations.append(
            {
                "step": step["id"],
                "tool": step["tool"],
                "arguments": step["arguments"],
                "returned": row.get("result"),
                "native_exception": row.get("native_exception"),
                "persisted_delta": state_delta(row["before_state"], row["after_state"]),
            }
        )
    evidence = {
        "kind": "same_session_native_observations",
        "initial_record_counts": {
            k: len(rows[0]["before_state"].get(k, [])) for k in ("projects", "tasks", "subtasks")
        },
        "observations": observations,
        "limits": "One synthetic state and sequence, not a guarantee for other inputs. Symbols denote receipt-verified created IDs. Native return and persisted change are distinct. Incidental timestamps and absolute workspace paths omitted. Initial unrelated records represented only by counts. This is evidence, not a task plan or a requirement to repeat calls.",
    }
    text = json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    for actual, token in sorted(substitutions.items(), key=lambda item: -len(item[0])):
        text = text.replace(actual, token)
    text = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", "<timestamp>", text)
    text = re.sub(r"\d{1,2}/\d{1,2}/\d{4},\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M", "<timestamp>", text)
    if len(text) > 24000:
        raise ValueError("Evidence exceeds frozen whole-sequence admission size; no truncation")
    return "Observed state-linked contract evidence: " + text


def compile_knowledge(base, target, feedback):
    result = deepcopy(base["knowledge"])
    changed = {r["tool_id"] for r in base["diff"]["changed"] + base["diff"]["added"]}
    if ROOT_ID not in changed:
        return result, []
    matches = [
        r for r in feedback if r.get("stage") == target["version"] and r.get("server") == PROJECT
    ]
    if len(matches) != 1:
        raise ValueError("Exactly one reviewed sequence required for the affected stage")
    cert = matches[0]["result"]
    if (
        cert.get("kind") != "relational_native_memory_v1"
        or cert.get("semantic_review") != "accepted"
    ):
        raise ValueError("Unreviewed or wrong certificate")
    data = cert["inventory"]
    actual = [t for t in target["tools"] if t["server_id"] == PROJECT]
    if (
        data["server"] != PROJECT
        or data["target"]["tools"] != actual
        or data["target"]["version"] != target["version"]
    ):
        raise ValueError("Frozen metadata does not match current host")
    note = observation_note(data, cert["proposal"], cert["observations"])
    record = next(t for t in result["tools"] if t["tool_id"] == ROOT_ID)
    before = deepcopy(record["usage_rules"])
    record["usage_rules"].append(note)
    return result, [
        {
            "tool_id": ROOT_ID,
            "field": "usage_rules",
            "before": before,
            "after": deepcopy(record["usage_rules"]),
            "reason": "reviewed same-session native transition evidence",
        }
    ]

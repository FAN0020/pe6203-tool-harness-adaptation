"""Bounded model-chosen native probes and direct changed-record adjudication.

This compiler establishes scope/provenance, not semantic truth. Native receipts
and a separately frozen source-based review must support any admitted update.
No benchmark question, answer or actor trajectory is an input.
"""

import json
from copy import deepcopy

from jsonschema import ValidationError, validators

from .selective import adapt_result

PROJECT = "@pimzino/agentic-tools-mcp"
ALLOWED = {
    "math-mcp": {"validate_syntax", "evaluate", "batch_evaluate"},
    PROJECT: {
        "create_project",
        "get_project",
        "list_projects",
        "list_tasks",
        "review_project_status",
        "review_workspace_health",
        "get_next_task_recommendation",
        "list_memories",
        "get_task",
        "create_task",
        "update_task",
    },
}


def inventory(old, target, server):
    if server not in ALLOWED:
        raise ValueError("Unsupported native probe host")
    base = adapt_result(old, target)
    roots = {r["tool_id"] for r in base["diff"]["changed"] + base["diff"]["added"]}
    records = [t for t in target["tools"] if t["server_id"] == server]
    changed = sorted(roots & {t["tool_id"] for t in records})
    claims = []
    for t in records:
        if t["tool_id"] not in changed:
            continue
        paths = [("description", t["description"])]
        paths.extend(
            (f"parameters.properties.{k}.description", v["description"])
            for k, v in t["parameters"].get("properties", {}).items()
            if isinstance(v.get("description"), str)
        )
        for path, text in paths:
            claims.append(
                {
                    "id": f"C{len(claims) + 1:03d}",
                    "tool_id": t["tool_id"],
                    "path": path,
                    "before": text,
                }
            )
    return {
        "server": server,
        "old": {
            **{k: deepcopy(old[k]) for k in ("schema_version", "benchmark_commit", "version")},
            "tools": [deepcopy(t) for t in old["tools"] if t["server_id"] == server],
        },
        "target": {
            **{k: deepcopy(target[k]) for k in ("schema_version", "benchmark_commit", "version")},
            "tools": deepcopy(records),
        },
        "changed_ids": changed,
        "claims": claims,
        "allowed_probe_tools": sorted(
            t["tool_id"] for t in records if t["name"] in ALLOWED[server]
        ),
    }


def validate_probes(data, payload):
    if not isinstance(payload, dict) or set(payload) != {"probes"}:
        raise ValueError("Expected probes only")
    rows = payload["probes"]
    if not isinstance(rows, list) or len(rows) > 4:
        raise ValueError("At most four native calls per job; empty means abstention")
    tools = {t["tool_id"]: t for t in data["target"]["tools"]}
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {
            "id",
            "basis",
            "tool_id",
            "arguments",
            "question",
        }:
            raise ValueError("Invalid probe fields")
        if row["id"] not in {"P1", "P2", "P3", "P4"} or row["id"] in seen:
            raise ValueError("Unknown or duplicate probe ID")
        seen.add(row["id"])
        if (
            row["basis"] not in data["changed_ids"]
            or row["tool_id"] not in data["allowed_probe_tools"]
        ):
            raise ValueError("Probe lacks changed root or allowed native route")
        if not isinstance(row["question"], str) or not 1 <= len(row["question"]) <= 600:
            raise ValueError("Missing bounded contract question")
        args = row["arguments"]
        if not isinstance(args, dict) or len(json.dumps(args, allow_nan=False)) > 4096:
            raise ValueError("Invalid or oversized native arguments")
        for key in ("workingDirectory", "workspace"):
            if key in args and args[key] != "$WORKSPACE":
                raise ValueError("Workspace must be the host-bound isolated placeholder")
        if data["server"] == "math-mcp":
            expressions = (
                args.get("expressions")
                if row["tool_id"].endswith("::batch_evaluate")
                else [args.get("expression")]
            )
            if (
                not isinstance(expressions, list)
                or not 1 <= len(expressions) <= 4
                or any(not isinstance(e, str) or len(e) > 128 for e in expressions)
            ):
                raise ValueError("One to four bounded expressions required")
        schema = tools[row["tool_id"]]["parameters"]
        try:
            validators.validator_for(schema)(schema).validate(args)
        except ValidationError as exc:
            raise ValueError("Native schema violation: " + exc.message) from exc
    return deepcopy(rows)


def compile_decisions(old, target, data, payload, evidence_ids):
    if data != inventory(old, target, data["server"]):
        raise ValueError("Inventory no longer matches frozen metadata")
    if not isinstance(payload, dict) or set(payload) != {"decisions"}:
        raise ValueError("Expected decisions only")
    rows = payload["decisions"]
    claims = {c["id"]: c for c in data["claims"]}
    if not isinstance(rows, list) or len(rows) != len(claims):
        raise ValueError("Exactly one decision per claim required")
    result = deepcopy(adapt_result(old, target)["knowledge"])
    tools = {t["tool_id"]: t for t in result["tools"]}
    edits = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"id", "action", "after", "evidence", "reason"}:
            raise ValueError("Invalid decision fields")
        cid = row["id"]
        if cid not in claims or cid in seen:
            raise ValueError("Unknown or duplicate claim ID")
        seen.add(cid)
        claim = claims[cid]
        if row["action"] not in {"retain", "replace", "unknown"}:
            raise ValueError("Unknown decision action")
        if not isinstance(row["reason"], str) or not row["reason"].strip():
            raise ValueError("Missing public justification")
        if not isinstance(row["evidence"], list) or any(
            e not in evidence_ids for e in row["evidence"]
        ):
            raise ValueError("Cites unavailable native evidence")
        if row["action"] != "replace":
            if row["after"] != claim["before"]:
                raise ValueError("Retain/unknown may not mutate a field")
            continue
        if (
            not row["evidence"]
            or not isinstance(row["after"], str)
            or not 1 <= len(row["after"]) <= 1800
            or row["after"] == claim["before"]
        ):
            raise ValueError("Replacement needs a bounded changed field and actual probe evidence")
        node = tools[claim["tool_id"]]
        for key in claim["path"].split(".")[:-1]:
            node = node[key]
        key = claim["path"].split(".")[-1]
        if node[key] != claim["before"]:
            raise ValueError("Stale field value")
        node[key] = row["after"]
        edits.append({**deepcopy(claim), **deepcopy(row)})
    return result, edits


def frozen_knowledge(old, target, feedback):
    """Apply already-reviewed field decisions to the full SP snapshot."""
    result = deepcopy(adapt_result(old, target)["knowledge"])
    changes = []
    tools = {t["tool_id"]: t for t in result["tools"]}
    for server in ALLOWED:
        data = inventory(old, target, server)
        if not data["changed_ids"]:
            continue
        matches = [
            r for r in feedback if r.get("stage") == target["version"] and r.get("server") == server
        ]
        if len(matches) != 1:
            raise ValueError(
                "Exactly one frozen reviewed proposal per affected host/stage required"
            )
        cert = matches[0]["result"]
        if (
            cert.get("kind") != "model_designed_native_probes_v1"
            or cert.get("semantic_review") != "accepted"
            or cert.get("inventory") != data
        ):
            raise ValueError("Unreviewed, stale or incorrect active-probe certificate")
        _, edits = compile_decisions(old, target, data, cert["payload"], set(cert["evidence_ids"]))
        for edit in edits:
            node = tools[edit["tool_id"]]
            for key in edit["path"].split(".")[:-1]:
                node = node[key]
            node[edit["path"].split(".")[-1]] = edit["after"]
            changes.append(edit)
    return result, changes

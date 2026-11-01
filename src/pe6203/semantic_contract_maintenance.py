"""Compile evidence-cited semantic edits without changing call contracts.

Structural admissibility is not semantic truth: a separate frozen review must
accept the model's evidence entailment before any benchmark execution.
"""

import hashlib
import re
from copy import deepcopy

from .selective import adapt_result, canonical


def math_fingerprint(catalog):
    return hashlib.sha256(
        canonical([t for t in catalog["tools"] if t["server_id"] == "math-mcp"]).encode()
    ).hexdigest()


def compile_patch(old, target, proposal, evidence_ids, closure):
    base = adapt_result(old, target)
    knowledge = deepcopy(base["knowledge"])
    tools = {t["tool_id"]: t for t in knowledge["tools"]}
    allowed = {k for k, t in tools.items() if t["server_id"] == "math-mcp"}
    changed = {r["tool_id"] for r in base["diff"]["changed"] + base["diff"]["added"]} & allowed
    if not isinstance(proposal, dict) or set(proposal) != {"edges", "edits"}:
        raise ValueError("Expected edges and edits only")
    if not isinstance(proposal["edges"], list) or not isinstance(proposal["edits"], list):
        raise ValueError("Invalid proposal lists")

    def citations(row):
        ev = row.get("evidence")
        if (
            not isinstance(ev, list)
            or not ev
            or any(not isinstance(e, str) or e not in evidence_ids for e in ev)
            or not isinstance(row.get("reason"), str)
            or not row["reason"].strip()
        ):
            raise ValueError("Missing supplied evidence or reason")

    edges = set()
    for edge in proposal["edges"]:
        if not isinstance(edge, dict) or set(edge) != {"source", "target", "evidence", "reason"}:
            raise ValueError("Invalid edge fields")
        if (
            edge["source"] not in allowed
            or edge["target"] not in allowed
            or edge["source"] == edge["target"]
        ):
            raise ValueError("Unknown or reflexive edge")
        citations(edge)
        pair = (edge["source"], edge["target"])
        if pair in edges:
            raise ValueError("Duplicate edge")
        edges.add(pair)

    def reachable(start):
        seen = {start}
        while True:
            more = {b for a, b in edges if a in seen} - seen
            if not more:
                return seen
            seen |= more

    reachable_all = set().union(*(reachable(x) for x in changed)) if changed else set()
    if any(a not in reachable_all for a, b in edges):
        raise ValueError("Edge lacks changed-tool root")
    seen = set()
    log = []
    for edit in proposal["edits"]:
        if not isinstance(edit, dict) or set(edit) != {
            "tool_id",
            "path",
            "before",
            "after",
            "basis",
            "evidence",
            "reason",
        }:
            raise ValueError("Invalid edit fields")
        identity, path, basis = edit["tool_id"], edit["path"], edit["basis"]
        if identity not in allowed or basis not in changed or identity not in reachable(basis):
            raise ValueError("Edit lacks supported impact path")
        if not isinstance(path, str) or not (
            path == "description"
            or re.fullmatch(r"parameters\.properties\.[A-Za-z0-9_]+\.description", path)
        ):
            raise ValueError("Structural or unsupported field edit")
        if (identity, path) in seen:
            raise ValueError("Duplicate edit")
        seen.add((identity, path))
        citations(edit)
        if not isinstance(edit["after"], str) or not 1 <= len(edit["after"]) <= 1800:
            raise ValueError("Invalid replacement description")
        node = tools[identity]
        try:
            for key in path.split(".")[:-1]:
                node = node[key]
            if node[path.split(".")[-1]] != edit["before"]:
                raise ValueError("Stale before value")
        except (KeyError, TypeError) as exc:
            raise ValueError("Missing annotation path") from exc
        if closure or identity in changed:
            node[path.split(".")[-1]] = edit["after"]
            log.append(deepcopy(edit))
    return knowledge, log


def frozen_patch(old, target, feedback, closure):
    base = adapt_result(old, target)
    if base["status"] == "no_change" or not any(
        t["server_id"] == "math-mcp" for t in target["tools"]
    ):
        return base["knowledge"], []
    rows = [
        r for r in feedback if r.get("stage") == target["version"] and r.get("server") == "math-mcp"
    ]
    if len(rows) != 1:
        raise ValueError("Need one frozen semantic proposal")
    data = rows[0]["result"]
    if (
        data["kind"] != "semantic_contract_maintenance_v1"
        or data["target_sha256"] != math_fingerprint(target)
        or data["old_sha256"] != math_fingerprint(old)
    ):
        raise ValueError("Frozen proposal catalog mismatch")
    return compile_patch(old, target, data["proposal"], set(data["evidence_ids"]), closure)

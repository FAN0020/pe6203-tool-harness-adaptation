"""Program-first V5 scope selection and compact, evidence-linked model views.

The screen is a semantic candidate proposal, not a proof of non-impact. Exact
metadata stays authoritative; selected records receive one detailed review each.
No text is truncated to make a request fit a budget.
"""

from copy import deepcopy

from .rules_v5 import decisions, patches
from .selective import METADATA_DIFF_FIELDS, build_reference_index, canonical_equal


def field_delta(old, new, path=""):
    """Exact changed JSON leaves; omit equal subtrees rather than resending schemas."""
    if canonical_equal(old, new):
        return []
    if isinstance(old, dict) and isinstance(new, dict):
        result = []
        for key in sorted(set(old) | set(new)):
            pointer = path + "/" + key.replace("~", "~0").replace("/", "~1")
            if key not in old or key not in new:
                side, value = ("new", new[key]) if key in new else ("old", old[key])
                result.append(
                    {
                        "path": pointer,
                        "operation": "add" if side == "new" else "remove",
                        side: deepcopy(value),
                    }
                )
            else:
                result.extend(field_delta(old[key], new[key], pointer))
        return result
    return [
        {"path": path or "/", "operation": "replace", "old": deepcopy(old), "new": deepcopy(new)}
    ]


def program_scope(base, old, changes):
    records = {t["tool_id"]: t for t in base["knowledge"]["tools"]}
    references = build_reference_index(old)
    basis = {}
    completed = set()
    for key, change in changes.items():
        root = change["tool_id"]
        if root in records:
            if records[root].get("usage_rules") or change.get("kind") == "independent_evidence":
                basis.setdefault(root, set()).add(key)
            else:
                completed.add(root)
        # A description change can invalidate a referencing rule as well as a
        # structural change. Do not restrict this lookup to schema/routing diffs.
        for host in references.get(root, []):
            if host in records and records[host].get("usage_rules"):
                basis.setdefault(host, set()).add(key)
    completed -= basis.keys()
    eligible = set(records) - set(basis) - completed
    return {
        "program_completed_tool_ids": sorted(completed),
        "program_semantic_tool_ids": sorted(basis),
        "program_basis": {k: sorted(v) for k, v in basis.items()},
        "screen_eligible_tool_ids": sorted(eligible),
        "limitation": "Program completion certifies metadata synchronization only, not behavioral truth.",
    }


def change_views(changes):
    result = []
    for key, row in changes.items():
        view = {"change_id": key, "tool_id": row["tool_id"]}
        if row.get("kind") == "independent_evidence":
            view.update(kind=row["kind"], evidence_id=row["evidence_id"])
        else:
            old, new = row.get("old") or {}, row.get("new") or {}
            view["operation"] = "change" if old and new else "add" if new else "remove"
            view["fields"] = field_delta(
                {k: v for k, v in old.items() if k in METADATA_DIFF_FIELDS},
                {k: v for k, v in new.items() if k in METADATA_DIFF_FIELDS},
            )
        result.append(view)
    return result


def screen_payload(records, plan, changes, sources):
    # Description + stored rules exactly once per eligible record. No full
    # schema, complete global knowledge index, or three copies of each record.
    directory = [
        {
            "tool_id": t["tool_id"],
            "description": t["description"],
            "usage_rules": deepcopy(t.get("usage_rules", [])),
        }
        for t in records
        if t["tool_id"] in plan["screen_eligible_tool_ids"]
    ]
    return {
        "phase": "scope_screen",
        "changes": change_views(changes),
        "independent_evidence": {
            k: deepcopy(v) for k, v in sources.items() if v["kind"] != "catalog"
        },
        "program_completed_tool_ids": plan["program_completed_tool_ids"],
        "program_semantic_tool_ids": plan["program_semantic_tool_ids"],
        "program_context": [
            {
                "tool_id": t["tool_id"],
                "description": t["description"],
                "usage_rules": deepcopy(t.get("usage_rules", [])),
            }
            for t in records
            if t["tool_id"] in plan["program_semantic_tool_ids"]
        ],
        "directory": directory,
    }


def screen_candidates(payload, eligible, changes):
    if not isinstance(payload, dict) or set(payload) != {"screened_tool_ids", "candidates"}:
        raise ValueError("Expected scope-screen coverage and sparse candidates")
    covered = payload["screened_tool_ids"]
    if (
        not isinstance(covered, list)
        or any(type(i) is not str for i in covered)
        or len(set(covered)) != len(covered)
        or set(covered) != set(eligible)
    ):
        raise ValueError("Incomplete or duplicate lightweight screen coverage")
    if not isinstance(payload["candidates"], list):
        raise ValueError("Scope candidates must be a list")
    seen = set()
    for row in payload["candidates"]:
        if not isinstance(row, dict) or set(row) != {
            "tool_id",
            "classification",
            "basis",
            "reason",
        }:
            raise ValueError("Invalid scope candidate fields")
        identity = row["tool_id"]
        if type(identity) is not str or identity not in eligible or identity in seen:
            raise ValueError("Unknown, duplicate or already program-classified scope candidate")
        seen.add(identity)
        if row["classification"] not in {"potential_impact", "uncertain"}:
            raise ValueError("Screen proposes only potential impact or uncertainty")
        if (
            not isinstance(row["basis"], list)
            or not row["basis"]
            or any(type(k) is not str or k not in changes for k in row["basis"])
        ):
            raise ValueError("Scope candidate requires actual change/evidence-event IDs")
        if not isinstance(row["reason"], str) or not 0 < len(row["reason"].strip()) <= 1200:
            raise ValueError("Scope candidate needs a bounded reason")
    return deepcopy(payload["candidates"])


def detail_payload(records, basis, changes, sources):
    selected = {t["tool_id"] for t in records}
    keys = {key for identity in selected for key in basis[identity]}
    relevant = {k: v for k, v in changes.items() if k in keys}
    owners = selected | {c["tool_id"] for c in relevant.values()}
    catalog_fields = {
        (s["tool_id"], s["field"], s["side"]): s["value"]
        for s in sources.values()
        if s["kind"] == "catalog"
    }
    registry = {}
    for key, source in sources.items():
        if source["tool_id"] not in owners:
            continue
        if source["kind"] != "catalog":
            registry[key] = deepcopy(source)
        elif source["field"] == "description":
            if source["side"] == "old" and canonical_equal(
                source["value"], catalog_fields.get((source["tool_id"], "description", "target"))
            ):
                continue
            registry[key] = {
                k: deepcopy(source[k]) for k in ("kind", "side", "tool_id", "field", "value")
            }
        elif source["field"] == "usage_rules" and source["side"] == "old":
            # The exact post-program rule list is supplied once in records.
            registry[key] = {k: source[k] for k in ("kind", "side", "tool_id", "field")}
            registry[key]["view"] = (
                "rules are in the local post-program record; raw source retained in audit"
            )
        elif source["field"] in {"parameters", "output_schema"}:
            identity, field = source["tool_id"], source["field"]
            old_value = catalog_fields.get((identity, field, "old"))
            new_value = catalog_fields.get((identity, field, "target"))
            delta = field_delta(old_value, new_value)
            if delta:
                registry[key] = {k: source[k] for k in ("kind", "side", "tool_id", "field")}
                registry[key].update(
                    view="exact old-to-target JSON delta; not full schema", delta=delta
                )
    return {
        "phase": "local_semantic_review",
        "changes": change_views(relevant),
        "evidence_registry": registry,
        "records": [
            {
                "tool_id": t["tool_id"],
                "usage_rules": deepcopy(t.get("usage_rules", [])),
                "basis": basis[t["tool_id"]],
            }
            for t in records
        ],
    }


def review_edits(payload, ids, changes, sources, records):
    """One local decision, and any proposed patch, validated in the same response."""
    if (
        not isinstance(payload, dict)
        or set(payload) != {"decisions"}
        or not isinstance(payload["decisions"], list)
    ):
        raise ValueError("Expected exactly local decisions")
    plain, edits = [], []
    common = {"tool_id", "action", "reason", "basis", "evidence_ids"}
    for row in payload["decisions"]:
        if not isinstance(row, dict):
            raise ValueError("Invalid local decision")
        expected = common | (
            {"retain_rule_indices", "rules"} if row.get("action") == "update" else set()
        )
        if set(row) != expected:
            raise ValueError("Only update decisions may contain scoped rule operations")
        plain.append({k: deepcopy(row[k]) for k in common})
        if row.get("action") == "update":
            edits.append({k: deepcopy(v) for k, v in row.items() if k != "action"})
    decisions({"decisions": plain}, ids, changes, sources)
    proposed = patches({"patches": edits}, {r["tool_id"] for r in edits}, changes, sources, records)
    return plain, proposed

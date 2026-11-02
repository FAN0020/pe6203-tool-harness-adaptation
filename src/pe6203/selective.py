"""Historical deterministic V1 Selective Patch (owner group C).

Main preserves this deterministic core as its compatible default.
Hybrid V2/V3/V5/V6 are available through explicit selective-mode selection.

Updates only the tool-knowledge records affected by a persistent environment
change, then hands the resulting full snapshot to the shared ``ChatModel``
runner. The pipeline is, in order:

1. ``diff_catalogs``        deterministic metadata diff (add / remove / field change)
2. ``build_reference_index`` explicit one-hop references between knowledge rules
3. ``locate_impact``        expand the affected set through those references
4. selected-record rewrite  (structured fields from target metadata, never invented)
5. schema + routing + unchanged-record validation

The optional LLM updater for *semantic* usage-rule rewriting is strictly gated:
it runs only when ``context["allow_llm_update"]`` is true AND both
``UPDATER_API_KEY`` / ``UPDATER_BASE_URL`` are present AND the budget permits.
Every artifact committed by this repository uses the deterministic default
(``formal_llm_rewrite=False``); rules that would need semantic rewriting are
recorded as unresolved instead of being invented.

Structured metadata fields (name, parameters, description, output_schema,
routing) are authoritative in the target environment. ``usage_rules`` is our own
knowledge layer: the target catalog does not provide rules, so it is never
overwritten from an empty target; it is preserved, dropped only when it keeps a
dangling reference to a removed tool (recorded as unresolved), or passed to the
optional LLM updater.
"""

import hashlib
import json
import os
import re
from copy import deepcopy
from pathlib import Path
from time import perf_counter

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from .benchmark import read_json, write_json

# Fields where the target environment's metadata is authoritative.
METADATA_DIFF_FIELDS = ("name", "parameters", "description", "output_schema", "routing")
# Fields whose change invalidates cross-tool knowledge that depends on them.
STRUCTURAL_FIELDS = ("name", "parameters", "output_schema", "routing")

DEFAULT_BUDGET = {
    "max_llm_calls": 2,  # one initial patch + one corrective revision, per 5.4
    "max_llm_attempts_per_call": 2,
    "max_probe_calls": 3,
    "max_seconds": 120.0,
}

DEFAULT_UPDATER = {
    "model": "deepseek/deepseek-v4.1-flash-1017",
    "base_url_env": "UPDATER_BASE_URL",
    "api_key_env": "UPDATER_API_KEY",
    "temperature": 0.0,
    "max_completion_tokens": 4096,
}


def canonical(value):
    """Stable JSON text: object key order ignored, array order and text preserved."""
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    )


def canonical_equal(left, right):
    return canonical(left) == canonical(right)


def _check_schema(schema, field, tool_id):
    if field == "output_schema" and schema is None:
        return
    if not isinstance(schema, dict):
        raise ValueError(f"Invalid {field}: {tool_id}")
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise ValueError(f"Invalid {field}: {tool_id}: {exc.message}") from exc


def build_knowledge(metadata):
    """Validate and deep-copy a complete single-stage ToolRecord envelope.

    Mirrors ``baselines.build_knowledge`` so updaters and baselines accept the
    same input envelopes. The *output* of a selective patch may mix record
    versions (unchanged entries keep their source stage), so it is validated by
    :func:`validate_adaptation` instead.
    """
    if not isinstance(metadata, dict):
        raise ValueError("Metadata must be a dictionary")
    if metadata.get("schema_version") != "1.0" or not metadata.get("benchmark_commit"):
        raise ValueError("Metadata requires schema_version=1.0 and benchmark_commit")
    stage = metadata.get("version")
    if stage not in ("early", "middle", "late"):
        raise ValueError("Metadata requires a valid stage")
    tools = metadata.get("tools")
    if not isinstance(tools, list) or not tools:
        raise ValueError("Metadata must contain a nonempty tools list")
    seen = set()
    for tool in tools:
        if not isinstance(tool, dict):
            raise ValueError("Each tool must be a dictionary")
        for field in ("name", "server_id", "tool_id"):
            if not isinstance(tool.get(field), str) or not tool[field].strip():
                raise ValueError(f"Each tool requires a nonempty {field}")
        identity = tool["server_id"] + "::" + tool["name"]
        if tool["tool_id"] != identity or identity in seen:
            raise ValueError(f"Invalid or duplicate tool_id: {tool['tool_id']}")
        seen.add(identity)
        if tool.get("version") != stage:
            raise ValueError("Record version must match the metadata stage")
        if tool.get("routing") != {"server_id": tool["server_id"], "tool_name": tool["name"]}:
            raise ValueError(f"Routing does not match tool identity: {identity}")
        if not isinstance(tool.get("description"), str):
            raise ValueError(f"Invalid description: {identity}")
        rules = tool.get("usage_rules")
        if not isinstance(rules, list) or any(not isinstance(r, str) for r in rules):
            raise ValueError(f"Invalid usage_rules: {identity}")
        _check_schema(tool.get("parameters"), "parameters", identity)
        _check_schema(tool.get("output_schema"), "output_schema", identity)
    json.dumps(metadata, allow_nan=False)
    return deepcopy(metadata)


def diff_catalogs(old_knowledge, new_metadata):
    """Return a structured diff between two complete single-stage envelopes.

    Identity is ``server_id::name`` (tool_id). A rename with no explicit stable
    evidence is recorded as ``removed`` + ``added``, never guessed as the same
    tool. ``usage_rules`` is deliberately excluded: the target environment does
    not provide rules, so an empty target must not erase our knowledge layer.
    """
    old_tools = {t["tool_id"]: t for t in old_knowledge["tools"]}
    new_tools = {t["tool_id"]: t for t in new_metadata["tools"]}
    counter = {"r": 0, "a": 0, "c": 0}
    removed, added, changed, unchanged = [], [], [], []
    for tool_id in sorted(set(old_tools) - set(new_tools)):
        counter["r"] += 1
        removed.append(
            {
                "change_id": f"r{counter['r']}",
                "tool_id": tool_id,
                "old": deepcopy(old_tools[tool_id]),
                "rename_evidence": None,
            }
        )
    for tool_id in sorted(set(new_tools) - set(old_tools)):
        counter["a"] += 1
        added.append(
            {
                "change_id": f"a{counter['a']}",
                "tool_id": tool_id,
                "new": deepcopy(new_tools[tool_id]),
            }
        )
    for tool_id in sorted(set(old_tools) & set(new_tools)):
        old_record, new_record = old_tools[tool_id], new_tools[tool_id]
        changed_fields = [
            field
            for field in METADATA_DIFF_FIELDS
            if not canonical_equal(old_record.get(field), new_record.get(field))
        ]
        if changed_fields:
            counter["c"] += 1
            changed.append(
                {
                    "change_id": f"c{counter['c']}",
                    "tool_id": tool_id,
                    "changed_fields": changed_fields,
                    "old": deepcopy(old_record),
                    "new": deepcopy(new_record),
                }
            )
        else:
            unchanged.append(tool_id)
    return {
        "schema_version": "1.0",
        "old_commit": old_knowledge["benchmark_commit"],
        "new_commit": new_metadata["benchmark_commit"],
        "old_version": old_knowledge["version"],
        "new_version": new_metadata["version"],
        "old_tool_count": len(old_tools),
        "new_tool_count": len(new_tools),
        "removed": removed,
        "added": added,
        "changed": changed,
        "unchanged_tool_ids": unchanged,
        "unchanged_count": len(unchanged),
    }


def _build_matchers(knowledge):
    matchers = []
    for tool in knowledge["tools"]:
        name = tool["name"]
        matchers.append(
            (
                tool["tool_id"],
                name,
                re.compile(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])"),
                re.compile(re.escape(tool["tool_id"])),
            )
        )
    return matchers


def _rule_references(rule, matchers):
    hits = set()
    for tool_id, _name, name_pattern, id_pattern in matchers:
        if id_pattern.search(rule) or name_pattern.search(rule):
            hits.add(tool_id)
    return hits


def build_reference_index(knowledge):
    """Map referenced tool_id -> host tool_ids whose usage rules mention it.

    This is the simple v1 explicit reference index (one hop, substring /
    word-boundary match over the natural-language ``usage_rules``). It is a
    documented heuristic, not a semantic dependency graph.
    """
    matchers = _build_matchers(knowledge)
    index = {}
    for tool in knowledge["tools"]:
        for rule in tool.get("usage_rules") or []:
            for ref in _rule_references(rule, matchers):
                if ref != tool["tool_id"]:
                    index.setdefault(ref, set()).add(tool["tool_id"])
    return {ref: sorted(hosts) for ref, hosts in index.items()}


def locate_impact(diff, old_knowledge, expand_dependencies=True):
    """Return (impacted_tool_ids, edges) where edges maps host -> changed refs."""
    changed_ids = {c["tool_id"] for c in diff["changed"]}
    removed_ids = {c["tool_id"] for c in diff["removed"]}
    added_ids = {c["tool_id"] for c in diff["added"]}
    impacted = set(changed_ids) | set(removed_ids) | set(added_ids)
    edges = {}
    if expand_dependencies:
        index = build_reference_index(old_knowledge)
        triggers = removed_ids | {
            c["tool_id"]
            for c in diff["changed"]
            if set(c["changed_fields"]) & set(STRUCTURAL_FIELDS)
        }
        for ref_id in sorted(triggers):
            for host in index.get(ref_id, []):
                impacted.add(host)
                edges.setdefault(host, set()).add(ref_id)
    return impacted, {host: sorted(refs) for host, refs in edges.items()}


def _resolve_context(context):
    context = context or {}
    budget = {**DEFAULT_BUDGET, **(context.get("budget") or {})}
    updater = {**DEFAULT_UPDATER, **(context.get("updater_config") or {})}
    return budget, updater, bool(context.get("allow_llm_update"))


def _rewrite_rules_with_llm(requests, updater, budget):
    """Rewrite semantic usage rules with the shared updater model.

    Returns ``({tool_id: [rules]}, usage)``. Gated by the caller; raises
    ``ValueError`` when credentials or budget are unavailable. The model may
    only rewrite the listed rules from the supplied evidence; structured fields
    are never in scope.
    """
    api_key = os.environ.get(updater["api_key_env"])
    base_url = os.environ.get(updater["base_url_env"])
    if not api_key or not base_url:
        raise ValueError(f"Configure {updater['api_key_env']} and {updater['base_url_env']}")
    from openai import OpenAI  # noqa: PLC0415

    client = OpenAI(api_key=api_key, base_url=base_url)
    system = (
        "You update only the usage_rules of the tool-knowledge records listed. "
        'Return a single JSON object: {"rules": [{"tool_id": "...", "usage_rules": [...]}]}. '
        "Do not invent tool names, schemas or routing. Use only the evidence provided "
        "and keep unrelated entries unchanged. If evidence is insufficient, return the "
        'rule unchanged and set an explicit "unresolved": true flag on that item.'
    )
    user = json.dumps({"rewrite_requests": requests, "budget": budget}, ensure_ascii=False)
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for _ in range(max(1, int(budget.get("max_llm_calls", 1)))):
        response = client.chat.completions.create(
            model=updater["model"],
            temperature=updater["temperature"],
            max_completion_tokens=updater["max_completion_tokens"],
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        if response.usage:
            for key in usage:
                usage[key] += getattr(response.usage, key, 0) or 0
        raw = (response.choices[0].message.content or "").strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
        try:
            parsed = json.loads(raw)["rules"]
            return {item["tool_id"]: item["usage_rules"] for item in parsed}, usage
        except (KeyError, TypeError, ValueError):
            continue
    raise ValueError("LLM updater failed to return valid structured rule edits")


def _apply_patch(old_knowledge, target, diff, impacted, edges, context):
    budget, updater, allow_llm = _resolve_context(context)
    new_tools = {t["tool_id"]: t for t in target["tools"]}
    removed_ids = {c["tool_id"] for c in diff["removed"]}
    changed_ids = {c["tool_id"] for c in diff["changed"]}
    changed_by_id = {c["tool_id"]: c for c in diff["changed"]}
    matchers = _build_matchers(old_knowledge)

    changes, unresolved = [], []
    semantic_requests = {}
    records = []
    for old_record in old_knowledge["tools"]:
        tool_id = old_record["tool_id"]
        basis = []
        if tool_id in removed_ids:
            changes.append(
                {
                    "operation": "remove",
                    "tool_id": tool_id,
                    "basis": [c["change_id"] for c in diff["removed"] if c["tool_id"] == tool_id],
                    "reason": "tool absent from target environment",
                }
            )
            continue
        if tool_id in changed_ids:
            record = deepcopy(new_tools[tool_id])
            basis = [changed_by_id[tool_id]["change_id"]]
        else:
            record = deepcopy(old_record)

        rules = list(old_record.get("usage_rules") or [])
        if rules:
            kept, dangling = [], []
            for rule in rules:
                refs = _rule_references(rule, matchers)
                if refs & removed_ids:
                    dangling.append((rule, sorted(refs & removed_ids)))
                else:
                    kept.append(rule)
            for rule, refs in dangling:
                unresolved.append(
                    {
                        "kind": "dropped_dangling_rule",
                        "tool_id": tool_id,
                        "reason": "rule references a removed tool; no LLM rewrite available",
                        "removed_rule": rule,
                        "dangling_refs": refs,
                    }
                )
                changes.append(
                    {
                        "operation": "remove_rule",
                        "tool_id": tool_id,
                        "removed_rule": rule,
                        "basis": [c["change_id"] for c in diff["removed"] if c["tool_id"] in refs],
                        "reason": "dropped dangling reference to a removed tool",
                    }
                )
            if kept and (tool_id in changed_ids or tool_id in impacted):
                if allow_llm:
                    semantic_requests[tool_id] = {
                        "tool_id": tool_id,
                        "current_rules": kept,
                        "evidence": {
                            "changed_fields": (
                                changed_by_id[tool_id]["changed_fields"]
                                if tool_id in changed_ids
                                else None
                            ),
                            "referenced_changed_tools": edges.get(tool_id, []),
                        },
                    }
                else:
                    for rule in kept:
                        unresolved.append(
                            {
                                "kind": "needs_semantic_rewrite",
                                "tool_id": tool_id,
                                "rule": rule,
                                "reason": "rule may depend on a changed tool; deterministic fallback kept it",
                                "basis": (
                                    basis if tool_id in changed_ids else edges.get(tool_id, [])
                                ),
                            }
                        )
            rules = kept
            record["usage_rules"] = rules
        if tool_id in changed_ids:
            changes.append(
                {
                    "operation": "replace",
                    "tool_id": tool_id,
                    "fields": changed_by_id[tool_id]["changed_fields"],
                    "new": deepcopy(record),
                    "basis": basis,
                    "reason": "tool metadata changed in target environment",
                }
            )
        records.append(record)

    llm_used = False
    if semantic_requests:
        try:
            rewritten, usage = _rewrite_rules_with_llm(semantic_requests, updater, budget)
            for record in records:
                if record["tool_id"] in rewritten:
                    record["usage_rules"] = rewritten[record["tool_id"]]
            llm_used = True
            changes.append(
                {"operation": "rewrite_rules", "tool_ids": sorted(rewritten), "usage": usage}
            )
        except ValueError as exc:
            unresolved.append(
                {
                    "kind": "llm_rewrite_failed",
                    "tool_id": sorted(semantic_requests),
                    "reason": f"{type(exc).__name__}: {exc}",
                }
            )

    for item in diff["added"]:
        records.append(deepcopy(item["new"]))
        changes.append(
            {
                "operation": "add",
                "tool_id": item["tool_id"],
                "new": deepcopy(item["new"]),
                "basis": [item["change_id"]],
                "reason": "new tool present in target environment",
            }
        )

    knowledge = {
        "schema_version": target["schema_version"],
        "benchmark_commit": target["benchmark_commit"],
        "version": target["version"],
        "tools": records,
    }
    return knowledge, changes, unresolved, llm_used


def _dangling_references(knowledge, removed):
    """True if any rule still references a removed tool id or name."""
    if not removed:
        return False
    id_patterns = [re.compile(re.escape(item["tool_id"])) for item in removed]
    name_patterns = [
        re.compile(rf"(?<![A-Za-z0-9_]){re.escape(item['old']['name'])}(?![A-Za-z0-9_])")
        for item in removed
    ]
    for tool in knowledge["tools"]:
        for rule in tool.get("usage_rules") or []:
            if any(pattern.search(rule) for pattern in id_patterns) or any(
                pattern.search(rule) for pattern in name_patterns
            ):
                return True
    return False


def validate_adaptation(knowledge, old_knowledge, target, diff, rule_modified_ids=None):
    """Structural validation of a candidate selective snapshot.

    Checks envelope identity, per-record schema/routing, unchanged records being
    canonical-equal to the source (unless only their knowledge-layer rules were
    modified), changed/added records matching the target environment for
    authoritative fields, no dangling rules, and a fixed server set. Does not
    use task questions, answers, scores or mutation labels.
    """
    rule_modified_ids = rule_modified_ids or set()
    changed_ids = {c["tool_id"] for c in diff["changed"]} | {c["tool_id"] for c in diff["added"]}
    errors = []
    old_tools = {t["tool_id"]: t for t in old_knowledge["tools"]}
    new_tools = {t["tool_id"]: t for t in target["tools"]}
    if knowledge["benchmark_commit"] != target["benchmark_commit"]:
        errors.append("Benchmark commit mismatch in candidate snapshot")
    if knowledge["version"] != target["version"]:
        errors.append("Envelope version mismatch in candidate snapshot")
    if {t["server_id"] for t in knowledge["tools"]} != {t["server_id"] for t in target["tools"]}:
        errors.append("Candidate snapshot server set differs from target environment")
    seen_ids = set()
    for tool in knowledge["tools"]:
        tool_id = tool.get("tool_id")
        if not isinstance(tool_id, str) or tool_id in seen_ids:
            errors.append(f"Invalid or duplicate tool_id: {tool_id}")
            continue
        seen_ids.add(tool_id)
        if tool.get("routing") != {"server_id": tool["server_id"], "tool_name": tool["name"]}:
            errors.append(f"Routing does not match tool identity: {tool_id}")
        if tool.get("tool_id") != tool["server_id"] + "::" + tool["name"]:
            errors.append(f"tool_id does not match server_id::name: {tool_id}")
        try:
            _check_schema(tool.get("parameters"), "parameters", tool_id)
            _check_schema(tool.get("output_schema"), "output_schema", tool_id)
        except ValueError as exc:
            errors.append(str(exc))
        if tool_id in changed_ids:
            reference = new_tools.get(tool_id)
            if reference is None:
                errors.append(f"Patched record missing from target: {tool_id}")
            else:
                for field in METADATA_DIFF_FIELDS:
                    if not canonical_equal(tool.get(field), reference.get(field)):
                        errors.append(f"Changed record not grounded in target: {tool_id}.{field}")
        else:
            # Metadata-unchanged record: authoritative fields must still match old.
            for field in METADATA_DIFF_FIELDS:
                if not canonical_equal(tool.get(field), old_tools[tool_id].get(field)):
                    errors.append(f"Untouched metadata field changed: {tool_id}.{field}")
            if tool_id not in rule_modified_ids and not canonical_equal(tool, old_tools[tool_id]):
                errors.append(f"Unchanged record was modified: {tool_id}")
    if seen_ids != set(new_tools):
        errors.append("Candidate tool IDs must exactly cover the target catalog")
    if _dangling_references(knowledge, diff["removed"]):
        errors.append("Candidate snapshot contains dangling references to removed tools")
    checks = {"records": len(knowledge["tools"]), "unchanged": len(diff["unchanged_tool_ids"])}
    return {"errors": errors, "checks": checks}


def adapt_result(old_knowledge, new_metadata, context=None):
    """Return the full adaptation result dict (see ``_impl_result`` fields).

    Public so tests and teammates can inspect the diff, impacted set,
    unresolved items and validation alongside the tuple returned by
    :func:`adapt`.
    """
    if (context or {}).get("allow_llm_update"):
        raise ValueError(
            "Only deterministic Selective Patch is validated; optional LLM rule rewriting is not enabled"
        )
    started = perf_counter()
    old = build_knowledge(old_knowledge)
    target = build_knowledge(new_metadata)
    if old["version"] != "early":
        raise ValueError("Selective Patch must start from Early knowledge")
    if target["benchmark_commit"] != old["benchmark_commit"]:
        raise ValueError("Benchmark commit mismatch")
    if {t["server_id"] for t in target["tools"]} != {t["server_id"] for t in old["tools"]}:
        raise ValueError("Metadata must cover the same fixed server set")

    cost = {
        "method": "deterministic_diff_selective_patch",
        "calls": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "usd": 0.0,
        "seconds": 0.0,
        "update_operations": 0,
        "untouched_records": 0,
        "llm_used": False,
        "probe_calls": 0,
        "unresolved_count": 0,
    }

    diff = diff_catalogs(old, target)
    if target["version"] == "early":
        if not canonical_equal(old, target):
            raise ValueError("Early Selective Patch must reuse the same K0")
        cost["method"] = "early_k0_reuse"
        cost["seconds"] = perf_counter() - started
        return _impl_result(old, [], diff, [], [], {"errors": [], "checks": {}}, "no_change", cost)

    if not (diff["removed"] or diff["added"] or diff["changed"]):
        cost["method"] = "no_change_detected"
        cost["seconds"] = perf_counter() - started
        return _impl_result(old, [], diff, [], [], {"errors": [], "checks": {}}, "no_change", cost)

    impacted, edges = locate_impact(diff, old)
    knowledge, changes, unresolved, llm_used = _apply_patch(
        old, target, diff, impacted, edges, context
    )
    rule_modified_ids = _rule_modified_ids(changes)
    validation = validate_adaptation(knowledge, old, target, diff, rule_modified_ids)

    untouched = len(set(diff["unchanged_tool_ids"]) - impacted)
    status = "applied"
    if validation["errors"]:
        knowledge = None
        status = "failed"
    elif unresolved:
        status = "unresolved"
    cost["seconds"] = perf_counter() - started
    cost["update_operations"] = len(changes)
    cost["untouched_records"] = untouched
    cost["llm_used"] = llm_used
    cost["unresolved_count"] = len(unresolved)

    return _impl_result(
        knowledge, changes, diff, list(impacted), unresolved, validation, status, cost
    )


def _rule_modified_ids(changes):
    tool_ids = set()
    for change in changes:
        operation = change.get("operation")
        if operation in ("remove_rule", "replace"):
            tool_ids.add(change["tool_id"])
        elif operation == "rewrite_rules":
            tool_ids.update(change.get("tool_ids", []))
    return tool_ids


def _impl_result(knowledge, changes, diff, impacted, unresolved, validation, status, cost):
    return {
        "knowledge": knowledge,
        "changes": changes,
        "diff": diff,
        "impacted_tool_ids": impacted,
        "unresolved_items": unresolved,
        "validation": validation,
        "status": status,
        "cost": cost,
    }


def adapt(old_knowledge, new_metadata, context=None):
    """Return ``(knowledge, changes, cost)``; raise ``ValueError`` on failure.

    On hard validation failure the candidate is rolled back (no knowledge is
    returned) and the reason is raised, so the caller never silently runs an
    invalid snapshot.
    """
    result = adapt_result(old_knowledge, new_metadata, context)
    if result["knowledge"] is None:
        detail = "; ".join(result["validation"]["errors"]) or "validation failed"
        raise ValueError(f"Selective patch validation failed: {detail}")
    return result["knowledge"], result["changes"], result["cost"]


def cache_key(old_knowledge, new_metadata, context=None):
    """Deterministic reuse key over source checksums, strategy and updater settings."""
    _, updater, allow_llm = _resolve_context(context)
    payload = {
        "old_digest": canonical(old_knowledge),
        "new_digest": canonical(new_metadata),
        "updater": updater,
        "allow_llm_update": allow_llm,
    }
    return hashlib.sha256(canonical(payload).encode("utf-8")).hexdigest()


def write_adaptation(old_path, metadata_path, output, context=None):
    """Persist a selective-patch artifact (knowledge + provenance)."""
    old_path, metadata_path, output = Path(old_path), Path(metadata_path), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    artifact = {
        "schema_version": "1.0",
        "strategy": "selective_patch",
        "status": "failed",
        "formal_llm_rewrite": False,
        "validation": {"errors": []},
    }
    try:
        old = read_json(old_path)
        target = read_json(metadata_path)
        result = adapt_result(old, target, context)
        if result["knowledge"] is None:
            raise ValueError(
                "Selective patch validation failed: " + "; ".join(result["validation"]["errors"])
            )
        write_json(output / "knowledge.json", result["knowledge"])
        artifact.update(
            status="validated",
            adapt_status=result["status"],
            target_stage=target["version"],
            benchmark_commit=result["knowledge"]["benchmark_commit"],
            cache_key=cache_key(old, target, context),
            formal_llm_rewrite=result["cost"]["llm_used"],
            input={
                "old_knowledge_file_sha256": hashlib.sha256(old_path.read_bytes()).hexdigest(),
                "target_metadata_file_sha256": hashlib.sha256(
                    metadata_path.read_bytes()
                ).hexdigest(),
            },
            output={
                "knowledge_path": "knowledge.json",
                "knowledge_file_sha256": hashlib.sha256(
                    (output / "knowledge.json").read_bytes()
                ).hexdigest(),
            },
            diff=result["diff"],
            impacted_tool_ids=result["impacted_tool_ids"],
            patch=result["changes"],
            unresolved_items=result["unresolved_items"],
            validation=result["validation"],
            cost=result["cost"],
        )
    except (ValueError, KeyError, OSError, TypeError) as exc:
        artifact["validation"]["errors"].append(f"{type(exc).__name__}: {exc}")
        raise
    finally:
        write_json(output / "adaptation.json", artifact)
    return artifact

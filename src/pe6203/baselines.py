"""Runner-compatible baselines; Full Rewrite uses the shared LLM implementation."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from .benchmark import read_json, write_json


def updater_settings(context):
    """Accept configuration, never inline credentials or arbitrary task context."""
    settings = (context or {}).get("updater", {})
    allowed = {
        "model",
        "temperature",
        "max_tokens",
        "timeout",
        "api_key_env",
        "base_url_env",
        "allow_metadata_api",
        "request_retry",
    }
    if not isinstance(settings, dict) or set(settings) - allowed:
        raise ValueError("Updater requires supported settings and environment variable names only")
    return deepcopy(settings)


def runner_cost(cost):
    """Map updater accounting to the common artifact; unknown usage stays null."""
    prompt, completion = cost["input_tokens"], cost["output_tokens"]
    return {
        "method": "llm_full_rewrite",
        "calls": cost["model_calls"],
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": prompt + completion
        if prompt is not None and completion is not None
        else None,
        "usd": cost["api_cost_usd"],
        "seconds": cost["elapsed_seconds"],
        "update_operations": cost["update_operations"],
    }


def build_knowledge(metadata):
    """Validate and deep-copy a complete, single-stage ToolRecord envelope."""
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
        for field in ("parameters", "output_schema"):
            schema = tool.get(field)
            if field == "output_schema" and schema is None:
                continue
            if not isinstance(schema, dict):
                raise ValueError(f"Invalid {field}: {identity}")
            try:
                Draft202012Validator.check_schema(schema)
            except SchemaError as exc:
                raise ValueError(f"Invalid {field}: {identity}: {exc.message}") from exc
    # Reject non-JSON values rather than emitting a malformed artifact.
    json.dumps(metadata, allow_nan=False)
    return deepcopy(metadata)


def adapt(old_knowledge, new_metadata, strategy, context=None):
    """Return (knowledge, diff_log, update_cost); no task or judge inputs are used."""
    from .patch_variants import VARIANTS
    from .patch_variants import adapt as variant_adapt

    if strategy in VARIANTS:
        return variant_adapt(old_knowledge, new_metadata, strategy, context)
    if strategy == "selective_patch":
        mode = (context or {}).get("selective_mode", "hybrid_v2")
        if mode == "deterministic_v1":
            from .selective import adapt as selective_adapt
        elif mode == "hybrid_v2":
            from .hybrid_selective import adapt as selective_adapt
        elif mode == "hybrid_v5":
            from .selective_v5 import adapt as selective_adapt
        else:
            raise ValueError(f"Unsupported selective mode: {mode}")

        return selective_adapt(old_knowledge, new_metadata, context)
    if strategy not in {"no_update", "full_rewrite"}:
        raise ValueError(f"Unsupported strategy: {strategy}")
    old = build_knowledge(old_knowledge)
    if old["version"] != "early":
        raise ValueError("Both baselines must start from Early knowledge")
    cost = {
        "method": "no_update",
        "calls": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "usd": 0.0,
        "seconds": 0.0,
        "update_operations": 0,
    }
    if strategy == "no_update":
        return old, [], cost  # Never inspect or merge target metadata.
    target = build_knowledge(new_metadata)
    if target["benchmark_commit"] != old["benchmark_commit"]:
        raise ValueError("Benchmark commit mismatch")
    if {t["server_id"] for t in target["tools"]} != {t["server_id"] for t in old["tools"]}:
        raise ValueError("Metadata must cover the same fixed server set")
    if target["version"] == "early":
        if target != old:
            raise ValueError("Early baselines must reuse the same K0")
        return old, [], {**cost, "method": "early_k0_reuse"}
    from integration.baselines import adapt as llm_adapt

    # The shared engine keys by name. Use stable cross-server IDs as temporary
    # names, while retaining the native name as immutable metadata evidence.
    tools = deepcopy(target["tools"])
    for tool in tools:
        tool["native_name"] = tool["name"]
        tool["name"] = tool["tool_id"]
    safe_context = {"updater": updater_settings(context)}
    if (context or {}).get("audit_path"):
        safe_context["audit_path"] = context["audit_path"]
    rewritten, log, update_cost = llm_adapt({}, {"tools": tools}, strategy, safe_context)
    descriptions = {block["name"]: block["metadata"]["description"] for block in rewritten["tools"]}
    for tool in target["tools"]:
        tool["description"] = descriptions[tool["tool_id"]]
    log[0]["rebuilt_tool_ids"] = [t["tool_id"] for t in target["tools"]]
    log[0]["removed_tool_ids"] = sorted(
        {t["tool_id"] for t in old["tools"]} - {t["tool_id"] for t in target["tools"]}
    )
    return build_knowledge(target), log, runner_cost(update_cost)


def write_adaptation(old_path, metadata_path, strategy, output, context=None):
    """Persist the baseline output, provenance and costs without overwriting attempts."""
    from .patch_variants import VARIANTS, NoteError, context_settings

    if strategy in VARIANTS:
        context_settings(context)
    if strategy == "selective_patch":
        mode = (context or {}).get("selective_mode", "hybrid_v2")
        if mode == "deterministic_v1":
            from .selective import write_adaptation as selective_write
        elif mode == "hybrid_v2":
            from .hybrid_selective import write_adaptation as selective_write
        elif mode == "hybrid_v5":
            from .selective_v5 import write_adaptation as selective_write
        else:
            raise ValueError(f"Unsupported selective mode: {mode}")

        return selective_write(old_path, metadata_path, output, context)
    old_path, metadata_path, output = Path(old_path), Path(metadata_path), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    artifact = {
        "schema_version": "1.0",
        "strategy": strategy,
        "status": "failed",
        "formal_llm_rewrite": False,
        "validation": {"errors": []},
    }
    try:
        old, target = read_json(old_path), read_json(metadata_path)
        safe_context = {
            "updater": updater_settings(context),
            "audit_path": str(output / "updater-audit.json"),
        }
        if strategy in VARIANTS and "feedback" in (context or {}):
            safe_context["feedback"] = context["feedback"]
        knowledge, log, cost = adapt(old, target, strategy, safe_context)
        write_json(output / "knowledge.json", knowledge)
        artifact.update(
            status="validated",
            target_stage=target["version"],
            benchmark_commit=knowledge["benchmark_commit"],
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
            patch=log,
            cost=cost,
            formal_llm_rewrite=cost["method"] == "llm_full_rewrite",
        )
        if artifact["formal_llm_rewrite"]:
            artifact["updater_audit_path"] = "updater-audit.json"
        if strategy in VARIANTS and cost["calls"]:
            artifact.update(
                updater_audit_path="updater-audit.json", semantic_grounding="requires_human_review"
            )
    except (ValueError, KeyError, OSError, TypeError) as exc:
        audit = getattr(exc, "audit", None)
        if isinstance(exc, NoteError):
            artifact.update(cost=audit["cost"], updater_audit_path="updater-audit.json")
        elif audit is not None:
            artifact.update(
                formal_llm_rewrite=True,
                cost=runner_cost(audit["update_cost"]),
                updater_audit_path="updater-audit.json",
            )
        artifact["validation"]["errors"].append(f"{type(exc).__name__}: {exc}")
        raise
    finally:
        write_json(output / "adaptation.json", artifact)
    return artifact

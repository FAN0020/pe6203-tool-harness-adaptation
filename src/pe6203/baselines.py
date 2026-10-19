"""Runner-compatible Sprint 1 baselines, adapted from Muchu Wu's submission.

Full Rewrite here is a deterministic complete metadata rebuild, NOT the planned
LLM semantic rewrite. Keep that distinction in every adaptation artifact.
"""

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from time import perf_counter

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from .benchmark import read_json, write_json


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
    if strategy not in {"no_update", "full_rewrite"}:
        raise ValueError(f"Unsupported strategy: {strategy}")
    start = perf_counter()
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
    log = [
        {
            "operation": "full_rebuild",
            "rebuilt_tool_ids": [t["tool_id"] for t in target["tools"]],
            "removed_tool_ids": sorted(
                {t["tool_id"] for t in old["tools"]} - {t["tool_id"] for t in target["tools"]}
            ),
            "rebuilt_blocks": len(target["tools"]),
        }
    ]
    cost.update(
        method="deterministic_full_rebuild",
        seconds=perf_counter() - start,
        update_operations=len(target["tools"]),
    )
    return target, log, cost


def write_adaptation(old_path, metadata_path, strategy, output):
    """Persist the baseline output, provenance and costs without overwriting attempts."""
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
        knowledge, log, cost = adapt(old, target, strategy)
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
        )
    except (ValueError, KeyError, OSError, TypeError) as exc:
        artifact["validation"]["errors"].append(f"{type(exc).__name__}: {exc}")
        raise
    finally:
        write_json(output / "adaptation.json", artifact)
    return artifact

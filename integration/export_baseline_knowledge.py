"""Export No Update and LLM Full Rewrite for Group A's file interface.

LLM export requires explicit --allow-metadata-api and makes a paid updater call.
This exporter does not execute agent tasks or judge calls.
"""

import argparse
import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

from integration import baselines
from integration.baseline_wrapper import run_baseline_once

STAGES = {"early", "middle", "late"}
REQUIRED = {
    "tool_id",
    "server_id",
    "version",
    "name",
    "parameters",
    "description",
    "usage_rules",
    "routing",
}


def validate_envelope(envelope):
    """Check the current ToolRecord contract and runner routing constraints."""
    if envelope.get("schema_version") != "1.0":
        raise ValueError("Expected schema_version 1.0")
    if not isinstance(envelope.get("benchmark_commit"), str) or not envelope["benchmark_commit"]:
        raise ValueError("Missing benchmark_commit")
    if envelope.get("version") not in STAGES:
        raise ValueError("Unknown envelope version")
    tools = envelope.get("tools")
    if not isinstance(tools, list) or not tools:
        raise ValueError("Expected a nonempty complete tools catalog")
    names, ids = set(), set()
    for tool in tools:
        if not isinstance(tool, dict) or not REQUIRED <= tool.keys():
            raise ValueError("Missing required ToolRecord fields")
        if tool.keys() - REQUIRED - {"output_schema"}:
            raise ValueError("Unexpected ToolRecord fields")
        for field in ("tool_id", "server_id", "name"):
            if not isinstance(tool[field], str) or not tool[field].strip():
                raise ValueError(f"Invalid {field}")
        if tool["version"] not in STAGES:
            raise ValueError("Unknown record version")
        if not isinstance(tool["parameters"], dict) or not isinstance(tool["description"], str):
            raise ValueError("Invalid parameters or description")
        if not isinstance(tool["usage_rules"], list) or not all(
            isinstance(rule, str) for rule in tool["usage_rules"]
        ):
            raise ValueError("Invalid usage_rules")
        if tool.get("output_schema") is not None and not isinstance(tool["output_schema"], dict):
            raise ValueError("Invalid output_schema")
        route = tool["routing"]
        if not isinstance(route, dict) or set(route) != {"server_id", "tool_name"}:
            raise ValueError("Invalid routing fields")
        if route["server_id"] != tool["server_id"] or route["tool_name"] != tool["name"]:
            raise ValueError("Routing does not match the unaliased ToolRecord")
        if tool["tool_id"] != f"{tool['server_id']}::{tool['name']}":
            raise ValueError("Invalid tool_id")
        if tool["name"] in names or tool["tool_id"] in ids:
            raise ValueError("Duplicate tool name or tool_id")
        names.add(tool["name"])
        ids.add(tool["tool_id"])


def convert_knowledge(knowledge, source_envelope):
    """Unwrap prototype blocks without discarding any source ToolRecord fields."""
    records = []
    for block in knowledge["tools"]:
        record = block["metadata"]
        if block["name"] != record["name"] or json.loads(block["text"]) != record:
            raise ValueError("Prototype knowledge block is inconsistent")
        records.append(deepcopy(record))
    envelope = deepcopy(source_envelope)
    envelope["tools"] = records
    validate_envelope(envelope)
    return envelope


def adapt_for_runner(old_metadata, target_metadata, strategy, context=None):
    """Adapt Early K0 and return the runner envelope plus the raw update record."""
    validate_envelope(old_metadata)
    validate_envelope(target_metadata)
    if old_metadata["version"] != "early":
        raise ValueError("K0 must come from Early metadata")
    if old_metadata["benchmark_commit"] != target_metadata["benchmark_commit"]:
        raise ValueError("Benchmark commit mismatch")
    if {t["server_id"] for t in old_metadata["tools"]} != {
        t["server_id"] for t in target_metadata["tools"]
    }:
        raise ValueError("Fixed server group mismatch")
    if any(t["version"] != old_metadata["version"] for t in old_metadata["tools"]):
        raise ValueError("Mixed versions in Early metadata")
    if any(t["version"] != target_metadata["version"] for t in target_metadata["tools"]):
        raise ValueError("Mixed versions in target metadata")
    if target_metadata["version"] == "early":
        raise ValueError("This exporter handles Middle/Late; Early reuses K0 directly")

    old_knowledge = baselines.build_knowledge(old_metadata)
    record = run_baseline_once(
        adapt_fn=baselines.adapt,
        old_knowledge=old_knowledge,
        raw_new_metadata=target_metadata,
        strategy=strategy,
        context=context,
    )
    source = old_metadata if strategy == "no_update" else target_metadata
    envelope = convert_knowledge(record["new_knowledge"], source)
    if strategy == "no_update":
        if envelope != source:
            raise ValueError("No Update must preserve Early knowledge exactly")
    else:
        for actual, expected in zip(envelope["tools"], source["tools"], strict=True):
            if {k: v for k, v in actual.items() if k != "description"} != {
                k: v for k, v in expected.items() if k != "description"
            }:
                raise ValueError("Full Rewrite changed protected ToolRecord fields")
    return envelope, record


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-version", choices=["middle", "late"], required=True)
    parser.add_argument("--old-metadata", type=Path, default=root / "examples/metadata/early.json")
    parser.add_argument("--new-metadata", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--allow-metadata-api",
        action="store_true",
        help="Allow paid LLM rewrite of the public target tool catalog",
    )
    args = parser.parse_args()
    new_path = args.new_metadata or root / f"examples/metadata/{args.target_version}.json"
    old, new = read_json(args.old_metadata), read_json(new_path)
    lock = read_json(root / "configs/benchmark.lock.json")
    if old["benchmark_commit"] != lock["commit"]:
        raise ValueError("Metadata does not match the pinned benchmark")
    if new["version"] != args.target_version:
        raise ValueError("Target version does not match metadata")
    if {t["server_id"] for t in old["tools"]} != set(lock["servers"]):
        raise ValueError("This export must cover the complete reviewed smoke server group")

    if not args.allow_metadata_api:
        parser.error(
            "LLM export requires --allow-metadata-api; use the pilot --dry-run for free checks"
        )
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    output = (
        args.output_dir or root / f"outputs/knowledge/{stamp}-{args.target_version}"
    ).resolve()
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "K0-early.json", old)
    for strategy in ("no_update", "full_rewrite"):
        folder = output / strategy
        folder.mkdir()
        knowledge, record = adapt_for_runner(
            old,
            new,
            strategy,
            context={
                "updater": {"allow_metadata_api": True},
                "audit_path": str(folder / "update-audit.json"),
            },
        )
        knowledge_path = folder / "knowledge.json"
        write_json(knowledge_path, knowledge)
        write_json(folder / "adapt-output.json", record)
        raw_cost = record["update_cost"]
        runner_cost = {
            "tokens": (
                raw_cost["input_tokens"] + raw_cost["output_tokens"]
                if raw_cost["input_tokens"] is not None and raw_cost["output_tokens"] is not None
                else None
            ),
            "seconds": 0 if strategy == "no_update" else raw_cost["elapsed_seconds"],
            "usd": raw_cost["api_cost_usd"],
        }
        write_json(
            folder / "runner-config-fragment.json",
            {
                "knowledge_path": str(knowledge_path),
                "update_cost": runner_cost,
            },
        )
        write_json(
            folder / "export-record.json",
            {
                "artifact_type": "baseline_knowledge_export",
                "method": "no_update" if strategy == "no_update" else "llm_full_rewrite",
                "formal_method_ready": False,
                "benchmark_executed": False,
                "target_environment_version": args.target_version,
                "knowledge_version": knowledge["version"],
                "server_group": sorted(lock["servers"]),
                "tool_count": len(knowledge["tools"]),
                "old_metadata_file_sha256": file_hash(args.old_metadata),
                "target_metadata_file_sha256": file_hash(new_path),
                "baseline_source_file_sha256": file_hash(baselines.__file__),
                "exporter_source_file_sha256": file_hash(__file__),
                "knowledge_file_sha256": file_hash(knowledge_path),
                "K0_file_sha256": file_hash(output / "K0-early.json"),
                "runner_update_cost": runner_cost,
                "raw_update_cost": raw_cost,
                "cost_note": "No Update reuse costs zero; measured copy overhead stays in raw_update_cost. K0 construction and serialization are excluded.",
                "official_metrics": {"TF": None, "PE": None, "ECS": None},
            },
        )
        print(f"{strategy}: {len(knowledge['tools'])} tools -> {knowledge_path}")
    print("Knowledge exports only. Merge runner-config-fragment.json into the shared model config.")


if __name__ == "__main__":
    main()

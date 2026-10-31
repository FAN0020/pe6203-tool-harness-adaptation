"""Selective Patch module tests, all synthetic and labeled as such.

These verify wiring and semantics only; none of these scores are benchmark
measurements. The task brief's synthetic matrix (section 7.1) is covered:
no-change skip, add/remove, parameter/description/output changes, missing
evidence, dangling references, hard failure rollback, cache and isolation.
"""

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest
from test_contract import record

from pe6203.baselines import adapt, write_adaptation
from pe6203.runner import prepare_tools
from pe6203.selective import (
    adapt_result,
    build_reference_index,
    cache_key,
    diff_catalogs,
    locate_impact,
)

ROOT = Path(__file__).resolve().parents[1]


def snapshot(version="early", tools=None):
    return {
        "schema_version": "1.0",
        "benchmark_commit": "pinned-commit",
        "version": version,
        "tools": tools if tools is not None else [record(version)],
    }


def add_tool(knowledge, name, tool_id):
    extra = record(knowledge["version"])
    extra.update(name=name, tool_id=tool_id)
    extra["routing"] = {"server_id": "server", "tool_name": name}
    knowledge["tools"].append(extra)
    return extra


def bump_to_late(knowledge):
    knowledge["version"] = "late"
    for tool in knowledge["tools"]:
        tool["version"] = "late"
    return knowledge


def changed_target(change):
    target = snapshot("late")
    if change == "description":
        target["tools"][0]["description"] = "Changed description"
    elif change == "parameter":
        target["tools"][0]["parameters"] = {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        }
    elif change == "output":
        target["tools"][0]["output_schema"] = {
            "type": "object",
            "properties": {
                "nested": {"type": "object", "properties": {"body": {"type": "string"}}}
            },
        }
    elif change == "remove":
        target["tools"].pop(0)
    elif change == "add":
        add_tool(target, "extra_tool", "server::extra_tool")
    return target


def test_no_change_skips_updater_and_preserves_knowledge():
    result = adapt_result(snapshot(), snapshot("late"))  # identical except version marker
    assert result["status"] == "no_change"
    assert result["knowledge"] == snapshot()
    assert result["changes"] == []
    cost = result["cost"]
    assert cost["method"] == "no_change_detected"
    assert cost["calls"] == cost["total_tokens"] == 0
    assert cost["update_operations"] == 0


@pytest.mark.parametrize("change", ["description", "parameter", "output"])
def test_single_field_change_is_detected_and_grounded(change):
    old, target = snapshot(), changed_target(change)
    result = adapt_result(old, target)
    field = {
        "description": "description",
        "parameter": "parameters",
        "output": "output_schema",
    }[change]
    assert result["knowledge"]["tools"][0][field] == target["tools"][0][field]
    assert any(c["operation"] == "replace" for c in result["changes"])
    assert result["cost"]["calls"] == 0  # deterministic path never calls the updater
    assert result["status"] == "applied"


def test_add_and_remove_update_manifest_and_routing():
    old = snapshot()
    add_tool(old, "second_tool", "server::second_tool")
    target = copy.deepcopy(old)
    bump_to_late(target)
    target["tools"].pop(1)  # remove second_tool
    add_tool(target, "new_tool", "server::new_tool")  # add new_tool
    result = adapt_result(old, target)
    ids = {t["tool_id"] for t in result["knowledge"]["tools"]}
    assert "server::second_tool" not in ids and "server::new_tool" in ids
    operations = {c["operation"] for c in result["changes"]}
    assert {"add", "remove"} <= operations
    tools, routes = prepare_tools(result["knowledge"]["tools"], "selective_patch")
    assert set(routes) == {t["function"]["name"] for t in tools}
    assert result["cost"]["untouched_records"] == 1  # old_tool stayed untouched


def test_output_position_change_flags_dependent_rule_as_unresolved():
    old = snapshot()
    old["tools"][0]["output_schema"] = {
        "type": "object",
        "properties": {"body": {"type": "string"}},
    }
    add_tool(old, "publisher", "server::publisher")
    old["tools"][1]["usage_rules"] = ["Take the body field from old_tool's result and publish it"]
    target = copy.deepcopy(old)
    bump_to_late(target)
    target["tools"][0]["output_schema"] = {
        "type": "object",
        "properties": {"nested": {"type": "object", "properties": {"body": {"type": "string"}}}},
    }
    result = adapt_result(old, target)
    kinds = {u["kind"] for u in result["unresolved_items"]}
    assert "needs_semantic_rewrite" in kinds
    publisher = next(t for t in result["knowledge"]["tools"] if t["tool_id"] == "server::publisher")
    assert publisher["usage_rules"][0].startswith("Take the body")  # not fabricated


def test_removed_tool_drops_dangling_rule_instead_of_keeping_invalid_reference():
    old = snapshot()
    add_tool(old, "publisher", "server::publisher")
    old["tools"][1]["usage_rules"] = ["Use old_tool then publish"]
    target = copy.deepcopy(old)
    bump_to_late(target)
    target["tools"].pop(0)  # remove old_tool
    result = adapt_result(old, target)
    ids = {t["tool_id"] for t in result["knowledge"]["tools"]}
    assert "server::old_tool" not in ids
    assert result["knowledge"]["tools"][0]["usage_rules"] == []  # dangling rule dropped
    assert any(c["operation"] == "remove_rule" for c in result["changes"])
    assert result["status"] == "unresolved"


def test_new_optional_field_is_not_invented():
    target = changed_target("add")
    result = adapt_result(snapshot(), target)
    added = next(t for t in result["knowledge"]["tools"] if t["tool_id"] == "server::extra_tool")
    assert "max_price" not in added["parameters"].get("properties", {})
    assert added["usage_rules"] == []


def test_insufficient_evidence_is_not_fabricated():
    target = changed_target("description")
    result = adapt_result(snapshot(), target)
    record_updated = result["knowledge"]["tools"][0]
    assert record_updated["description"] == "Changed description"
    assert record_updated["usage_rules"] == []  # no invented rules
    assert result["unresolved_items"] == []


def test_unchanged_records_are_canonically_preserved_including_version():
    old = snapshot()
    add_tool(old, "keeper", "server::keeper")
    target = copy.deepcopy(old)
    bump_to_late(target)
    target["tools"][0]["description"] = "Changed"
    result = adapt_result(old, target)
    assert result["knowledge"]["tools"][1] == old["tools"][1]
    assert result["knowledge"]["tools"][1]["version"] == "early"  # source version preserved
    assert result["cost"]["untouched_records"] == 1


@pytest.mark.parametrize("defect", ["server_set", "commit", "not_early"])
def test_selective_rejects_mixed_sources(defect):
    old, target = snapshot(), changed_target("description")
    if defect == "server_set":
        target["tools"][0].update(server_id="other", tool_id="other::old_tool")
        target["tools"][0]["routing"]["server_id"] = "other"
    elif defect == "commit":
        target["benchmark_commit"] = "other-commit"
    else:
        old = snapshot("middle")
    with pytest.raises(ValueError):
        adapt(old, target, "selective_patch")


def test_hard_validation_failure_rolls_back_without_group_fallback():
    old, target = snapshot(), snapshot("late")
    target["tools"][0]["parameters"] = {"type": "not-a-json-schema-type"}
    with pytest.raises(ValueError):
        adapt(old, target, "selective_patch")
    # no silent full rewrite: the deterministic method name is still the strategy's
    knowledge, changes, cost = adapt(old, changed_target("description"), "selective_patch")
    assert cost["method"] == "deterministic_diff_selective_patch"


def test_early_selective_reuses_k0_without_update():
    old = snapshot()
    knowledge, changes, cost = adapt(old, copy.deepcopy(old), "selective_patch")
    assert knowledge == old and changes == []
    assert cost["method"] == "early_k0_reuse"


def test_cache_key_varies_with_sources_and_config():
    old = snapshot()
    first = cache_key(old, changed_target("description"))
    again = changed_target("description")
    again["tools"][0]["description"] = "Different"
    assert cache_key(old, again) != first
    assert cache_key(old, snapshot("late"), {"allow_llm_update": True}) != cache_key(
        old, snapshot("late")
    )


def test_reference_index_and_impact_are_one_hop():
    old = snapshot()
    add_tool(old, "publisher", "server::publisher")
    old["tools"][1]["usage_rules"] = ["Pass old_tool output to publisher"]
    index = build_reference_index(old)
    assert index["server::old_tool"] == ["server::publisher"]
    diff = diff_catalogs(old, changed_target("parameter"))
    impacted, edges = locate_impact(diff, old)
    assert {"server::old_tool", "server::publisher"} <= impacted
    assert edges == {"server::publisher": ["server::old_tool"]}


@pytest.mark.parametrize("strategy", ["no_update", "selective_patch"])
def test_cli_adapt_writes_consumable_artifact(tmp_path, strategy):
    old_path, target_path = tmp_path / "early.json", tmp_path / "late.json"
    old_path.write_text(json.dumps(snapshot()))
    target_path.write_text(json.dumps(changed_target("description")))
    output = tmp_path / "adaptation"
    command = [
        sys.executable,
        "-m",
        "pe6203.cli",
        "adapt",
        "--strategy",
        strategy,
        "--old-knowledge",
        str(old_path),
        "--new-metadata",
        str(target_path),
        "--output",
        str(output),
    ]
    run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    knowledge = json.loads((output / "knowledge.json").read_text())
    artifact = json.loads((output / "adaptation.json").read_text())
    assert artifact["strategy"] == strategy and artifact["status"] == "validated"
    assert artifact["formal_llm_rewrite"] is False
    assert len(artifact["output"]["knowledge_file_sha256"]) == 64
    prepare_tools(knowledge["tools"], strategy)
    if strategy == "selective_patch":
        assert artifact["cost"]["method"] == "deterministic_diff_selective_patch"
        assert knowledge["version"] == "late"
        assert knowledge["tools"][0]["description"] == "Changed description"
        assert any(item["operation"] == "replace" for item in artifact["patch"])


def test_failed_adaptation_is_recorded_without_knowledge_output(tmp_path):
    old_path, target_path = tmp_path / "old.json", tmp_path / "target.json"
    old_path.write_text(json.dumps(snapshot()))
    bad = changed_target("description")
    bad["tools"][0]["routing"]["tool_name"] = "wrong"  # invalid routing identity
    target_path.write_text(json.dumps(bad))
    output = tmp_path / "failed"
    with pytest.raises(ValueError):
        write_adaptation(old_path, target_path, "selective_patch", output)
    assert not (output / "knowledge.json").exists()
    result = json.loads((output / "adaptation.json").read_text())
    assert result["status"] == "failed" and result["validation"]["errors"]


def test_selective_knowledge_never_leaks_target_into_untouched_records():
    old = snapshot()
    add_tool(old, "keeper", "server::keeper")
    old["tools"][1]["description"] = "Kept description"
    target = copy.deepcopy(old)
    bump_to_late(target)
    target["tools"][0]["description"] = "Changed"
    result = adapt_result(old, target)
    tools, _routes = prepare_tools(result["knowledge"]["tools"], "selective_patch")
    keeper = next(t for t in tools if t["function"]["name"] == "keeper")
    assert "Kept description" in keeper["function"]["description"]
    assert "Changed" not in keeper["function"]["description"]


def test_cross_server_same_names_remain_distinct_after_patch():
    old = snapshot()
    second = copy.deepcopy(old["tools"][0])
    second.update(server_id="other", tool_id="other::old_tool")
    second["routing"]["server_id"] = "other"
    old["tools"].append(second)
    target = bump_to_late(copy.deepcopy(old))
    target["tools"][0]["description"] = "Updated"
    result = adapt_result(old, target)
    assert result["knowledge"] is not None, result["validation"]
    tools, routes = prepare_tools(result["knowledge"]["tools"], "selective_patch", "namespaced")
    assert len(tools) == len(routes) == 2
    assert result["knowledge"]["tools"][1] == second


def test_validation_rejects_missing_target_record():
    from pe6203.selective import validate_adaptation

    old = snapshot()
    target = changed_target("add")
    diff = diff_catalogs(old, target)
    candidate = adapt_result(old, target)["knowledge"]
    assert not validate_adaptation(candidate, old, target, diff)["errors"]
    candidate["tools"].pop()
    assert validate_adaptation(candidate, old, target, diff)["errors"]


def test_unverified_optional_llm_path_cannot_report_zero_billed_cost():
    with pytest.raises(ValueError, match="deterministic"):
        adapt_result(snapshot(), changed_target("description"), {"allow_llm_update": True})

"""Baseline contracts at the real runner boundary, independent of model quality."""

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest
from test_contract import record

from pe6203.baselines import adapt, build_knowledge, write_adaptation
from pe6203.runner import prepare_tools, run

ROOT = Path(__file__).resolve().parents[1]


def snapshot(version="early"):
    return {
        "schema_version": "1.0",
        "benchmark_commit": "pinned-commit",
        "version": version,
        "tools": [record(version)],
    }


def test_rebuild_preserves_runner_envelope_schema_rules_and_routes():
    metadata = snapshot("late")
    metadata["tools"][0]["usage_rules"] = ["Use UTC"]
    metadata["tools"][0]["output_schema"] = {"type": "object"}
    knowledge = build_knowledge(metadata)
    assert knowledge == metadata
    tools, routes = prepare_tools(knowledge["tools"], "full_rewrite", "namespaced")
    assert "Use UTC" in tools[0]["function"]["description"]
    assert list(routes.values()) == [{"server_id": "server", "tool_name": "old_tool"}]
    knowledge["tools"][0]["parameters"]["properties"]["new"] = {"type": "string"}
    assert metadata["tools"][0]["parameters"]["properties"] == {}


def test_cross_server_same_names_are_not_dropped_or_rejected():
    metadata = snapshot()
    other = record()
    other.update(server_id="other", tool_id="other::old_tool")
    other["routing"]["server_id"] = "other"
    metadata["tools"].append(other)
    tools, routes = prepare_tools(build_knowledge(metadata)["tools"], "no_update", "namespaced")
    assert len(tools) == len(routes) == 2
    assert {r["server_id"] for r in routes.values()} == {"server", "other"}


@pytest.mark.parametrize("change", ["rename", "add", "remove", "parameter", "description", "rules"])
def test_full_rebuild_uses_entire_target_catalog_and_no_update_stays_early(change):
    old, target = snapshot(), snapshot("late")
    extra = copy.deepcopy(target["tools"][0])
    extra.update(name="second", tool_id="server::second")
    extra["routing"]["tool_name"] = "second"
    target["tools"].append(extra)
    if change == "rename":
        target["tools"][0].update(name="replacement", tool_id="server::replacement")
        target["tools"][0]["routing"]["tool_name"] = "replacement"
    elif change == "remove":
        target["tools"].pop(0)
    elif change == "parameter":
        target["tools"][0]["parameters"] = {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        }
    elif change == "description":
        target["tools"][0]["description"] = "Changed meaning"
    elif change == "rules":
        target["tools"][0]["usage_rules"] = ["New constraint"]
    old_before, target_before = copy.deepcopy(old), copy.deepcopy(target)
    fresh, log, cost = adapt(old, target, "full_rewrite")
    assert fresh == target
    assert log[0]["rebuilt_tool_ids"] == [t["tool_id"] for t in target["tools"]]
    assert cost["method"] == "deterministic_full_rebuild"
    assert cost["calls"] == cost["total_tokens"] == 0
    unchanged, log, cost = adapt(old, target, "no_update")
    assert unchanged == old and log == []
    assert cost["seconds"] == cost["usd"] == cost["total_tokens"] == 0
    fresh["tools"][0]["description"] = "Output mutation"
    unchanged["tools"][0]["description"] = "Output mutation"
    assert old == old_before and target == target_before


def test_no_update_never_reads_target_metadata():
    old = snapshot()
    knowledge, log, cost = adapt(old, None, "no_update")
    assert knowledge == old and log == []
    assert cost["update_operations"] == 0


@pytest.mark.parametrize("defect", ["duplicate", "route", "parameters", "version", "empty"])
def test_invalid_metadata_cannot_produce_runnable_knowledge(defect):
    target = snapshot("late")
    if defect == "duplicate":
        target["tools"].append(copy.deepcopy(target["tools"][0]))
    elif defect == "route":
        target["tools"][0]["routing"]["server_id"] = "outside"
    elif defect == "parameters":
        target["tools"][0]["parameters"] = {"type": "not-a-json-schema-type"}
    elif defect == "version":
        target["tools"][0]["version"] = "early"
    else:
        target["tools"] = []
    with pytest.raises(ValueError):
        build_knowledge(target)


@pytest.mark.parametrize("defect", ["commit", "server_set", "not_early"])
def test_adaptation_rejects_mixed_sources_and_non_early_base(defect):
    old, target = snapshot(), snapshot("late")
    if defect == "commit":
        target["benchmark_commit"] = "different-commit"
    elif defect == "server_set":
        t = target["tools"][0]
        t.update(server_id="other", tool_id="other::old_tool")
        t["routing"]["server_id"] = "other"
    else:
        old = snapshot("middle")
    with pytest.raises(ValueError):
        adapt(old, target, "full_rewrite")


@pytest.mark.parametrize("strategy", ["no_update", "full_rewrite"])
def test_cli_adapt_writes_consumable_artifact_and_refuses_overwrite(tmp_path, strategy):
    old, target = tmp_path / "early.json", tmp_path / "late.json"
    old.write_text(json.dumps(snapshot()))
    target.write_text(json.dumps(snapshot("late")))
    output = tmp_path / "adaptation"
    command = [
        sys.executable,
        "-m",
        "pe6203.cli",
        "adapt",
        "--strategy",
        strategy,
        "--old-knowledge",
        str(old),
        "--new-metadata",
        str(target),
        "--output",
        str(output),
    ]
    run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    knowledge = json.loads((output / "knowledge.json").read_text())
    artifact = json.loads((output / "adaptation.json").read_text())
    assert knowledge["version"] == ("early" if strategy == "no_update" else "late")
    assert artifact["strategy"] == strategy and artifact["status"] == "validated"
    assert artifact["target_stage"] == "late"
    assert len(artifact["output"]["knowledge_file_sha256"]) == 64
    assert artifact["formal_llm_rewrite"] is False
    prepare_tools(knowledge["tools"], strategy)
    assert subprocess.run(command, capture_output=True).returncode == 2


def test_early_full_rewrite_reuses_k0_without_update_cost():
    old = snapshot()
    knowledge, log, cost = adapt(old, copy.deepcopy(old), "full_rewrite")
    assert knowledge == old and log == []
    assert cost["seconds"] == cost["update_operations"] == 0


def test_selective_patch_is_not_silently_implemented_as_full_rewrite():
    with pytest.raises(ValueError, match="Unsupported"):
        adapt(snapshot(), snapshot("late"), "selective_patch")


@pytest.mark.parametrize("defect", ["knowledge_changed", "wrong_strategy", "wrong_stage"])
def test_runner_rejects_mismatched_adaptation_before_model_calls(tmp_path, monkeypatch, defect):
    from pe6203.benchmark import read_json

    if not (ROOT / ".cache/mcpevol/upstream/.git").exists():
        pytest.skip("Requires the pinned upstream checkout")
    folder = tmp_path / "adaptation"
    write_adaptation(
        ROOT / "examples/catalogs/task139/early.json",
        ROOT / "examples/catalogs/task139/late.json",
        "full_rewrite",
        folder,
    )
    if defect == "knowledge_changed":
        with (folder / "knowledge.json").open("a") as stream:
            stream.write(" ")
    config = read_json(ROOT / "configs/full-catalog-smoke.json")
    config.update(
        root=str(ROOT),
        output_dir=str(tmp_path / "run"),
        adaptation_path=str(folder / "adaptation.json"),
    )
    monkeypatch.delenv("AGENT_API_KEY", raising=False)
    _, result = run(
        139,
        "middle" if defect == "wrong_stage" else "late",
        "no_update" if defect == "wrong_strategy" else "full_rewrite",
        0,
        config,
    )
    assert result["status"] == "blocked" and result["TF"] is None
    assert "adaptation" in result["errors"][0]["message"].lower()
    assert "AGENT_API_KEY" not in result["errors"][0]["message"]


def test_failed_adaptation_is_recorded_without_a_knowledge_output(tmp_path):
    old, target = tmp_path / "old.json", tmp_path / "target.json"
    old.write_text(json.dumps(snapshot()))
    bad = snapshot("late")
    bad["tools"][0]["routing"]["tool_name"] = "wrong"
    target.write_text(json.dumps(bad))
    output = tmp_path / "failed"
    with pytest.raises(ValueError):
        write_adaptation(old, target, "full_rewrite", output)
    assert not (output / "knowledge.json").exists()
    result = json.loads((output / "adaptation.json").read_text())
    assert result["status"] == "failed" and result["validation"]["errors"]

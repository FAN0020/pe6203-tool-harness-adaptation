"""Regressions: label leakage, live-schema leakage, route drift, invalid judge scores."""

import copy
import importlib
import json
import math
from zipfile import ZipFile

import pytest


def module(name):
    try:
        return importlib.import_module("pe6203." + name)
    except ImportError as exc:
        pytest.fail(f"Adapter functionality not implemented: {exc}")


def record(version="early"):
    return {
        "tool_id": "server::old_tool",
        "server_id": "server",
        "version": version,
        "name": "old_tool",
        "parameters": {"type": "object", "properties": {}},
        "description": "Original description",
        "usage_rules": [],
        "routing": {"server_id": "server", "tool_name": "old_tool"},
    }


def test_task_loader_excludes_labels_and_reference_trajectories(tmp_path):
    data = tmp_path / "src/custom/data/test_cases"
    data.mkdir(parents=True)
    (data / "chosen_idx.json").write_text(json.dumps({"samples": [{"idx": 139}]}))
    (data / "test_cases.json").write_text(
        json.dumps(
            [
                {
                    "idx": 139,
                    "question": "Create a project",
                    "servers": {"server": ["old_tool"]},
                    "answer": "ORACLE",
                    "eval_result": {"task_fulfillment": 10},
                    "trajectory_messages": [{"content": "REFERENCE"}],
                    "response": "RATIONALE",
                }
            ]
        )
    )
    result = module("benchmark").load_task(tmp_path, 139)
    assert result == {
        "idx": 139,
        "question": "Create a project",
        "servers": {"server": ["old_tool"]},
    }
    with pytest.raises(ValueError, match="selected"):
        module("benchmark").load_task(tmp_path, 333)


def test_frozen_knowledge_preserves_old_name_schema_and_description():
    records = [record()]
    original = copy.deepcopy(records)
    tools, routes = module("runner").prepare_tools(records, "no_update")
    assert tools[0]["function"] == {
        "name": "old_tool",
        "description": "Original description",
        "parameters": {"type": "object", "properties": {}},
    }
    assert routes == {"old_tool": {"server_id": "server", "tool_name": "old_tool"}}
    assert records == original


def test_no_update_rejects_new_snapshot_and_duplicate_routes():
    prepare = module("runner").prepare_tools
    with pytest.raises(ValueError, match="early"):
        prepare([record("late")], "no_update")
    with pytest.raises(ValueError, match="Duplicate"):
        prepare([record(), record()], "selective_patch")


def test_judge_rejects_missing_out_of_range_boolean_and_nonfinite_scores():
    parse = module("judge").parse_scores
    good = {"task_fulfillment": 8, "grounding": 9, "planning_and_efficiency": 7}
    assert parse("```json\n" + json.dumps(good) + "\n```") == good
    for bad in [None, 0, 11, True, math.nan, 3.5]:
        with pytest.raises(ValueError):
            parse(json.dumps({**good, "task_fulfillment": bad}))
    with pytest.raises(ValueError):
        parse('{"grounding": 8}')


def test_missing_judge_runs_are_not_zero_and_incomplete_is_explicit():
    aggregate = module("judge").aggregate_scores
    assert aggregate([], expected=5) == {
        "successful_runs": 0,
        "total_runs": 5,
        "complete": False,
        "task_fulfillment_mean": None,
        "grounding_mean": None,
        "planning_and_efficiency_mean": None,
    }
    result = aggregate(
        [{"task_fulfillment": 8, "grounding": 6, "planning_and_efficiency": 7}], expected=5
    )
    assert result["task_fulfillment_mean"] == 8
    assert result["complete"] is False


def test_ecs_requires_complete_triplet_and_labels_variance_convention():
    ecs = module("judge").ecs
    result = ecs({"early": 6, "middle": 8, "late": 10})
    assert result["upstream_population"] == pytest.approx(6.3670068381445475)
    assert result["paper_sample"] == 6
    assert ecs({"early": 8, "middle": None, "late": 10})["upstream_population"] is None


def test_archive_extraction_resolves_nested_dependencies_and_rejects_traversal(tmp_path):
    archive = tmp_path / "bundle.zip"
    files = {
        "node_modules/a/package.json": {"name": "a", "dependencies": {"b": "1"}},
        "node_modules/a/node_modules/b/package.json": {"name": "b"},
        "node_modules/b/package.json": {"name": "WRONG"},
    }
    with ZipFile(archive, "w") as z:
        for path, obj in files.items():
            z.writestr(path, json.dumps(obj))
        z.writestr("node_modules/a/index.js", "export const answer = 42")
    module("bootstrap").extract_packages(archive, tmp_path / "out", ["a"])
    assert (tmp_path / "out/node_modules/a/node_modules/b/package.json").exists()
    assert not (tmp_path / "out/node_modules/b").exists()
    with ZipFile(archive, "a") as z:
        z.writestr("node_modules/a/../../../escape", "bad")
    with pytest.raises(ValueError, match="Unsafe"):
        module("bootstrap").extract_packages(archive, tmp_path / "bad", ["a"])


def test_checksum_mismatch_stops_before_extracting(tmp_path):
    p = tmp_path / "bad.zip"
    p.write_bytes(b"not the released archive")
    with pytest.raises(ValueError, match="SHA256"):
        module("bootstrap").verify_sha256(p, "0" * 64)


def test_working_directory_cannot_escape_run_workspace(tmp_path):
    check = module("transport").check_arguments
    with pytest.raises(ValueError, match="workingDirectory"):
        check({"workingDirectory": str(tmp_path.parent)}, tmp_path)
    check({"workingDirectory": str(tmp_path)}, tmp_path)


def test_credentials_must_be_explicit_and_errors_redact_secrets(monkeypatch):
    m = module("runner")
    monkeypatch.delenv("TEST_KEY", raising=False)
    monkeypatch.setenv("TEST_BASE", "https://api.example.test/v1")
    with pytest.raises(ValueError, match="TEST_KEY"):
        m.credentials({"api_key_env": "TEST_KEY", "base_url_env": "TEST_BASE"})
    assert (
        m.redact("request sk-secret-value failed", ["sk-secret-value"])
        == "request [REDACTED] failed"
    )


def test_official_judge_formatting_keeps_upstream_truncation_and_hides_agent_text():
    from pathlib import Path

    upstream = Path(__file__).resolve().parents[1] / ".cache/mcpevol/upstream"
    if not upstream.exists():
        pytest.skip("Requires pinned upstream source")
    r = record()
    messages = [
        {"role": "system", "content": "SYSTEM_SECRET"},
        {"role": "user", "content": "TASK"},
        {"role": "assistant", "content": "HIDDEN_REASONING"},
        {"role": "tool", "tool_call_id": "call-1", "content": "x" * 1001},
    ]
    prompt = module("judge").official_prompt(
        upstream,
        {"question": "TASK", "servers": {"server": ["old_tool"]}},
        [r],
        messages,
        "ANSWER",
        [0, 1, 2],
    )
    assert "HIDDEN_REASONING" not in prompt
    assert "SYSTEM_SECRET" not in prompt
    assert "x" * 1000 + "..." in prompt
    assert "[Tool Result tool_call_id='call-1']" in prompt
    assert "Tools for Server - server:" in prompt


def test_protocol_hash_ignores_run_paths_but_not_models_or_endpoints():
    hash_protocol = module("runner").protocol_hash
    base = {
        "agent": {"model": "A"},
        "judge": {"model": "J"},
        "max_rounds": 12,
        "root": "/one",
        "output_dir": "/run1",
        "knowledge_path": "early.json",
    }
    endpoints = {"agent": "https://service.test/v1", "judge": "https://service.test/v1"}
    expected = hash_protocol(base, endpoints)
    assert (
        hash_protocol(
            {**base, "root": "/two", "output_dir": "/run2", "knowledge_path": "patched.json"},
            endpoints,
        )
        == expected
    )
    assert hash_protocol({**base, "agent": {"model": "B"}}, endpoints) != expected
    assert hash_protocol(base, {**endpoints, "judge": "https://other.test/v1"}) != expected

"""Synthetic evidence contracts; no model/behavioral performance claims."""

import copy
import hashlib
import json

import pytest
from test_hybrid_selective import tool

from pe6203.baselines import adapt, write_adaptation
from pe6203.benchmark import digest
from pe6203.capability import enrich, fingerprint, load_evidence
from pe6203.runner import prepare_tools


def catalogs():
    data = {
        "schema_version": "1.0",
        "benchmark_commit": "synthetic-fixture",
        "version": "early",
        "tools": [
            tool("helper", "Returns a prompt template, not an audit."),
            tool("unrelated", "Stores a number.", ["Preserve input."]),
        ],
    }
    return data, copy.deepcopy(data)


def bundle(record):
    return {
        "version": "capability-evidence-v1",
        "entries": [
            {
                "tool_id": record["tool_id"],
                "tool_fingerprint": fingerprint(record),
                "kind": "catalog",
                "quote": record["description"],
            }
        ],
    }


def test_public_v3_enriches_unchanged_without_metadata_diff_or_model():
    old, target = catalogs()
    snapshot = copy.deepcopy((old, target))
    knowledge, changes, cost = adapt(
        old,
        target,
        "selective_patch",
        {"selective_mode": "hybrid_v3", "capability_evidence": bundle(target["tools"][0])},
    )
    assert (old, target) == snapshot
    assert cost["calls"] == 0
    assert all(c["operation"] == "initial_evidence_enrichment" for c in changes)
    for original, updated in zip(old["tools"], knowledge["tools"]):
        assert {k: updated[k] for k in original} == original
    boundary = knowledge["tools"][0]["capability_boundary"]
    assert boundary["observations"][0]["object"] == "declared_tool_contract"
    assert "does not execute" in boundary["limitation"]
    assert knowledge["tools"][1]["capability_boundary"]["status"] == "unresolved_no_evidence"
    model_tools, routes = prepare_tools(knowledge["tools"], "selective_patch")
    assert "prompt template" in model_tools[0]["function"]["description"]
    assert "Capability evidence" in model_tools[0]["function"]["description"]
    assert routes["helper"] == old["tools"][0]["routing"]


@pytest.mark.parametrize("mode", ["hybrid_v2", "deterministic_v1"])
def test_historical_modes_still_leave_unchanged_records_exact(mode):
    old, target = catalogs()
    knowledge, _, _ = adapt(old, target, "selective_patch", {"selective_mode": mode})
    assert knowledge == old
    assert "capability_boundary" not in knowledge["tools"][0]


@pytest.mark.parametrize("mutation", ["quote", "fingerprint", "assertion", "identity", "kind"])
def test_unsupported_or_stale_semantics_rejected(mutation):
    old, target = catalogs()
    evidence = bundle(target["tools"][0])
    row = evidence["entries"][0]
    if mutation == "quote":
        row["quote"] = "The generated Python is secure."
    elif mutation == "fingerprint":
        target["tools"][0]["description"] = "Changed capability."
    elif mutation == "assertion":
        row["establishes"] = "The entire generated program has been validated."
    elif mutation == "identity":
        row["tool_id"] = "server::invented"
    else:
        row["kind"] = "model_opinion"
    with pytest.raises(ValueError):
        enrich(target, old, evidence)


def test_change_removes_old_boundary_and_requires_new_fingerprint():
    old, target = catalogs()
    enrich(old, old, bundle(old["tools"][0]))
    target = copy.deepcopy(old)
    target["tools"][0]["description"] = "Returns text only."
    changes = enrich(target, old, {"version": "capability-evidence-v1", "entries": []})
    assert changes[0]["operation"] == "capability_change_propagation"
    assert target["tools"][0]["capability_boundary"]["observations"] == []
    assert target["tools"][0]["capability_boundary"]["status"] == "unresolved_no_evidence"
    assert target["tools"][1] == old["tools"][1]


@pytest.mark.parametrize("kind", ["source", "probe"])
def test_external_source_hash_and_exact_excerpt(tmp_path, kind):
    old, target = catalogs()
    content = json.dumps(
        {
            "tool_id": target["tools"][0]["tool_id"],
            "tool_fingerprint": fingerprint(target["tools"][0]),
            "arguments": {"input": "x"},
            "result": "Prompt Template",
        }
    )
    source = tmp_path / "source.json"
    source.write_text(content)
    entry = {
        "tool_id": target["tools"][0]["tool_id"],
        "tool_fingerprint": fingerprint(target["tools"][0]),
        "kind": kind,
        "path": source.name,
        "sha256": hashlib.sha256(content.encode()).hexdigest(),
        "quote": "Prompt Template",
    }
    manifest = tmp_path / "evidence.json"
    manifest.write_text(json.dumps({"version": "capability-evidence-v1", "entries": [entry]}))
    loaded = load_evidence(manifest)
    enrich(target, old, loaded)
    observation = target["tools"][0]["capability_boundary"]["observations"][0]
    assert observation["source_sha256"] == entry["sha256"]
    assert observation["literal_observation"] == "Prompt Template"
    source.write_text(content + "changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        load_evidence(manifest)


def test_v3_file_entry_publishes_hashed_knowledge_and_no_overwrite(tmp_path):
    old, target = catalogs()
    for name, data in [("old", old), ("target", target)]:
        (tmp_path / (name + ".json")).write_text(json.dumps(data))
    context = {"selective_mode": "hybrid_v3", "capability_evidence": bundle(target["tools"][0])}
    result = write_adaptation(
        tmp_path / "old.json",
        tmp_path / "target.json",
        "selective_patch",
        tmp_path / "out",
        context,
    )
    assert result["status"] == "validated"
    assert result["capability_evidence_sha256"] == digest(context["capability_evidence"])
    assert (
        result["output"]["knowledge_file_sha256"]
        == hashlib.sha256((tmp_path / "out/knowledge.json").read_bytes()).hexdigest()
    )
    with pytest.raises(FileExistsError):
        write_adaptation(
            tmp_path / "old.json",
            tmp_path / "target.json",
            "selective_patch",
            tmp_path / "out",
            context,
        )


def test_missing_evidence_fails_without_publishing_knowledge(tmp_path):
    old, target = catalogs()
    for name, data in [("old", old), ("target", target)]:
        (tmp_path / (name + ".json")).write_text(json.dumps(data))
    with pytest.raises(ValueError, match="evidence"):
        write_adaptation(
            tmp_path / "old.json",
            tmp_path / "target.json",
            "selective_patch",
            tmp_path / "out",
            {"selective_mode": "hybrid_v3"},
        )
    assert not (tmp_path / "out/knowledge.json").exists()
    assert json.loads((tmp_path / "out/adaptation.json").read_text())["status"] == "failed"


def test_v3_metadata_change_uses_light_screen_and_preserves_rules(monkeypatch):
    from integration import baselines as provider

    old, target = catalogs()
    target["version"] = "late"
    for entry in target["tools"]:
        entry["version"] = "late"
        entry["usage_rules"] = []
    target["tools"][0]["description"] = "Returns an updated prompt template; not an audit."
    calls = []

    def request(messages, settings):
        payload = json.loads(messages[-1]["content"])
        calls.append(payload)
        return {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": json.dumps(
                            {
                                "screened_tool_ids": [c["tool_id"] for c in payload["directory"]],
                                "candidates": [],
                            }
                        )
                    },
                }
            ],
            "usage": {},
        }

    monkeypatch.setattr(provider, "_request_completion", request)
    knowledge, changes, cost = adapt(
        old,
        target,
        "selective_patch",
        {
            "selective_mode": "hybrid_v3",
            "capability_evidence": bundle(target["tools"][0]),
            "updater": {"allow_metadata_api": True},
        },
    )
    assert cost["calls"] == 1
    assert [c["tool_id"] for c in calls[0]["directory"]] == ["server::unrelated"]
    assert calls[0]["program_completed_tool_ids"] == ["server::helper"]
    assert "capability_evidence" not in json.dumps(calls[0])
    assert knowledge["tools"][0]["description"] == target["tools"][0]["description"]
    assert knowledge["tools"][1]["usage_rules"] == old["tools"][1]["usage_rules"]
    assert any(c["operation"] == "capability_change_propagation" for c in changes)


@pytest.mark.parametrize("stage", ["early", "middle", "late"])
def test_no_change_artifact_targets_requested_environment_without_rewriting_k0(tmp_path, stage):
    old, target = catalogs()
    target["version"] = stage
    for t in target["tools"]:
        t["version"] = stage
        if stage != "early":
            t["usage_rules"] = []
    for name, data in [("old", old), ("target", target)]:
        (tmp_path / f"{name}.json").write_text(json.dumps(data))
    result = write_adaptation(
        tmp_path / "old.json",
        tmp_path / "target.json",
        "selective_patch",
        tmp_path / "out",
        {"selective_mode": "hybrid_v3", "capability_evidence": bundle(target["tools"][0])},
    )
    knowledge = json.loads((tmp_path / "out/knowledge.json").read_text())
    assert result["target_stage"] == stage
    assert result["cost"]["calls"] == 0
    assert knowledge["version"] == "early"
    assert all(t["version"] == "early" for t in knowledge["tools"])
    assert knowledge["tools"][1]["usage_rules"] == old["tools"][1]["usage_rules"]

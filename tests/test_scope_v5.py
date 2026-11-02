"""Independent scope failure cases; scripted replies do not prove model recall."""

import copy
import json

import pytest
from test_hybrid_selective import catalogs as catalogs
from test_hybrid_selective import tool
from test_selective_v5 import ctx, install_llm, reply

from pe6203.scope_v5 import screen_candidates
from pe6203.selective_v5 import HybridPatchError, adapt_result


def test_program_only_parameter_sync_needs_no_llm(monkeypatch):
    old = {
        "schema_version": "1.0",
        "benchmark_commit": "synthetic-fixture",
        "version": "early",
        "tools": [tool("read", "Read a value.")],
    }
    target = copy.deepcopy(old)
    target["version"] = "late"
    target["tools"][0]["version"] = "late"
    target["tools"][0]["parameters"]["properties"]["strict"] = {"type": "boolean"}
    target["tools"][0]["parameters"]["required"].append("strict")
    install_llm(monkeypatch, lambda _: pytest.fail("Program-complete metadata was sent to LLM"))
    result = adapt_result(old, target, ctx())
    assert result["knowledge"]["tools"][0]["parameters"] == target["tools"][0]["parameters"]
    assert result["cost"]["calls"] == result["cost"]["input_utf8_bytes"] == 0


def test_implicit_dependency_found_without_full_schema(catalogs, monkeypatch):
    requests = install_llm(monkeypatch)
    result = adapt_result(*catalogs, ctx())
    screen, local = requests
    assert screen["phase"] == "scope_screen"
    assert {r["tool_id"] for r in screen["directory"]} == {"server::display", "server::unchanged"}
    assert all(set(r) == {"tool_id", "description", "usage_rules"} for r in screen["directory"])
    assert "knowledge_index" not in screen and "knowledge_index" not in local
    assert [r["tool_id"] for r in local["records"]] == ["server::display"]
    assert "old_record" not in json.dumps(local) and "patched_record" not in json.dumps(local)
    assert "Unverified LLM guidance" in result["knowledge"]["tools"][1]["usage_rules"][0]
    assert result["knowledge"]["tools"][2] == catalogs[0]["tools"][2]


def test_program_explicit_dependency_not_reclassified_by_screen(catalogs, monkeypatch):
    old, target = catalogs
    old["tools"][1]["usage_rules"] = ["Send fetch_balance output directly to display."]
    requests = install_llm(monkeypatch)
    result = adapt_result(old, target, ctx())
    assert result["audit"]["scope_plan"]["program_semantic_tool_ids"] == ["server::display"]
    assert [r["tool_id"] for r in requests[0]["directory"]] == ["server::unchanged"]
    assert requests[0]["program_context"][0]["tool_id"] == "server::display"
    assert result["audit"]["reviewed_tool_ids"] == ["server::display"]


def test_uncertainty_gets_one_local_review_not_repeated_expansion(catalogs, monkeypatch):
    def model(payload):
        data = reply(payload, action="unresolved")
        if payload["phase"] == "scope_screen":
            data["candidates"][0]["classification"] = "uncertain"
        return data

    requests = install_llm(monkeypatch, model)
    result = adapt_result(*catalogs, ctx())
    assert [p["phase"] for p in requests] == ["scope_screen", "local_semantic_review"]
    assert result["audit"]["unresolved_items"][0]["tool_id"] == "server::display"
    assert result["knowledge"]["tools"][1]["usage_rules"][0].startswith("Unknown semantic impact")


@pytest.mark.parametrize(
    "bad", ["missing", "duplicate", "unknown", "program_complete", "bad_basis", "bad_class"]
)
def test_invalid_scope_never_silently_passes(catalogs, monkeypatch, bad):
    def model(payload):
        data = reply(payload)
        if payload["phase"] != "scope_screen":
            return data
        if bad == "missing":
            data["screened_tool_ids"].pop()
        elif bad == "duplicate":
            data["candidates"].append(copy.deepcopy(data["candidates"][0]))
        elif bad == "unknown":
            data["candidates"][0]["tool_id"] = "other::invented"
        elif bad == "program_complete":
            data["candidates"][0]["tool_id"] = "server::fetch_balance"
        elif bad == "bad_basis":
            data["candidates"][0]["basis"] = ["invented"]
        else:
            data["candidates"][0]["classification"] = "known_safe"
        return data

    install_llm(monkeypatch, model)
    with pytest.raises(HybridPatchError):
        adapt_result(*catalogs, ctx())


def test_empty_discovery_preserves_rules_and_exposes_recall_limit(catalogs, monkeypatch):
    # A model can still miss a true implicit link. The audit must not label its
    # negative screen as a full semantic proof or secretly run another screen.
    def model(payload):
        assert payload["phase"] == "scope_screen"
        return {"screened_tool_ids": [r["tool_id"] for r in payload["directory"]], "candidates": []}

    requests = install_llm(monkeypatch, model)
    result = adapt_result(*catalogs, ctx())
    assert len(requests) == 1
    assert result["audit"]["reviewed_tool_ids"] == []
    assert result["audit"]["validation"]["semantic_entailment_proven"] is False
    assert result["knowledge"]["tools"][1]["usage_rules"] == catalogs[0]["tools"][1]["usage_rules"]


def test_discovered_candidates_all_reviewed_once_across_batches(catalogs, monkeypatch):
    old, target = catalogs
    old["tools"][2]["usage_rules"] = ["Use fetch_balance as the measurement source."]
    target["tools"][2]["usage_rules"] = []
    requests = install_llm(monkeypatch)
    result = adapt_result(old, target, ctx(patch_budget={"review_batch_size": 1}))
    reviewed = result["audit"]["reviewed_tool_ids"]
    assert reviewed == ["server::display", "server::unchanged"]
    assert len(reviewed) == len(set(reviewed))
    assert len(requests) == 3


def test_scope_validator_handles_bad_receipt_types():
    with pytest.raises(ValueError):
        screen_candidates({"screened_tool_ids": [{}], "candidates": []}, {"a"}, {})


def test_arbitrary_record_labels_never_enter_model_payload(catalogs, monkeypatch):
    old, target = catalogs
    for catalog in (old, target):
        for record in catalog["tools"]:
            record["benchmark_answer"] = "FORBIDDEN-ANSWER-MARKER"
    requests = install_llm(monkeypatch)
    adapt_result(old, target, ctx())
    assert "FORBIDDEN-ANSWER-MARKER" not in json.dumps(requests)


@pytest.mark.parametrize("retain_old", [False, True])
def test_acceptance_checks_retained_entries_not_negated_quotation(
    catalogs, monkeypatch, retain_old
):
    from scripts.measure_v5_scope import semantic_checks

    def model(payload):
        result = reply(payload)
        if payload["phase"] == "local_semantic_review":
            row = result["decisions"][0]
            row["retain_rule_indices"] = [0] if retain_old else []
            row["rules"][0].update(
                kind="conflict",
                text="Passing directly without conversion is unsafe; do not follow the obsolete rule.",
            )
        return result

    install_llm(monkeypatch, model)
    result = adapt_result(*catalogs, ctx())
    assert semantic_checks(result, *catalogs)["obsolete_direct_rule_withdrawn"] is not retain_old

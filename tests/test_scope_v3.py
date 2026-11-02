"""Independent V3 scope failures, quote gates and protected metadata invariants."""

import copy
import json

import pytest
from test_hybrid_selective import catalogs as catalogs
from test_hybrid_selective import evidence, response, tool

from integration import baselines as provider
from pe6203.capability import adapt_result as public_v3
from pe6203.hybrid_selective import HybridPatchError
from pe6203.scoped_selective_v3 import adapt_result


def context(**kwargs):
    return {"updater": {"allow_metadata_api": True}, **kwargs}


def reply(payload):
    if payload["phase"] == "scope_screen":
        return {
            "screened_tool_ids": [r["tool_id"] for r in payload["directory"]],
            "candidates": [
                {
                    "tool_id": "server::display",
                    "classification": "potential_impact",
                    "basis": ["c1"],
                    "reason": "The balance source changed units.",
                }
            ],
        }
    return {
        "decisions": [
            {
                "tool_id": r["tool_id"],
                "action": "update",
                "reason": "Remove the obsolete direct-pass rule.",
                "basis": ["c1"],
                "evidence": evidence(),
                "usage_rules": [
                    "Convert the supplied amount from cents to dollars by dividing by 100 before display."
                ],
            }
            for r in payload["records"]
        ]
    }


def install(monkeypatch, model=reply):
    requests = []

    def complete(messages, settings):
        payload = json.loads(messages[-1]["content"])
        requests.append(payload)
        return response(model(payload))

    monkeypatch.setattr(provider, "_request_completion", complete)
    return requests


def test_implicit_candidate_review_and_edit_in_one_call(catalogs, monkeypatch):
    requests = install(monkeypatch)
    result = adapt_result(*catalogs, context())
    assert [p["phase"] for p in requests] == ["scope_screen", "local_semantic_review"]
    assert result["audit"]["reviewed_tool_ids"] == ["server::display"]
    assert result["knowledge"]["tools"][1]["usage_rules"] == [
        "Convert the supplied amount from cents to dollars by dividing by 100 before display."
    ]
    assert result["knowledge"]["tools"][2] == catalogs[0]["tools"][2]
    assert result["knowledge"]["tools"][0]["description"] == catalogs[1]["tools"][0]["description"]
    assert "knowledge_index" not in json.dumps(requests)
    assert "patched_record" not in json.dumps(requests) and "target_record" not in json.dumps(
        requests
    )
    assert result["cost"]["input_utf8_bytes"] > 0


def test_program_complete_parameter_change_needs_zero_model_calls(monkeypatch):
    old = {
        "schema_version": "1.0",
        "benchmark_commit": "synthetic-fixture",
        "version": "early",
        "tools": [tool("read", "Read a value.")],
    }
    target = copy.deepcopy(old)
    target["version"] = "late"
    t = target["tools"][0]
    t["version"] = "late"
    t["parameters"]["properties"]["strict"] = {"type": "boolean"}
    t["parameters"]["required"].append("strict")
    install(monkeypatch, lambda _: pytest.fail("Program-complete tool sent to model"))
    result = adapt_result(old, target, context())
    assert result["cost"]["calls"] == result["cost"]["prompt_tokens"] == 0
    assert result["knowledge"]["tools"][0]["parameters"] == t["parameters"]


def test_program_seed_is_not_reclassified_and_is_reviewed_once(catalogs, monkeypatch):
    old, target = catalogs
    old["tools"][1]["usage_rules"] = ["Send fetch_balance output directly to display."]

    def model(payload):
        if payload["phase"] == "scope_screen":
            assert [r["tool_id"] for r in payload["directory"]] == ["server::unchanged"]
            return {"screened_tool_ids": ["server::unchanged"], "candidates": []}
        return {
            "decisions": [
                {
                    "tool_id": "server::display",
                    "action": "keep",
                    "reason": "Retained for this test.",
                    "basis": [],
                    "evidence": [],
                }
            ]
        }

    requests = install(monkeypatch, model)
    result = adapt_result(old, target, context())
    assert result["audit"]["scope_plan"]["program_semantic_tool_ids"] == ["server::display"]
    assert result["audit"]["reviewed_tool_ids"] == ["server::display"] and len(requests) == 2


@pytest.mark.parametrize(
    "bad",
    [
        "missing_coverage",
        "duplicate_coverage",
        "unknown_candidate",
        "completed_candidate",
        "unknown_basis",
        "invalid_class",
        "duplicate_candidate",
    ],
)
def test_bad_screen_fails_closed(catalogs, monkeypatch, bad):
    def model(payload):
        data = reply(payload)
        if payload["phase"] == "scope_screen":
            if bad == "missing_coverage":
                data["screened_tool_ids"].pop()
            elif bad == "duplicate_coverage":
                data["screened_tool_ids"].append(data["screened_tool_ids"][0])
            elif bad == "unknown_candidate":
                data["candidates"][0]["tool_id"] = "server::invented"
            elif bad == "completed_candidate":
                data["candidates"][0]["tool_id"] = "server::fetch_balance"
            elif bad == "unknown_basis":
                data["candidates"][0]["basis"] = ["nonexistent"]
            elif bad == "invalid_class":
                data["candidates"][0]["classification"] = "proven_unaffected"
            else:
                data["candidates"].append(copy.deepcopy(data["candidates"][0]))
        return data

    install(monkeypatch, model)
    with pytest.raises(HybridPatchError):
        adapt_result(*catalogs, context())


@pytest.mark.parametrize(
    "bad",
    [
        "metadata_edit",
        "invented_quote",
        "missing_local",
        "duplicate_local",
        "unresolved",
        "oversized_rules",
        "keep_with_rules",
    ],
)
def test_bad_local_never_publishes_a_snapshot(catalogs, monkeypatch, bad):
    def model(payload):
        data = reply(payload)
        if payload["phase"] == "local_semantic_review":
            row = data["decisions"][0]
            if bad == "metadata_edit":
                row["description"] = "Model cannot edit authoritative metadata"
            elif bad == "invented_quote":
                row["evidence"][0]["quote"] = "Fabricated guarantee"
            elif bad == "missing_local":
                data["decisions"] = []
            elif bad == "duplicate_local":
                data["decisions"].append(copy.deepcopy(row))
            elif bad == "unresolved":
                row["action"] = "unresolved"
                row.pop("usage_rules")
            elif bad == "oversized_rules":
                row["usage_rules"] = ["x" * 1201]
            else:
                row["action"] = "keep"
        return data

    install(monkeypatch, model)
    with pytest.raises(HybridPatchError):
        adapt_result(*catalogs, context())


def test_negative_screen_is_not_a_recall_proof(catalogs, monkeypatch):
    def model(payload):
        return {"screened_tool_ids": [r["tool_id"] for r in payload["directory"]], "candidates": []}

    requests = install(monkeypatch, model)
    result = adapt_result(*catalogs, context())
    assert len(requests) == 1 and result["audit"]["reviewed_tool_ids"] == []
    assert result["audit"]["validation"]["hidden_dependency_recall_proven"] is False
    assert result["knowledge"]["tools"][1]["usage_rules"] == catalogs[0]["tools"][1]["usage_rules"]


def test_oversized_input_is_rejected_without_truncation(catalogs, monkeypatch):
    requests = install(monkeypatch)
    with pytest.raises(HybridPatchError, match="budget"):
        adapt_result(*catalogs, context(patch_budget={"max_request_chars": 1000}))
    assert requests == []


def test_arbitrary_labels_and_capability_bundle_do_not_enter_semantic_model(catalogs, monkeypatch):
    for catalog in catalogs:
        for t in catalog["tools"]:
            t["benchmark_answer"] = "FORBIDDEN-ANSWER-MARKER"
    requests = install(monkeypatch)
    result = public_v3(
        *catalogs, context(capability_evidence={"version": "capability-evidence-v1", "entries": []})
    )
    assert "FORBIDDEN-ANSWER-MARKER" not in json.dumps(requests)
    assert "capability_evidence" not in json.dumps(requests)
    assert result["audit"]["updater_core_version"] == "hybrid_v3_program_first_v1"
    assert all(
        t["capability_boundary"]["status"] == "unresolved_no_evidence"
        for t in result["knowledge"]["tools"]
    )


def test_budget_cannot_drop_program_seed(catalogs, monkeypatch):
    old, target = catalogs
    old["tools"][1]["usage_rules"] = ["Use fetch_balance output directly."]
    requests = install(monkeypatch)
    with pytest.raises(HybridPatchError, match="Budget"):
        adapt_result(old, target, context(patch_budget={"max_calls": 1}))
    assert not requests


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Convert the balance service result from cents to dollars before display.", True),
        ("The service returns cents; convert the result to dollars before passing it.", True),
        ("Convert a cents balance from the balance service to dollars.", True),
        ("Convert dollars to cents before display.", False),
        ("Pass the balance unchanged.", False),
    ],
)
def test_conversion_checker_accepts_units_without_requiring_numeral(text, expected):
    from scripts.measure_v3_scope import conversion_wording

    assert conversion_wording([text]) is expected


def test_checker_never_accepts_retained_obsolete_rule():
    from scripts.measure_v3_scope import NEW_RULE, RULE, conversion_wording

    assert not conversion_wording([RULE, NEW_RULE])


def test_checker_allows_changed_source_to_document_its_new_schema():
    from scripts.measure_v3_scope import catalogs as measure_catalogs
    from scripts.measure_v3_scope import checks

    old, target, bundle = measure_catalogs(1, program_only=True)
    result = public_v3(old, target, context(capability_evidence=bundle))
    result["knowledge"]["tools"][0]["usage_rules"] = [
        "Both amount and strict are required by the target schema."
    ]
    assert all(checks(result, old, target, True).values())

"""Synthetic contract/regression tests. Model responses are explicit test doubles.

These test implementation behavior, not real LLM reasoning or benchmark scores.
"""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from integration import baselines as provider
from pe6203.baselines import adapt, write_adaptation
from pe6203.hybrid_selective import HybridPatchError, adapt_result
from pe6203.runner import prepare_tools


def tool(name, description, rules=None):
    return {
        "tool_id": "server::" + name,
        "server_id": "server",
        "name": name,
        "version": "early",
        "description": description,
        "parameters": {
            "type": "object",
            "properties": {"amount": {"type": "number"}},
            "required": ["amount"],
            "additionalProperties": False,
        },
        "output_schema": None,
        "usage_rules": rules or [],
        "routing": {"server_id": "server", "tool_name": name},
    }


@pytest.fixture
def catalogs():
    old = {
        "schema_version": "1.0",
        "benchmark_commit": "synthetic-fixture",
        "version": "early",
        "tools": [
            tool("fetch_balance", "Returns the account balance for the display panel in dollars."),
            tool(
                "display",
                "Displays the account balance supplied by the balance service. The amount input is in dollars.",
                ["Pass the balance service result directly as amount without conversion."],
            ),
            tool(
                "unchanged",
                "Stores unrelated numeric measurements.",
                ["Preserve the original value."],
            ),
        ],
    }
    target = copy.deepcopy(old)
    target["version"] = "late"
    for t in target["tools"]:
        t["version"] = "late"
        t["usage_rules"] = []  # tools/list does not supply our learned usage rules
    target["tools"][0]["description"] = (
        "Returns the account balance for the display panel in cents."
    )
    return old, target


def evidence():
    return [
        {
            "tool_id": "server::fetch_balance",
            "side": "target",
            "field": "description",
            "quote": "Returns the account balance for the display panel in cents.",
        },
        {
            "tool_id": "server::display",
            "side": "old",
            "field": "usage_rules",
            "quote": "Pass the balance service result directly as amount without conversion.",
        },
    ]


def reply(payload):
    if "candidates" in payload:
        decisions = []
        for record in payload["candidates"]:
            identity = record["tool_id"]
            affected = identity == "server::display"
            decisions.append(
                {
                    "tool_id": identity,
                    "action": "update" if affected else "keep",
                    "reason": "Input units changed" if affected else "No rule change needed",
                    "basis": ["c1"] if affected else [],
                    "evidence": evidence() if affected else [],
                }
            )
        return {"decisions": decisions}
    return {
        "patches": [
            {
                "tool_id": "server::display",
                "usage_rules": [
                    "Convert the supplied amount from cents to dollars by dividing by 100 before display."
                ],
                "reason": "Display expects dollars but the source now returns cents",
                "basis": ["c1"],
                "evidence": evidence(),
                "unresolved": False,
            }
        ]
    }


def response(payload, *, usage=True):
    return {
        "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(payload)}}],
        **(
            {"usage": {"prompt_tokens": 10, "completion_tokens": 20, "cost": 0.001}}
            if usage
            else {}
        ),
    }


@pytest.fixture
def llm(monkeypatch):
    requests = []

    def complete(messages, settings):
        assert settings["allow_metadata_api"] is True
        requests.append(copy.deepcopy(messages))
        return response(reply(json.loads(messages[-1]["content"])))

    monkeypatch.setattr(provider, "_request_completion", complete)
    return requests


def context(**kwargs):
    return {"updater": {"allow_metadata_api": True}, **kwargs}


def test_public_strategy_uses_all_four_stages_and_finds_implicit_link(catalogs, llm):
    old, target = catalogs
    result = adapt_result(old, target, context())
    audit = result["audit"]
    assert [s["stage"] for s in audit["stages"]] == [
        "deterministic_diff",
        "semantic_review",
        "semantic_patch",
        "program_validation",
    ]
    assert audit["deterministic_impacted"] == ["server::fetch_balance"]
    assert audit["semantic_impacted"] == ["server::display"]
    assert set(audit["reviewed_tool_ids"]) == {t["tool_id"] for t in old["tools"]}
    assert result["knowledge"]["tools"][1]["usage_rules"] != old["tools"][1]["usage_rules"]
    assert result["knowledge"]["tools"][2] == old["tools"][2]
    knowledge, _, cost = adapt(old, target, "selective_patch", context())
    assert knowledge == result["knowledge"]
    assert cost["method"] == "hybrid_selective_patch_v2" and cost["calls"] == 2
    assert cost["usd"] == 0.002 and cost["total_tokens"] == 60
    assert len(llm) == 4
    prepare_tools(knowledge["tools"], "selective_patch")
    assert old == catalogs[0] and target == catalogs[1]


def test_multibatch_review_does_not_skip_unchanged_records(catalogs, llm):
    result = adapt_result(*catalogs, context(patch_budget={"review_batch_size": 1}))
    assert result["cost"]["calls"] == 4
    assert [a["phase"] for a in result["audit"]["attempts"]] == [
        "semantic_review",
        "semantic_review",
        "semantic_review",
        "semantic_patch",
    ]


def test_targeted_required_argument_and_retention_regressions(catalogs, llm):
    old, target = catalogs
    target["tools"][0]["parameters"]["properties"]["currency"] = {"type": "string"}
    target["tools"][0]["parameters"]["required"].append("currency")
    cases = [
        {"tool_id": "server::fetch_balance", "arguments": {"amount": 100}, "expected_valid": False},
        {
            "tool_id": "server::fetch_balance",
            "arguments": {"amount": 100, "currency": "USD"},
            "expected_valid": True,
        },
        {"tool_id": "server::unchanged", "arguments": {"amount": 100}, "expected_valid": True},
    ]
    result = adapt_result(old, target, context(validation_cases=cases))
    assert all(c["passed"] for c in result["audit"]["validation"]["argument_cases"])
    assert result["knowledge"]["tools"][0]["parameters"] == target["tools"][0]["parameters"]


def test_regression_failure_prevents_publishing_knowledge(tmp_path, catalogs, llm):
    old, target = catalogs
    a, b = tmp_path / "old.json", tmp_path / "new.json"
    a.write_text(json.dumps(old))
    b.write_text(json.dumps(target))
    output = tmp_path / "failed"
    with pytest.raises(HybridPatchError, match="validation"):
        write_adaptation(
            a,
            b,
            "selective_patch",
            output,
            context(
                validation_cases=[
                    {"tool_id": "server::unchanged", "arguments": {}, "expected_valid": True}
                ]
            ),
        )
    assert not (output / "knowledge.json").exists()
    artifact = json.loads((output / "adaptation.json").read_text())
    assert artifact["status"] == "failed" and artifact["cost"]["calls"] == 2
    assert (output / "updater-audit.json").exists()


@pytest.mark.parametrize(
    "defect",
    [
        "missing_review",
        "duplicate_review",
        "foreign_review",
        "unresolved_review",
        "bad_basis",
        "fabricated_quote",
        "missing_record_evidence",
        "truncated",
        "invalid_json",
        "extra_metadata",
        "outside_patch",
        "missing_patch",
        "unresolved_patch",
        "blank_rule",
        "failed_provider",
        "unknown_usage",
    ],
)
def test_untrusted_or_failed_model_output_never_silently_falls_back(
    catalogs, monkeypatch, defect, tmp_path
):
    requests = []

    def complete(messages, settings):
        payload = json.loads(messages[-1]["content"])
        requests.append(payload)
        if defect == "failed_provider":
            raise RuntimeError("sensitive-provider-detail")
        data = reply(payload)
        if "decisions" in data:
            rows = data["decisions"]
            changed = next(d for d in rows if d["action"] == "update")
            if defect == "missing_review":
                rows.pop()
            if defect == "duplicate_review":
                rows.append(copy.deepcopy(rows[0]))
            if defect == "foreign_review":
                rows[0]["tool_id"] = "server::invented"
            if defect == "unresolved_review":
                changed["action"] = "unresolved"
            if defect == "bad_basis":
                changed["basis"] = ["fake-change"]
            if defect == "fabricated_quote":
                changed["evidence"][0]["quote"] = "not in metadata"
            if defect == "missing_record_evidence":
                changed["evidence"].pop()
        else:
            patch = data["patches"][0]
            if defect == "extra_metadata":
                patch["parameters"] = {"type": "object"}
            if defect == "outside_patch":
                patch["tool_id"] = "server::unchanged"
            if defect == "missing_patch":
                data["patches"] = []
            if defect == "unresolved_patch":
                patch["unresolved"] = True
            if defect == "blank_rule":
                patch["usage_rules"] = [""]
        result = response(data, usage=defect != "unknown_usage")
        if defect == "truncated":
            result["choices"][0]["finish_reason"] = "length"
        if defect == "invalid_json":
            result["choices"][0]["message"]["content"] = "broken"
        return result

    monkeypatch.setattr(provider, "_request_completion", complete)
    config = context(audit_path=str(tmp_path / "audit.json"))
    if defect == "unknown_usage":
        result = adapt_result(*catalogs, config)
        assert result["cost"]["usd"] is None and result["cost"]["total_tokens"] is None
        assert result["cost"]["unknown_charge_requests"] == 2
    else:
        with pytest.raises(HybridPatchError) as caught:
            adapt_result(*catalogs, config)
        assert caught.value.audit["status"] == "failed"
        if defect == "failed_provider":
            assert caught.value.audit["cost"]["usd"] is None
            assert "sensitive-provider-detail" not in json.dumps(caught.value.audit)
    assert (tmp_path / "audit.json").exists()


@pytest.mark.parametrize(
    "config",
    [
        {"patch_budget": {"max_calls": 1}},
        {"patch_budget": {"max_request_chars": 1000}},
        {"updater": {"allow_metadata_api": False}},
    ],
)
def test_incomplete_budget_and_missing_opt_in_fail_before_requests(catalogs, llm, config):
    with pytest.raises(HybridPatchError):
        adapt_result(*catalogs, {**context(), **config})
    assert llm == []


def test_keep_decisions_do_not_invent_rules(catalogs, monkeypatch):
    def keep(messages, settings):
        data = reply(json.loads(messages[-1]["content"]))
        for row in data["decisions"]:
            row.update(action="keep", basis=[], evidence=[], reason="No rule edit needed")
        return response(data)

    monkeypatch.setattr(provider, "_request_completion", keep)
    result = adapt_result(*catalogs, context())
    assert result["cost"]["calls"] == 1
    assert result["knowledge"]["tools"][1] == catalogs[0]["tools"][1]
    assert result["audit"]["stages"][2]["edited_records"] == 0


def test_no_change_and_early_use_no_llm(catalogs, llm):
    old, _ = catalogs
    for stage in ("early", "late"):
        same = copy.deepcopy(old)
        same["version"] = stage
        for t in same["tools"]:
            t["version"] = stage
        result = adapt_result(old, same)
        assert result["knowledge"] == old and result["cost"]["calls"] == 0
        assert result["audit"]["stages"][1]["status"] == "skipped_no_metadata_change"
    assert llm == []


def test_legacy_mode_remains_explicit_and_unchanged(catalogs, llm):
    _, _, cost = adapt(*catalogs, "selective_patch", {"selective_mode": "deterministic_v1"})
    assert cost["method"] == "deterministic_diff_selective_patch"
    assert llm == []


def test_no_task_or_scoring_context_is_accepted(catalogs):
    with pytest.raises(ValueError, match="forbidden"):
        adapt_result(*catalogs, context(task_answer="not allowed"))


def test_extra_record_labels_are_not_sent_to_model(catalogs, llm):
    for catalog in catalogs:
        catalog["tools"][0]["answer"] = "PRIVATE_REFERENCE_ANSWER"
        catalog["tools"][1]["eval_result"] = "PRIVATE_JUDGE_RESULT"
    adapt_result(*catalogs, context())
    sent = json.dumps(llm)
    assert "PRIVATE_REFERENCE_ANSWER" not in sent and "PRIVATE_JUDGE_RESULT" not in sent


def test_recorded_live_requests_still_match_current_pipeline(monkeypatch):
    """Replay real responses only after exact prompt equality; no API requests."""
    root = Path(__file__).resolve().parents[1]
    saved = json.loads(
        (root / "results/qi-v2/live-smoke-02/adaptation/updater-audit.json").read_text()
    )
    remaining = list(saved["attempts"])

    def replay(messages, settings):
        attempt = remaining.pop(0)
        assert messages == attempt["request"]
        return copy.deepcopy(attempt["response"])

    monkeypatch.setattr(provider, "_request_completion", replay)
    old = json.loads((root / "examples/qi-v2/early.json").read_text())
    target = json.loads((root / "examples/qi-v2/late.json").read_text())
    cases = json.loads((root / "examples/qi-v2/validation-cases.json").read_text())
    result = adapt_result(
        old, target, context(validation_cases=cases, patch_budget={"max_calls": 2})
    )
    assert not remaining and result["audit"]["status"] == "validated"


def test_artifact_records_full_audit_and_preserves_inputs(tmp_path, catalogs, llm):
    original = copy.deepcopy(catalogs)
    a, b = tmp_path / "old.json", tmp_path / "new.json"
    a.write_text(json.dumps(catalogs[0]))
    b.write_text(json.dumps(catalogs[1]))
    artifact = write_adaptation(a, b, "selective_patch", tmp_path / "accepted", context())
    assert artifact["pipeline_version"] == "hybrid_v2" and artifact["formal_llm_rewrite"]
    assert artifact["status"] == "validated" and len(artifact["stages"]) == 4
    assert len(artifact["output"]["knowledge_file_sha256"]) == 64
    assert catalogs == original
    with pytest.raises(FileExistsError):
        write_adaptation(a, b, "selective_patch", tmp_path / "accepted", context())


def test_input_hashes_describe_consumed_bytes_even_if_files_change(tmp_path, catalogs, monkeypatch):
    a, b = tmp_path / "old.json", tmp_path / "target.json"
    a.write_text(json.dumps(catalogs[0]))
    b.write_text(json.dumps(catalogs[1]))
    original_hash = hashlib.sha256(b.read_bytes()).hexdigest()

    def complete(messages, settings):
        b.write_text("{}")  # another process changes the file during the request
        return response(reply(json.loads(messages[-1]["content"])))

    monkeypatch.setattr(provider, "_request_completion", complete)
    artifact = write_adaptation(a, b, "selective_patch", tmp_path / "accepted", context())
    assert artifact["target_stage"] == "late"
    assert artifact["input"]["target_metadata_file_sha256"] == original_hash

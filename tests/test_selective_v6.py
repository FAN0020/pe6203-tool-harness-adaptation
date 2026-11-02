"""Synthetic adversarial contracts; real catalog packing has its own receipt."""

import copy
import json

import pytest
from test_hybrid_selective import catalogs as catalogs
from test_hybrid_selective import response
from test_selective_v5 import bundle

from integration import baselines as provider
from pe6203 import execution_v6
from pe6203.baselines import adapt, write_adaptation
from pe6203.benchmark import digest, read_json, write_json
from pe6203.payload_v6 import detail_packet, prepare, screening_packet, selections
from pe6203.selective_v6 import HybridPatchError, adapt_result


def context(**extra):
    return {"selective_mode": "hybrid_v6", "updater": {"allow_metadata_api": True}, **extra}


def reply(packet):
    if packet["phase"] == "v6_global_screen":
        return {
            "covered_tool_ids": [r["tool_id"] for r in packet["catalog"]],
            "candidates": [
                {
                    "tool_id": "server::display",
                    "category": "potential",
                    "reason": "Balance units changed",
                    "basis": [packet["changes"][0]["change_id"]],
                    "fields": [],
                }
            ],
        }
    refs = list(packet["evidence_registry"])
    return {
        "patches": [
            {
                "tool_id": row["tool_id"],
                "retain_rule_indices": [],
                "rules": [
                    {
                        "kind": "guidance",
                        "text": "Convert cents to dollars before display.",
                        "evidence_ids": refs,
                    }
                ],
                "reason": "Units changed",
                "basis": row["basis"],
                "evidence_ids": refs,
            }
            for row in packet["selected"]
        ]
    }


def model(monkeypatch, change=lambda p, r: r):
    requests = []

    def call(messages, _settings):
        packet = json.loads(messages[-1]["content"])
        requests.append(packet)
        return response(change(packet, reply(packet)))

    monkeypatch.setattr(provider, "_request_completion", call)
    return requests


def test_global_once_local_only_and_metadata_program_owned(catalogs, monkeypatch):
    requests = model(monkeypatch)
    old, target = copy.deepcopy(catalogs)
    result = adapt_result(old, target, context())
    assert len(requests) == 2
    screen, detail = requests
    assert set(screen["catalog"][0]) == {"tool_id", "purpose", "rules"}
    assert "knowledge_index" not in detail and "catalog" not in detail
    assert {r["tool_id"] for r in detail["selected"]} == {"server::display"}
    assert {r["tool_id"] for r in detail["evidence_registry"].values()} == {
        "server::display",
        "server::fetch_balance",
    }
    assert result["knowledge"]["tools"][0]["description"] == target["tools"][0]["description"]
    assert result["knowledge"]["tools"][2] == old["tools"][2]
    assert old == catalogs[0] and target == catalogs[1]
    assert result["cost"]["calls"] == 2
    assert result["cost"]["request_chars"] > 0
    assert result["audit"]["acceptance"]["current_task_feedback_updates_knowledge"] is False


def test_missing_screen_coverage_never_publishes(catalogs, monkeypatch, tmp_path):
    model(monkeypatch, lambda p, r: {**r, "covered_tool_ids": []} if "catalog" in p else r)
    old, target = catalogs
    write_json(tmp_path / "old.json", old)
    write_json(tmp_path / "new.json", target)
    with pytest.raises(HybridPatchError, match="coverage"):
        write_adaptation(
            tmp_path / "old.json",
            tmp_path / "new.json",
            "selective_patch",
            tmp_path / "out",
            context(),
        )
    assert not (tmp_path / "out/knowledge.json").exists()
    assert read_json(tmp_path / "out/updater-audit.json")["cost"]["calls"] == 1


def test_program_mandatory_union_and_transitive_description_dependency(catalogs):
    old, target = catalogs
    old["tools"][1]["usage_rules"] = ["Use fetch_balance before display"]
    old["tools"][2]["usage_rules"] = ["Use display output"]
    state = prepare(old, target)
    rows = selections({"covered_tool_ids": list(state["records"]), "candidates": []}, state)
    assert {r["tool_id"] for r in rows} == {"server::display", "server::unchanged"}
    assert all(r["basis"] for r in rows)


def test_no_change_no_anomaly_zero_calls_and_baselines_unchanged(catalogs, monkeypatch, tmp_path):
    old, _ = catalogs
    model(monkeypatch, lambda *_: pytest.fail("No API needed"))
    # This independently collected finite check matches, so it alone does not
    # manufacture a change event or establish universal behavior.
    path = bundle(tmp_path, old, result={"isError": True})
    result = adapt_result(old, copy.deepcopy(old), context(evidence_bundle=str(path)))
    assert result["knowledge"] == old and result["cost"]["calls"] == 0
    assert adapt(old, old, "no_update", context())[0] == old
    assert adapt(old, old, "full_rewrite", context())[0] == old


def test_anomaly_is_required_but_raw_probe_absent_from_screen(catalogs, tmp_path):
    old, _ = catalogs
    state = prepare(old, old, bundle(tmp_path, old))
    packet = screening_packet(state)
    assert state["mandatory"] and packet["changes"][0]["event"] == "independent_anomaly"
    assert '"arguments":' not in json.dumps(packet) and '"result":' not in json.dumps(packet)


def test_precise_field_reads_and_scope_rejection(catalogs):
    old, target = catalogs
    state = prepare(old, target)
    row = reply(screening_packet(state))["candidates"][0]
    row["fields"] = [
        {
            "tool_id": "server::fetch_balance",
            "side": "target",
            "field": "parameters",
            "pointer": "/properties/amount/type",
        }
    ]
    packet, sources = detail_packet(state, [row])
    fragment = next(s for s in sources.values() if s["field"] == "parameters")
    assert fragment["value"] == "number"
    assert all(
        value != target["tools"][0]["parameters"] for value in packet["content_pool"].values()
    )
    row["fields"][0]["tool_id"] = "server::unchanged"
    with pytest.raises(ValueError, match="scope"):
        detail_packet(state, [row])


def test_whole_field_selector_root_normalization_is_lossless(catalogs):
    state = prepare(*catalogs)
    row = reply(screening_packet(state))["candidates"][0]
    before, sources = detail_packet(state, [row])
    row["fields"] = [{"tool_id": "server::fetch_balance", "side": "target", "field": "description"}]
    after, extra = detail_packet(state, [row])
    assert after == before and extra == sources  # Already supplied; not new evidence.
    row["fields"][0]["field"] = "parameters"
    whole, _ = detail_packet(state, [row])
    assert catalogs[1]["tools"][0]["parameters"] in whole["content_pool"].values()
    row["fields"][0]["unknown_key"] = "do not silently discard"
    with pytest.raises(ValueError, match="Only tool"):
        detail_packet(state, [row])


def test_diagnosis_uses_actual_call_events_and_preserves_uncertainty(catalogs):
    from pe6203.runner import prepare_tools

    old, _ = catalogs
    tools, _ = prepare_tools(old["tools"], "selective_patch", "namespaced")
    events = [
        {"type": "agent_response"},
        {
            "type": "tool_result",
            "call": {"function": {"name": tools[0]["function"]["name"], "arguments": "{}"}},
            "result": {"isError": True},
        },
    ]
    freeze = {"knowledge_sha256": digest(old)}
    diagnosis = execution_v6.diagnose(
        freeze, old, old["tools"], events, {"execution_status": "failed"}
    )
    assert diagnosis["actual_tool_calls_observed"] == 1
    assert diagnosis["trace_events_observed"] == 2
    assert diagnosis["findings"][0]["route"] == "action_or_artifact"
    assert not diagnosis["knowledge_modified"]
    success = execution_v6.diagnose(
        freeze, old, old["tools"], [], {"execution_status": "completed"}
    )
    assert success["findings"] == [] and success["status"] == "no_failure_detected"


@pytest.mark.parametrize("corrupt", ["invent_id", "metadata", "omit", "guarantee"])
def test_invalid_patches_bounded_one_revision_keep_costs(catalogs, monkeypatch, corrupt):
    def alter(packet, result):
        if "patches" in result:
            if corrupt == "invent_id":
                result["patches"][0]["evidence_ids"] = ["invented"]
            elif corrupt == "metadata":
                result["patches"][0]["parameters"] = {}
            elif corrupt == "omit":
                result["patches"] = []
            else:
                result["patches"][0]["rules"][0]["kind"] = "behavior_guarantee"
        return result

    requests = model(monkeypatch, alter)
    with pytest.raises(HybridPatchError) as error:
        adapt_result(*catalogs, context())
    assert len(requests) == 3 and error.value.audit["cost"]["calls"] == 3
    assert len(error.value.audit["revision_errors"]) == 2
    assert error.value.audit["status"] == "failed"


def test_requested_evidence_has_one_bounded_followup(catalogs, monkeypatch):
    def alter(packet, result):
        if packet["phase"] == "v6_local_patch" and not any(
            e["field"] == "parameters" for e in packet["evidence_registry"].values()
        ):
            return {
                "need_evidence": [
                    {
                        "tool_id": "server::fetch_balance",
                        "side": "target",
                        "field": "parameters",
                        "pointer": "/required",
                    }
                ]
            }
        return result

    requests = model(monkeypatch, alter)
    result = adapt_result(*catalogs, context())
    assert len(requests) == result["cost"]["calls"] == 3
    assert "catalog" not in requests[-1]
    assert requests[-1]["content_pool"]


@pytest.mark.parametrize(
    "budget",
    [{"max_request_chars": 20}, {"max_usd": 0.000001}, {"max_total_estimated_input_tokens": 1}],
)
def test_preflight_prevents_spend_without_truncating(catalogs, monkeypatch, budget):
    requests = model(monkeypatch)
    with pytest.raises(HybridPatchError) as exc:
        adapt_result(*catalogs, context(patch_budget=budget))
    assert not requests and exc.value.audit["cost"]["calls"] == 0
    assert exc.value.audit["preflights"][0]["status"] == "blocked"


@pytest.mark.parametrize("forbidden", ["task", "answers", "judge_scores", "test_feedback"])
def test_task_feedback_cannot_enter_updater(catalogs, forbidden):
    with pytest.raises(ValueError, match="forbidden"):
        adapt_result(*catalogs, context(**{forbidden: "no"}))


def test_unknown_charge_blocks_next_request(catalogs, monkeypatch):
    def call(messages, _settings):
        result = response(reply(json.loads(messages[-1]["content"])))
        result["usage"].pop("cost", None)
        return result

    monkeypatch.setattr(provider, "_request_completion", call)
    with pytest.raises(HybridPatchError, match="Unknown prior charge") as exc:
        adapt_result(*catalogs, context())
    assert exc.value.audit["cost"]["unknown_charge_requests"] == 1


def test_freeze_checks_before_execution_and_diagnosis_nonmutating(catalogs, monkeypatch, tmp_path):
    model(monkeypatch)
    old, target = catalogs
    write_json(tmp_path / "old.json", old)
    write_json(tmp_path / "new.json", target)
    artifact = write_adaptation(
        tmp_path / "old.json",
        tmp_path / "new.json",
        "selective_patch",
        tmp_path / "adapt",
        context(),
    )
    write_json(tmp_path / "config.json", {})
    calls = []
    monkeypatch.setattr(execution_v6, "run", lambda *args: calls.append(args) or ({}, {}))
    args = (
        tmp_path,
        999,
        "late",
        0,
        tmp_path / "config.json",
        tmp_path / "adapt/adaptation.json",
        tmp_path / "run",
    )
    execution_v6.run_v6(*args, non_python_deliverable=True)
    freeze = read_json(tmp_path / "run-freeze.json")
    knowledge = read_json(tmp_path / "adapt/knowledge.json")
    assert freeze["knowledge_sha256"] == digest(knowledge)
    before = copy.deepcopy(knowledge)
    diagnosis = execution_v6.diagnose(freeze, knowledge, [], [], {"execution_status": "failed"})
    assert diagnosis["findings"][0]["route"] == "retrieval_or_injection"
    assert knowledge == before and not diagnosis["knowledge_modified"]
    write_json(tmp_path / "adapt/knowledge.json", old)
    with pytest.raises(ValueError, match="hash mismatch"):
        execution_v6.run_v6(*args, non_python_deliverable=True)
    assert len(calls) == 1 and artifact["acceptance_sha256"]

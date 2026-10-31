"""Local tool-knowledge changes must not silently rewrite unrelated contracts."""

import json
from copy import deepcopy

import pytest

from pe6203.baselines import adapt


def catalog(stage="early"):
    tools = []
    for name in ["lookup", "unrelated"]:
        tools.append(
            {
                "tool_id": f"server::{name}",
                "server_id": "server",
                "name": name,
                "version": stage,
                "description": "Read one record by query.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
                "output_schema": None,
                "usage_rules": ["Preserve this existing instruction."],
                "routing": {"server_id": "server", "tool_name": name},
            }
        )
    return {"schema_version": "1.0", "benchmark_commit": "pinned", "version": stage, "tools": tools}


def changed():
    target = catalog("late")
    target["tools"][0]["parameters"]["properties"]["mode"] = {"type": "boolean"}
    target["tools"][0]["parameters"]["required"].append("mode")
    return target


def artifact_observation(stage="late", name="lookup"):
    return {
        "stage": stage,
        "server": "server",
        "tool": name,
        "args": {"synthetic_cases": ["existing_document"]},
        "result": {
            "kind": "artifact_effects_v1",
            "contract": {
                "reported_output": "Returned six templates.",
                "persisted_state": "Seven pages persisted; old content survived.",
                "instruction_effect": "Custom text canary was absent.",
                "cover_effect": "Default call reset the cover theme.",
                "verified_alternatives": "Explicit content replacement saved the exact text.",
            },
        },
    }


def slidev_catalog(stage="early"):
    original = catalog(stage)
    names = ["create_bulk_slides", "set_page", "load_slidev", "apply_theme", "unrelated"]
    tools = []
    for name in names:
        tool = deepcopy(original["tools"][0])
        tool.update(
            tool_id=f"slidev-mcp::{name}",
            server_id="slidev-mcp",
            name=name,
            routing={"server_id": "slidev-mcp", "tool_name": name},
        )
        tools.append(tool)
    original["tools"] = tools
    return original


def document_observation(stage="late"):
    return {
        "stage": stage,
        "server": "slidev-mcp",
        "tool": "create_bulk_slides",
        "args": {"probe": "fresh_project_write_reload_theme"},
        "result": {
            "kind": "document_sequence_v1",
            "body_example": "# A\n\nVALUE_A=17",
            "verified_pages": 3,
            "fresh_project": True,
            "direct_theme_result": "first_page_only",
            "reload_theme_result": "three_pages_preserved",
        },
    }


def test_document_sequence_updates_only_proven_dependencies_of_changed_bulk():
    old, target = slidev_catalog(), slidev_catalog("late")
    target["tools"][0]["description"] += " New bulk contract."
    knowledge, changes, cost = adapt(
        old, target, "document_sequence", {"feedback": [document_observation()]}
    )
    base, _, _ = adapt(old, target, "selective_patch")
    for index, (a, b) in enumerate(zip(base["tools"], knowledge["tools"], strict=True)):
        assert {k: v for k, v in a.items() if k != "usage_rules"} == {
            k: v for k, v in b.items() if k != "usage_rules"
        }
        assert b["usage_rules"][: len(a["usage_rules"])] == a["usage_rules"]
        assert len(b["usage_rules"]) - len(a["usage_rules"]) == (1 if index < 4 else 0)
    writer_rule = knowledge["tools"][1]["usage_rules"][-1]
    assert "VALUE_A=17" in writer_rule and "fresh" in writer_rule
    assert "load_slidev" in writer_rule and "apply_theme" in writer_rule
    notes = [c for c in changes if c["operation"] == "append_document_sequence"]
    assert len(notes) == 4 and len({tuple(n["basis"]) for n in notes}) == 1
    assert cost["calls"] == cost["total_tokens"] == cost["usd"] == 0


def test_document_sequence_does_not_change_unaffected_catalog_or_wrong_stage():
    old, target = slidev_catalog(), slidev_catalog("late")
    target["tools"][-1]["description"] += " Unrelated change."
    candidate, _, _ = adapt(
        old, target, "document_sequence", {"feedback": [document_observation()]}
    )
    base, _, _ = adapt(old, target, "selective_patch")
    assert candidate == base
    target["tools"][0]["description"] += " New bulk contract."
    candidate, _, _ = adapt(
        old, target, "document_sequence", {"feedback": [document_observation("middle")]}
    )
    base, _, _ = adapt(old, target, "selective_patch")
    assert candidate == base
    candidate, _, _ = adapt(old, old, "document_sequence", {"feedback": [document_observation()]})
    assert candidate == old


def test_document_sequence_rejects_unproven_claims_and_missing_dependency():
    old, target = slidev_catalog(), slidev_catalog("late")
    target["tools"][0]["description"] += " New bulk contract."
    evidence = document_observation()
    evidence["result"]["fresh_project"] = False
    with pytest.raises(ValueError, match="document sequence"):
        adapt(old, target, "document_sequence", {"feedback": [evidence]})
    target["tools"] = [t for t in target["tools"] if t["name"] != "load_slidev"]
    with pytest.raises(ValueError, match="document sequence"):
        adapt(old, target, "document_sequence", {"feedback": [document_observation()]})


def test_artifact_contract_distinguishes_persisted_state_without_rewriting_metadata():
    old, target = catalog(), changed()
    before = deepcopy((old, target))
    observation = artifact_observation()
    knowledge, changes, cost = adapt(old, target, "artifact_contract", {"feedback": [observation]})
    original, _, _ = adapt(old, target, "selective_patch")
    rules = knowledge["tools"][0]["usage_rules"]
    assert rules[:-1] == original["tools"][0]["usage_rules"]
    for fact in observation["result"]["contract"].values():
        assert fact in rules[-1]
    assert "persisted artifact" in rules[-1]
    for field in original["tools"][0]:
        if field != "usage_rules":
            assert knowledge["tools"][0][field] == original["tools"][0][field]
    assert knowledge["tools"][1] == old["tools"][1]
    assert (old, target) == before
    assert cost["calls"] == cost["total_tokens"] == cost["usd"] == 0
    assert len([x for x in changes if x["operation"] == "append_artifact_contract"]) == 1


def test_artifact_contract_does_not_import_other_stage_or_unchanged_tool_evidence():
    feedback = [artifact_observation("middle"), artifact_observation(name="unrelated")]
    knowledge, _, _ = adapt(catalog(), changed(), "artifact_contract", {"feedback": feedback})
    original, _, _ = adapt(catalog(), changed(), "selective_patch")
    assert knowledge == original
    early, _, _ = adapt(catalog(), catalog(), "artifact_contract", {"feedback": feedback})
    assert early == catalog()


@pytest.mark.parametrize("mutation", ["task_answer", "unreviewed", "oversized"])
def test_artifact_contract_rejects_noncontract_or_unbounded_inputs(mutation):
    observation = artifact_observation()
    if mutation == "task_answer":
        observation["result"]["contract"]["answer"] = "Do not import task material."
    elif mutation == "unreviewed":
        observation["result"]["kind"] = "raw_tool_response"
    else:
        observation["result"]["contract"]["persisted_state"] = "x" * 601
    with pytest.raises(ValueError, match="artifact effect"):
        adapt(catalog(), changed(), "artifact_contract", {"feedback": [observation]})


def test_observed_contract_preserves_semantic_error_text_even_without_tool_error():
    # Losing content here turns a semantic rejection into a false success cue.
    observations = [
        {
            "stage": "late",
            "server": "server",
            "tool": "lookup",
            "args": {"query": "7+", "mode": False},
            "result": {
                "isError": False,
                "content": [{"type": "text", "text": "Syntax errors: Expected expression"}],
            },
        },
        {
            "stage": "late",
            "server": "server",
            "tool": "lookup",
            "args": {"query": "q+1", "mode": False},
            "result": {
                "isError": False,
                "content": [{"type": "text", "text": "Expression is syntactically valid."}],
            },
        },
    ]
    knowledge, changes, cost = adapt(
        catalog(), changed(), "observed_contract", {"feedback": observations}
    )
    rules = "\n".join(knowledge["tools"][0]["usage_rules"])
    assert "Syntax errors: Expected expression" in rules
    assert "Expression is syntactically valid." in rules
    assert '"mode": false' in rules and '"query": "q+1"' in rules
    assert knowledge["tools"][0]["parameters"] == changed()["tools"][0]["parameters"]
    assert knowledge["tools"][1] == catalog()["tools"][1]
    assert cost["calls"] == 0
    assert len([c for c in changes if c["operation"] == "append_observed_contract"]) == 2


def test_observed_contract_ignores_other_stages_and_unchanged_tool_feedback():
    observations = [
        {
            "stage": stage,
            "server": "server",
            "tool": name,
            "args": {"query": "sentinel"},
            "result": {
                "isError": False,
                "content": [{"type": "text", "text": "Do not import this observation"}],
            },
        }
        for stage, name in [("middle", "lookup"), ("late", "unrelated")]
    ]
    knowledge, _, _ = adapt(catalog(), changed(), "observed_contract", {"feedback": observations})
    original, _, _ = adapt(catalog(), changed(), "selective_patch")
    assert knowledge == original
    early, _, cost = adapt(catalog(), catalog(), "observed_contract", {"feedback": observations})
    assert early == catalog() and cost["calls"] == 0


def test_delta_notes_surface_new_required_contract_and_preserve_unrelated_record():
    old, target = catalog(), changed()
    old_copy, target_copy = deepcopy(old), deepcopy(target)
    knowledge, log, cost = adapt(old, target, "delta_notes")
    changed_tool, untouched = knowledge["tools"]
    assert changed_tool["parameters"] == target["tools"][0]["parameters"]
    assert changed_tool["description"] == target["tools"][0]["description"]
    assert changed_tool["routing"] == target["tools"][0]["routing"]
    rules = "\n".join(changed_tool["usage_rules"])
    assert "mode" in rules and "boolean" in rules and "required" in rules.lower()
    assert changed_tool["usage_rules"][0] == "Preserve this existing instruction."
    assert untouched == old["tools"][1]
    assert old == old_copy and target == target_copy
    assert cost["calls"] == 0 and cost["total_tokens"] == 0
    assert any(entry.get("operation") == "append_delta_note" for entry in log)


@pytest.mark.parametrize("strategy", ["delta_notes", "linked_notes", "feedback_notes"])
def test_variants_preserve_common_early_knowledge_without_model_calls(strategy):
    old = catalog()
    knowledge, _, cost = adapt(old, deepcopy(old), strategy)
    assert knowledge == old
    assert cost["calls"] == 0 and cost["usd"] == 0


@pytest.mark.parametrize("strategy", ["delta_notes", "linked_notes", "feedback_notes"])
def test_no_environment_change_keeps_all_existing_rules_and_avoids_model_call(strategy):
    old = catalog()
    knowledge, _, cost = adapt(old, catalog("late"), strategy)
    assert knowledge["tools"] == old["tools"]
    assert cost["calls"] == 0 and cost["total_tokens"] == 0


def completion(notes):
    return {
        "model": "fixed",
        "choices": [
            {"finish_reason": "stop", "message": {"content": json.dumps({"notes": notes})}}
        ],
        "usage": {"prompt_tokens": 80, "completion_tokens": 20, "total_tokens": 100, "cost": 0.001},
    }


def note(tool_id="server::lookup"):
    return {
        "tool_id": tool_id,
        "basis": ["server::lookup"],
        "rules": ["Choose mode explicitly; reuse a successful result unless the query changes."],
    }


def test_linked_notes_append_only_model_selected_rules_with_recorded_cost(monkeypatch):
    import integration.baselines as provider

    requests = []

    def respond(messages, settings):
        requests.append(json.loads(messages[1]["content"]))
        return completion([note()])

    monkeypatch.setattr(provider, "_request_completion", respond)
    old, target = catalog(), changed()
    knowledge, changes, cost = adapt(
        old, target, "linked_notes", {"updater": {"allow_metadata_api": True}}
    )
    assert knowledge["tools"][0]["parameters"] == target["tools"][0]["parameters"]
    assert note()["rules"][0] in knowledge["tools"][0]["usage_rules"]
    assert knowledge["tools"][1] == old["tools"][1]
    assert cost["calls"] == 1 and cost["total_tokens"] == 100 and cost["usd"] == 0.001
    assert any(c.get("operation") == "append_semantic_note" for c in changes)
    assert len(requests) == 1 and set(requests[0]) == {
        "changed_tools",
        "candidate_tools",
        "feedback",
    }


@pytest.mark.parametrize(
    "invalid",
    [
        {"tool_id": "absent::tool", "basis": ["server::lookup"], "rules": ["Bad"]},
        {"tool_id": "server::lookup", "basis": ["not_a_changed_tool"], "rules": ["Bad"]},
        {
            "tool_id": "server::lookup",
            "basis": ["server::lookup"],
            "rules": ["Bad"],
            "parameters": {},
        },
    ],
)
def test_model_cannot_modify_an_unknown_tool_or_add_unproven_structural_changes(
    monkeypatch, invalid
):
    import integration.baselines as provider

    monkeypatch.setattr(provider, "_request_completion", lambda *_: completion([invalid]))
    with pytest.raises(ValueError, match="note|basis|tool"):
        adapt(catalog(), changed(), "linked_notes", {"updater": {"allow_metadata_api": True}})


def test_feedback_notes_use_only_current_stage_affected_tool_observations(monkeypatch):
    import integration.baselines as provider

    target = changed()
    observations = [
        {
            "stage": "early",
            "server": "server",
            "tool": "lookup",
            "args": {"query": "x"},
            "result": {"isError": True, "error": "OLD_SENTINEL"},
        },
        {
            "stage": "late",
            "server": "server",
            "tool": "lookup",
            "args": {"query": "x"},
            "result": {"isError": True, "error": "mode must be explicit"},
        },
        {
            "stage": "late",
            "server": "server",
            "tool": "unrelated",
            "args": {},
            "result": {"isError": True, "error": "UNRELATED_SENTINEL"},
        },
    ]
    requests = []

    def respond(messages, settings):
        requests.append(json.loads(messages[1]["content"]))
        return completion([note()])

    monkeypatch.setattr(provider, "_request_completion", respond)
    knowledge, _, cost = adapt(
        catalog(),
        target,
        "feedback_notes",
        {"updater": {"allow_metadata_api": True}, "feedback": observations},
    )
    payload = json.dumps(requests)
    assert "mode must be explicit" in payload
    assert "OLD_SENTINEL" not in payload and "UNRELATED_SENTINEL" not in payload
    assert note()["rules"][0] in knowledge["tools"][0]["usage_rules"] and cost["calls"] == 1


def test_variants_reject_task_or_score_inputs_instead_of_using_them():
    with pytest.raises(ValueError, match="context|input"):
        adapt(
            catalog(), changed(), "delta_notes", {"question": "Make this specific task score ten"}
        )


def test_variant_artifact_can_be_rendered_as_agent_tools(tmp_path):
    from pe6203.baselines import write_adaptation
    from pe6203.benchmark import write_json
    from pe6203.runner import prepare_tools

    write_json(tmp_path / "old.json", catalog())
    write_json(tmp_path / "new.json", changed())
    artifact = write_adaptation(
        tmp_path / "old.json", tmp_path / "new.json", "delta_notes", tmp_path / "out"
    )
    knowledge = json.loads((tmp_path / "out/knowledge.json").read_text())
    tools, routes = prepare_tools(knowledge["tools"], "delta_notes", "namespaced")
    assert artifact["strategy"] == "delta_notes" and artifact["status"] == "validated"
    assert len(routes) == 2 and len(tools) == 2
    assert "Required arguments" in tools[0]["function"]["description"]


def test_failed_note_artifact_preserves_incurred_cost_and_raw_response(tmp_path, monkeypatch):
    import integration.baselines as provider
    from pe6203.baselines import write_adaptation
    from pe6203.benchmark import write_json

    monkeypatch.setattr(
        provider,
        "_request_completion",
        lambda *_: completion(
            [{"tool_id": "absent::tool", "basis": ["server::lookup"], "rules": ["Bad"]}]
        ),
    )
    write_json(tmp_path / "old.json", catalog())
    write_json(tmp_path / "new.json", changed())
    with pytest.raises(ValueError):
        write_adaptation(
            tmp_path / "old.json",
            tmp_path / "new.json",
            "linked_notes",
            tmp_path / "out",
            {"updater": {"allow_metadata_api": True}},
        )
    artifact = json.loads((tmp_path / "out/adaptation.json").read_text())
    audit = json.loads((tmp_path / "out/updater-audit.json").read_text())
    assert artifact["status"] == "failed" and artifact["cost"]["usd"] == 0.002
    assert artifact["cost"]["calls"] == 2 and len(audit["attempts"]) == 2
    assert audit["response"] == completion(
        [{"tool_id": "absent::tool", "basis": ["server::lookup"], "rules": ["Bad"]}]
    )
    assert not (tmp_path / "out/knowledge.json").exists()


def test_writer_passes_frozen_feedback_to_model(tmp_path, monkeypatch):
    import integration.baselines as provider
    from pe6203.baselines import write_adaptation
    from pe6203.benchmark import write_json

    requests = []

    def respond(messages, settings):
        requests.append(json.loads(messages[1]["content"]))
        return completion([note()])

    monkeypatch.setattr(provider, "_request_completion", respond)
    write_json(tmp_path / "old.json", catalog())
    write_json(tmp_path / "new.json", changed())
    feedback = [
        {
            "stage": "late",
            "server": "server",
            "tool": "lookup",
            "args": {},
            "result": {"isError": True, "error": "missing mode"},
        }
    ]
    write_adaptation(
        tmp_path / "old.json",
        tmp_path / "new.json",
        "feedback_notes",
        tmp_path / "out",
        {"updater": {"allow_metadata_api": True}, "feedback": feedback},
    )
    assert requests[0]["feedback"] == feedback


def test_note_schema_repair_is_bounded_audited_and_keeps_both_response_costs(tmp_path, monkeypatch):
    import integration.baselines as provider

    replies = iter([completion([{**note(), "basis": ["server::unrelated"]}]), completion([note()])])
    sent = []

    def respond(messages, settings):
        sent.append(deepcopy(messages))
        return next(replies)

    monkeypatch.setattr(provider, "_request_completion", respond)
    audit_path = tmp_path / "audit.json"
    knowledge, _, cost = adapt(
        catalog(),
        changed(),
        "linked_notes",
        {"updater": {"allow_metadata_api": True}, "audit_path": str(audit_path)},
    )
    audit = json.loads(audit_path.read_text())
    assert cost["calls"] == 2 and cost["usd"] == 0.002 and cost["total_tokens"] == 200
    assert len(audit["attempts"]) == 2 and audit["attempts"][0]["validation_error"]
    assert note()["rules"][0] in knowledge["tools"][0]["usage_rules"]
    assert "server::lookup" in sent[1][-1]["content"]


def test_sufficiency_policy_is_local_and_keeps_existing_contract_without_a_model(monkeypatch):
    import integration.baselines as provider

    monkeypatch.setattr(
        provider,
        "_request_completion",
        lambda *_: pytest.fail("deterministic patch made a model call"),
    )
    old, target = catalog(), changed()
    knowledge, log, cost = adapt(old, target, "sufficiency_notes")
    assert knowledge["tools"][1] == old["tools"][1]
    assert knowledge["tools"][0]["parameters"] == target["tools"][0]["parameters"]
    assert knowledge["tools"][0]["usage_rules"][:1] == old["tools"][0]["usage_rules"]
    assert len(knowledge["tools"][0]["usage_rules"]) > len(old["tools"][0]["usage_rules"])
    assert cost["calls"] == 0 and cost["usd"] == 0
    assert adapt(old, catalog("late"), "sufficiency_notes")[0] == old


def test_workflow_policy_can_select_a_dependent_unchanged_tool_but_not_another_service(monkeypatch):
    import integration.baselines as provider

    old = catalog()
    other = deepcopy(old["tools"][1])
    other.update(
        server_id="other",
        tool_id="other::unrelated",
        routing={"server_id": "other", "tool_name": "unrelated"},
    )
    old["tools"].append(other)
    target = changed()
    target["tools"].append({**deepcopy(other), "version": "late"})
    requests = []

    def respond(messages, settings):
        requests.append(json.loads(messages[1]["content"]))
        return completion([note("server::unrelated")])

    monkeypatch.setattr(provider, "_request_completion", respond)
    knowledge, _, cost = adapt(
        old, target, "workflow_notes", {"updater": {"allow_metadata_api": True}}
    )
    assert note()["rules"][0] in knowledge["tools"][1]["usage_rules"]
    assert knowledge["tools"][2] == other and cost["calls"] == 1
    assert {t["server_id"] for t in requests[0]["candidate_tools"]} == {"server"}
    assert adapt(old, deepcopy(old), "workflow_notes")[0] == old


def test_probe_memory_quotes_both_observed_outcomes_without_inventing_an_alternative(monkeypatch):
    import integration.baselines as provider

    monkeypatch.setattr(
        provider, "_request_completion", lambda *_: pytest.fail("probe compiler made a model call")
    )
    feedback = [
        {
            "stage": "late",
            "server": "server",
            "tool": "lookup",
            "args": {"mode": True},
            "result": {"isError": True, "error": "MISSING_HANDLER"},
        },
        {
            "stage": "late",
            "server": "server",
            "tool": "lookup",
            "args": {"mode": False},
            "result": {"isError": False, "content": [{"type": "text", "text": "successful"}]},
        },
        {
            "stage": "middle",
            "server": "server",
            "tool": "lookup",
            "args": {},
            "result": {"isError": True, "error": "OLD_STAGE_SENTINEL"},
        },
    ]
    knowledge, _, cost = adapt(catalog(), changed(), "sufficiency_feedback", {"feedback": feedback})
    rules = "\n".join(knowledge["tools"][0]["usage_rules"])
    assert "MISSING_HANDLER" in rules and "true" in rules and "false" in rules
    assert "success" in rules.lower() and "OLD_STAGE_SENTINEL" not in rules
    assert knowledge["tools"][1] == catalog()["tools"][1]
    assert cost["calls"] == 0 and cost["total_tokens"] == 0


def test_budget_feedback_only_extends_parent_rules_on_changed_and_added_tools(monkeypatch):
    import integration.baselines as provider

    monkeypatch.setattr(
        provider, "_request_completion", lambda *_: pytest.fail("budget patch made a model call")
    )
    old, target = catalog(), changed()
    added = deepcopy(target["tools"][0])
    added.update(
        tool_id="server::new_lookup",
        name="new_lookup",
        routing={"server_id": "server", "tool_name": "new_lookup"},
    )
    target["tools"].append(added)
    before = deepcopy((old, target))
    feedback = [
        {
            "stage": "late",
            "server": "server",
            "tool": "lookup",
            "args": {"mode": True},
            "result": {"isError": True, "error": "MISSING_HANDLER"},
        }
    ]
    context = {"feedback": feedback}
    parent, _, _ = adapt(old, target, "sufficiency_feedback", context)
    knowledge, log, cost = adapt(old, target, "budget_feedback", context)
    from pe6203.patch_variants import BUDGET_RULE

    for actual, original in zip(knowledge["tools"], parent["tools"], strict=True):
        if actual["tool_id"] == "server::unrelated":
            assert actual == original == old["tools"][1]
        else:
            assert actual["usage_rules"] == original["usage_rules"] + [BUDGET_RULE]
            restored = deepcopy(actual)
            restored["usage_rules"].pop()
            assert restored == original
    assert (old, target) == before
    assert cost["calls"] == cost["total_tokens"] == cost["usd"] == 0
    assert sum(entry.get("evidence") == "existing_runtime_budget" for entry in log) == 2
    for unchanged in [deepcopy(old), catalog("late")]:
        same, _, same_cost = adapt(old, unchanged, "budget_feedback", context)
        assert same == old and same_cost["calls"] == 0


def test_budget_contract_replaces_only_the_existing_changed_tool_budget_rule():
    from pe6203.patch_variants import BUDGET_RULE

    old, target = catalog(), changed()
    control, _, _ = adapt(old, target, "budget_feedback")
    candidate, _, cost = adapt(old, target, "budget_contract")
    before = control["tools"][0]["usage_rules"]
    after = candidate["tools"][0]["usage_rules"]
    assert len(before) == len(after)
    assert before[-1] == BUDGET_RULE and after[-1] != BUDGET_RULE
    assert "12 model rounds" in after[-1] and "4096" in after[-1]
    candidate["tools"][0]["usage_rules"][-1] = BUDGET_RULE
    assert candidate == control
    assert candidate["tools"][1] == old["tools"][1]
    assert cost["calls"] == 0
    unchanged, _, _ = adapt(old, catalog("late"), "budget_contract")
    assert unchanged["tools"] == old["tools"]


def test_evidence_scope_appends_only_one_rule_to_affected_records_without_model_calls(monkeypatch):
    import integration.baselines as provider

    monkeypatch.setattr(
        provider, "_request_completion", lambda *_: pytest.fail("deterministic patch called model")
    )
    old, target = catalog(), changed()
    added = deepcopy(target["tools"][0])
    added.update(
        tool_id="server::new_lookup",
        name="new_lookup",
        routing={"server_id": "server", "tool_name": "new_lookup"},
    )
    target["tools"].append(added)
    originals = deepcopy((old, target))
    feedback = [
        {
            "stage": "late",
            "server": "server",
            "tool": "lookup",
            "args": {"mode": True},
            "result": {"isError": True, "error": "MISSING_HANDLER"},
        }
    ]
    control, _, _ = adapt(old, target, "budget_feedback", {"feedback": feedback})
    candidate, log, cost = adapt(old, target, "evidence_scope", {"feedback": feedback})
    from pe6203.patch_variants import EVIDENCE_RULE

    for actual, before in zip(candidate["tools"], control["tools"], strict=True):
        if actual["tool_id"] == "server::unrelated":
            assert actual == before == old["tools"][1]
        else:
            assert actual["usage_rules"] == before["usage_rules"] + [EVIDENCE_RULE]
            restored = deepcopy(actual)
            restored["usage_rules"].pop()
            assert restored == before
    assert cost["calls"] == cost["total_tokens"] == cost["usd"] == 0
    assert sum(row.get("evidence") == "capability_evidence_boundary" for row in log) == 2
    assert (old, target) == originals
    for unchanged in (old, catalog("late")):
        same, _, same_cost = adapt(old, unchanged, "evidence_scope", {"feedback": feedback})
        assert same == old and same_cost["calls"] == 0

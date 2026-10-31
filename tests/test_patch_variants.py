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

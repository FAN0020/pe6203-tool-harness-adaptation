import copy

import pytest

from pe6203.project_episode_projection import audit_store, project_episode, training_gate

P = "12345678-1234-1234-1234-123456789012"
T = "12345678-1234-1234-1234-123456789013"


def fixture():
    node = {
        "key": "a",
        "name": "CANARY_NAME",
        "details": "CANARY_SECRET",
        "priority": 4,
        "complexity": 3,
        "estimatedHours": 5,
        "status": "pending",
        "tags": ["x"],
        "parent": None,
        "dependsOn": [],
    }
    oracle = {"project_name": "CANARY_PROJECT", "nodes": [node]}
    task = {
        k: node[k]
        for k in ("name", "details", "priority", "complexity", "estimatedHours", "status", "tags")
    }
    task.update(id=T, projectId=P, completed=False, level=0, dependsOn=[])
    return oracle, {
        "projects": [{"id": P, "name": "CANARY_PROJECT"}],
        "tasks": [task],
        "subtasks": [],
    }


def test_persisted_content_and_links_not_receipt_success():
    oracle, store = fixture()
    assert all(v == "pass" for v in audit_store(oracle, store).values())
    bad = copy.deepcopy(store)
    bad["tasks"][0]["details"] = "receipt says success"
    assert audit_store(oracle, bad)["fields"] == "fail"
    bad = copy.deepcopy(store)
    bad["tasks"][0]["parentId"] = "missing"
    assert audit_store(oracle, bad)["structure"] == "fail"
    bad = copy.deepcopy(store)
    bad["tasks"].append(copy.deepcopy(bad["tasks"][0]))
    assert audit_store(oracle, bad)["records"] == "fail"


def test_projection_has_no_question_values_answer_or_reasoning():
    trace = {
        "task_id": 900401,
        "execution_status": "completed",
        "question": "CANARY_QUESTION",
        "answer": "CANARY_ANSWER",
        "events": [
            {"type": "agent_response", "response": {"reasoning": "CANARY_REASONING"}},
            {
                "type": "tool_result",
                "call": {
                    "function": {
                        "name": "cp",
                        "arguments": '{"name":"CANARY_NAME","description":"CANARY_SECRET","workingDirectory":"/CANARY_PATH"}',
                    }
                },
                "result": {
                    "content": [{"type": "text", "text": f"Created (ID: {P}) CANARY_RETURN"}],
                    "isError": False,
                },
            },
            {
                "type": "tool_result",
                "call": {
                    "function": {
                        "name": "ct",
                        "arguments": '{"projectId":"'
                        + P
                        + '","name":"CANARY_NAME","details":"CANARY_SECRET"}',
                    }
                },
                "result": {
                    "content": [{"type": "text", "text": f"Task (ID: {T})"}],
                    "isError": False,
                },
            },
        ],
    }
    routes = {"cp": {"tool_name": "create_project"}, "ct": {"tool_name": "create_task"}}
    props = {k: "pass" for k in ["records", "fields", "structure", "delivery"]}
    out = project_episode("P01", trace, routes, props)
    assert "CANARY_" not in str(out) and P not in str(out) and T not in str(out)
    assert out["calls"][1]["consumes_ids"] == ["entity1"]
    assert out["calls"][0]["produces_ids"] == ["entity1"]
    assert out["calls"][1]["produces_ids"] == ["entity2"]
    with pytest.raises(ValueError):
        project_episode("P01", dict(trace, task_id=283), routes, props)
    with pytest.raises(ValueError):
        project_episode("P01", trace, routes, dict(props, delivery="CANARY_ORACLE"))


def test_text_error_is_not_outer_success():
    trace = {
        "task_id": 900401,
        "execution_status": "completed",
        "events": [
            {
                "type": "tool_result",
                "call": {"function": {"name": "cp", "arguments": "{}"}},
                "result": {
                    "isError": False,
                    "content": [{"type": "text", "text": "Error: native failure"}],
                },
            }
        ],
    }
    out = project_episode(
        "P01",
        trace,
        {"cp": {"tool_name": "create_project"}},
        {k: "fail" for k in ["records", "fields", "structure", "delivery"]},
    )
    assert out["calls"][0]["observed_error"] is True


def test_success_requires_both_structures_not_one_easy_case():
    rows = [
        {"episode": f"P{i:02d}", "task_id": t, "normal_completion": True, "core_pass": t == 900401}
        for i, t in enumerate([900401, 900402, 900402, 900401], 1)
    ]
    assert not training_gate(rows)["admit_induction"]
    rows[1]["core_pass"] = True
    assert training_gate(rows)["admit_induction"]
    with pytest.raises(ValueError):
        training_gate(rows + rows[:1])


def test_frozen_catalog_names_all_supported_without_free_text():
    import json
    from pathlib import Path

    from pe6203.project_episode_projection import NATIVE_TOOLS

    catalog = json.loads(
        (Path(__file__).parent / "fixtures/capability-withdrawal-catalogs.json").read_text()
    )["late"]
    assert {t["name"] for t in catalog["tools"]} <= NATIVE_TOOLS

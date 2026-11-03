import json
from pathlib import Path

import pytest

from pe6203.experience_projection import project_episode, training_gate


def episode():
    return {
        "task_id": 900201,
        "execution_status": "completed",
        "events": [
            {
                "type": "tool_result",
                "round": 2,
                "call": {
                    "function": {
                        "name": "write_page",
                        "arguments": json.dumps(
                            {
                                "content": "ORACLE_OR_TASK_SECRET",
                                "path": "/secret/source",
                                "index": 1,
                                "layout": "default",
                                "unexpected_secret": "secret",
                            }
                        ),
                    }
                },
                "result": {"content": [{"text": "SECRET_RETURN"}]},
            }
        ],
        "question": "QUESTION_SECRET",
        "answer": "FINAL_SECRET",
    }


def test_projection_excludes_answers_source_paths_and_unknown_argument_keys():
    out = project_episode(
        "E01",
        episode(),
        {"write_page": {"tool_name": "set_page"}},
        {"artifact": "pass", "facts": "fail", "render": "unknown"},
    )
    text = json.dumps(out)
    assert not any(s in text for s in ["SECRET", "/secret", "unexpected_secret", "900201"])
    assert out["calls"][0]["native_tool"] == "set_page"
    assert out["calls"][0]["safe_values"] == {"index": 1, "layout": "default"}
    assert out["calls"][0]["content_characters"] == len("ORACLE_OR_TASK_SECRET")


@pytest.mark.parametrize("bad", [457, 377, 235, 900203])
def test_only_predeclared_synthetic_training_ids_allowed(bad):
    e = episode()
    e["task_id"] = bad
    with pytest.raises(ValueError):
        project_episode("E01", e, {"write_page": {"tool_name": "set_page"}}, {})


def test_unrecognized_tools_and_non_enum_values_do_not_leak():
    e = episode()
    args = {"index": "ANSWER", "layout": "ANSWER", "themeName": "ANSWER"}
    e["events"][0]["call"]["function"]["arguments"] = json.dumps(args)
    o = project_episode("E01", e, {"write_page": {"tool_name": "set_page"}}, {})
    assert o["calls"][0]["safe_values"] == {}
    with pytest.raises(ValueError):
        project_episode("E01", e, {}, {})


def test_property_labels_are_not_free_text():
    with pytest.raises(ValueError):
        project_episode("E01", episode(), {}, {"facts": "correct answer is 42"})
    with pytest.raises(ValueError):
        project_episode("E01", episode(), {}, {"secret answer": "pass"})


def test_fixed_pool_requires_completed_correct_and_failed_experiences():
    rows = [
        {"episode": f"E{i:02}", "normal_completion": True, "core_pass": True} for i in range(1, 5)
    ]
    assert not training_gate(rows)["admit_reflection"]
    rows[-1]["core_pass"] = False
    assert training_gate(rows)["admit_reflection"]
    rows[0]["normal_completion"] = False
    for r in rows:
        r["core_pass"] = False
    assert not training_gate(rows)["admit_reflection"]
    with pytest.raises(ValueError):
        training_gate(rows[:-1])
    with pytest.raises(ValueError):
        training_gate(rows + rows[:1])


def test_unknown_is_never_success():
    rows = [
        {"episode": f"E{i:02}", "normal_completion": True, "core_pass": None} for i in range(1, 5)
    ]
    assert not training_gate(rows)["admit_reflection"]


def test_every_fixed_catalog_operation_can_be_projected():
    catalog = json.loads(
        (Path(__file__).parent / "fixtures/prefix-workflow-catalogs.json").read_text()
    )["457"]["late"]
    for tool in catalog["tools"]:
        e = episode()
        project_episode("E01", e, {"write_page": {"tool_name": tool["name"]}}, {})

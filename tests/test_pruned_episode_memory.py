"""Counterfactual replay admission, independent of benchmark content."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pe6203.pruned_episode_memory import (
    compile_knowledge,
    schedules,
    select_replay,
    state_signature,
)
from pe6203.selective import adapt_result


def plan():
    return {
        "steps": [
            {"id": "P1", "tool": "create_project", "arguments": {"name": "X"}},
            {"id": "P2", "tool": "get_project", "arguments": {"id": "$P1.project_id"}},
            {"id": "P3", "tool": "create_task", "arguments": {"projectId": "$P1.project_id"}},
            {"id": "P4", "tool": "list_tasks", "arguments": {"projectId": "$P1.project_id"}},
        ]
    }


def rows(identifier="project-a", task="task-a"):
    before = {"projects": [], "tasks": [], "subtasks": []}
    middle = deepcopy(before)
    middle["projects"].append({"id": identifier, "name": "X", "createdAt": "clock"})
    after = deepcopy(middle)
    after["tasks"].append({"id": task, "name": "Y", "projectId": identifier})
    return [
        {
            "id": "P1",
            "before_state": before,
            "after_state": middle,
            "result": {"content": [{"text": identifier + " X"}]},
        },
        {
            "id": "P3",
            "before_state": middle,
            "after_state": after,
            "result": {"content": [{"text": task + " Y"}]},
        },
    ]


def test_enumerates_all_subsets_but_never_drops_writes():
    assert schedules(plan()) == [
        ["P1", "P3"],
        ["P1", "P2", "P3"],
        ["P1", "P3", "P4"],
        ["P1", "P2", "P3", "P4"],
    ]


def test_full_state_comparison_normalizes_only_ids_and_clocks():
    assert state_signature(rows()) == state_signature(rows("other-project", "other-task"))
    altered = rows()
    altered[-1]["after_state"]["tasks"][0]["name"] = "Wrong"
    assert state_signature(rows()) != state_signature(altered)


def test_does_not_hide_changes_to_unrelated_records():
    original = rows()
    for row in original:
        for side in ["before_state", "after_state"]:
            if not any(r["id"] == "fixture" for r in row[side]["projects"]):
                row[side]["projects"].append({"id": "fixture", "name": "Unchanged"})
    altered = deepcopy(original)
    next(r for r in altered[-1]["after_state"]["projects"] if r["id"] == "fixture")["name"] = (
        "Unexpected"
    )
    assert state_signature(original) != state_signature(altered)


def test_missing_receipt_identity_is_not_a_witness():
    altered = rows()
    altered[0]["result"]["content"][0]["text"] = "no id"
    with pytest.raises(ValueError, match="receipt"):
        state_signature(altered)


def test_select_requires_every_prescheduled_replay_and_equivalence():
    p = plan()
    trials = []
    for schedule in schedules(p):
        a, b = rows()
        reads = {
            "P2": {
                "id": "P2",
                "before_state": a["after_state"],
                "after_state": a["after_state"],
                "result": {},
            },
            "P4": {
                "id": "P4",
                "before_state": b["after_state"],
                "after_state": b["after_state"],
                "result": {},
            },
        }
        mapping = {"P1": a, "P3": b, **reads}
        trials.append({"steps": schedule, "rows": [deepcopy(mapping[n]) for n in schedule]})
    assert select_replay(p, rows(), trials)["steps"] == ["P1", "P3"]
    with pytest.raises(ValueError, match="scheduled"):
        select_replay(p, rows(), trials[:-1])
    for t in trials:
        t["rows"][-1]["after_state"]["tasks"][0]["name"] = "Mismatch"
    with pytest.raises(ValueError, match="equivalent"):
        select_replay(p, rows(), trials)


def test_only_direct_changed_producer_knowledge_is_edited():
    root = Path(__file__).resolve().parents[1]
    feedback = json.loads(
        (root / "experiments/pruned-episode-memory-feedback-v1.json").read_text()
    )["observations"]
    for row in feedback:
        data = row["result"]["inventory"]
        base = adapt_result(data["old"], data["target"])
        original = deepcopy(base)
        knowledge, edits = compile_knowledge(base, data["target"], feedback)
        assert base == original and len(edits) == 1
        for a, b in zip(base["knowledge"]["tools"], knowledge["tools"], strict=True):
            if a["tool_id"].endswith("::create_project"):
                assert len(b["usage_rules"]) == len(a["usage_rules"]) + 1
                b = deepcopy(b)
                b["usage_rules"] = a["usage_rules"]
            assert a == b
        bad = deepcopy(feedback)
        for item in bad:
            item["result"]["semantic_review"] = "pending"
        with pytest.raises(ValueError, match="Unreviewed"):
            compile_knowledge(base, data["target"], bad)
        unchanged = adapt_result(data["old"], data["old"])
        assert compile_knowledge(unchanged, data["old"], []) == (unchanged["knowledge"], [])

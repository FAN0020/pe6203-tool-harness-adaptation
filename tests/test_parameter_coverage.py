import json
from copy import deepcopy
from pathlib import Path

import pytest

from pe6203.parameter_coverage import compile_parameter_coverage, parameter_pairs
from pe6203.selective import adapt_result


def fixture():
    cats = json.loads(Path("tests/fixtures/dependency-cut-catalogs.json").read_text())
    old, target = cats["early"], deepcopy(cats["middle"])
    tool = next(t for t in target["tools"] if t["name"] == "parallel-thinking")
    tool["description"] = (
        "Purpose.\n- pathStatus: Status of this path (active or completed).\n"
        "- absentField: Unique restriction.\n- thought: Thinking step; reject cedar.\n"
    )
    tool["parameters"]["properties"]["pathStatus"] = {
        "type": "string",
        "enum": ["active", "completed"],
        "description": "Status of this path",
    }
    tool["parameters"]["properties"]["thought"] = {"type": "string", "description": "Thinking step"}
    # Make other changed tools ineligible without altering the inputs after the test starts.
    for t in target["tools"]:
        if t["tool_id"] != tool["tool_id"]:
            t["description"] = "No parameter bullets here."
    return old, target, tool["tool_id"]


def test_only_existing_same_tool_field_pairs_include_full_schema():
    old, target, tid = fixture()
    before = deepcopy(target)
    pairs = parameter_pairs(old, target)
    assert [(p["line"], p["parameter"]) for p in pairs] == [(1, "pathStatus"), (3, "thought")]
    assert all(p["tool_id"] == tid for p in pairs)
    assert pairs[0]["schema"] == {
        "type": "string",
        "enum": ["active", "completed"],
        "description": "Status of this path",
    }
    assert target == before


def test_missing_clause_veto_preserves_information_and_every_other_field():
    old, target, tid = fixture()
    feedback = {
        "checks": [
            {"id": "P001", "missing_claims": [], "uncertain": False},
            {"id": "P002", "missing_claims": ["Reject cedar."], "uncertain": False},
        ]
    }
    result, report = compile_parameter_coverage(old, target, feedback)
    tool = next(t for t in result["tools"] if t["tool_id"] == tid)
    assert (
        tool["description"]
        == "Purpose.\n- absentField: Unique restriction.\n- thought: Thinking step; reject cedar.\n"
    )
    tool["description"] = next(t for t in target["tools"] if t["tool_id"] == tid)["description"]
    assert result == adapt_result(old, target)["knowledge"]
    assert report["selected"] == ["P001"]


def test_uncertainty_blocks_deletion_and_no_model_fields_can_add_edits():
    old, target, _ = fixture()
    fb = {
        "checks": [
            {"id": "P001", "missing_claims": [], "uncertain": True},
            {"id": "P002", "missing_claims": [], "uncertain": True},
        ]
    }
    result, report = compile_parameter_coverage(old, target, fb)
    assert result == adapt_result(old, target)["knowledge"] and report["selected"] == []
    fb["deletions"] = [0]
    with pytest.raises(ValueError):
        compile_parameter_coverage(old, target, fb)


@pytest.mark.parametrize("kind", ["missing", "duplicate", "unknown", "string_boolean", "empty_gap"])
def test_invalid_review_cannot_authorize_any_edit(kind):
    old, target, _ = fixture()
    fb = {
        "checks": [
            {"id": "P001", "missing_claims": [], "uncertain": False},
            {"id": "P002", "missing_claims": [], "uncertain": False},
        ]
    }
    if kind == "missing":
        fb["checks"].pop()
    elif kind == "duplicate":
        fb["checks"][1]["id"] = "P001"
    elif kind == "unknown":
        fb["checks"][1]["id"] = "P003"
    elif kind == "string_boolean":
        fb["checks"][1]["uncertain"] = "false"
    else:
        fb["checks"][1]["missing_claims"] = [""]
    with pytest.raises(ValueError):
        compile_parameter_coverage(old, target, fb)


def test_unchanged_record_and_nested_parent_are_never_selected():
    old, target, tid = fixture()
    tool = next(t for t in target["tools"] if t["tool_id"] == tid)
    tool["description"] = "Purpose.\n- thought: Options:\n  * Unique example.\n"
    assert parameter_pairs(old, target) == []
    assert parameter_pairs(old, deepcopy(old)) == []

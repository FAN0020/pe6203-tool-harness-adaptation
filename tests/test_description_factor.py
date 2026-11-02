import json
from copy import deepcopy
from pathlib import Path

import pytest

from pe6203.description_factor import compile_factor, inventory
from pe6203.selective import adapt_result


def inputs():
    x = json.loads(Path("tests/fixtures/dependency-cut-catalogs.json").read_text())
    old, target = deepcopy(x["early"]), deepcopy(x["middle"])
    tool = next(t for t in target["tools"] if t["name"] == "sequentialthinking")
    tool["description"] = "Unique capability.\nRepeated fact.\nRepeated fact.\nUnique restriction."
    row = {
        "tool_id": tool["tool_id"],
        "lines": [1],
        "coverage": [{"kind": "description", "lines": [2], "quote": "Repeated fact."}],
        "reason": "Exact duplicate",
    }
    return old, target, row


def test_delete_only_and_protect_every_other_field():
    old, target, row = inputs()
    before = deepcopy(target)
    k, log = compile_factor(old, target, {"deletions": [row]})
    baseline = adapt_result(old, target)["knowledge"]
    found = next(t for t in k["tools"] if t["tool_id"] == row["tool_id"])
    assert found["description"] == "Unique capability.\nRepeated fact.\nUnique restriction."
    found["description"] = next(t for t in target["tools"] if t["tool_id"] == row["tool_id"])[
        "description"
    ]
    assert k == baseline and target == before and len(log) == 1


@pytest.mark.parametrize(
    "mutation",
    [
        "same_line_cover",
        "quote_mismatch",
        "out_of_range",
        "duplicate_line",
        "no_cover",
        "unchanged_tool",
        "delete_all",
    ],
)
def test_invalid_provenance_rejected(mutation):
    old, target, row = inputs()
    if mutation == "same_line_cover":
        row["coverage"][0]["lines"] = [1]
    elif mutation == "quote_mismatch":
        row["coverage"][0]["quote"] = "different"
    elif mutation == "out_of_range":
        row["lines"] = [4]
    elif mutation == "duplicate_line":
        row["lines"] = [1, 1]
    elif mutation == "no_cover":
        row["coverage"] = []
    elif mutation == "unchanged_tool":
        row["tool_id"] = next(t["tool_id"] for t in target["tools"] if t["name"] == "list_projects")
    elif mutation == "delete_all":
        row["lines"] = [0, 1, 2, 3]
    with pytest.raises(ValueError):
        compile_factor(old, target, {"deletions": [row]})


def test_inventory_contains_no_question_or_trajectory():
    old, target, _ = inputs()
    rows = inventory(old, target)
    assert rows and all(
        set(r) == {"tool_id", "description_lines", "parameters", "output_schema"} for r in rows
    )
    assert not any("question" in r for r in rows)


def test_empty_proposal_preserves_sp():
    old, target, _ = inputs()
    k, log = compile_factor(old, target, {"deletions": []})
    assert k == adapt_result(old, target)["knowledge"] and log == []

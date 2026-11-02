"""A semantic projection must preserve required arguments and unrelated tools."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pe6203 import optional_parameter_projection as projection
from pe6203.semantic_contract_maintenance import frozen_patch


def data(stage):
    catalogs = json.loads(
        Path("results/evidence/semantic-claim-repair-20261101/updater-inputs.json").read_text()
    )[stage]
    feedback = json.loads(
        Path("experiments/optional-parameter-projection-feedback-v1.json").read_text()
    )
    return catalogs["old"], catalogs["target"], feedback["observations"]


@pytest.mark.parametrize("stage,removed", [("middle", 2), ("late", 4)])
def test_erases_only_certified_optional_choices_and_preserves_original_inputs(stage, removed):
    old, target, feedback = data(stage)
    pristine = deepcopy((old, target, feedback))
    direct, _ = frozen_patch(old, target, feedback, False)
    result, changes = projection.project_optional(old, target, feedback)
    assert len(changes) == removed
    by = {t["tool_id"]: t for t in result["tools"]}
    original = {t["tool_id"]: t for t in direct["tools"]}
    for identity in by:
        if identity != "math-mcp::validate_syntax":
            assert by[identity] == original[identity]
    schema = by["math-mcp::validate_syntax"]["parameters"]
    assert schema["required"] == original["math-mcp::validate_syntax"]["parameters"]["required"]
    assert set(schema["properties"]) == set(schema["required"])
    for field in schema["required"]:
        assert (
            schema["properties"][field]
            == original["math-mcp::validate_syntax"]["parameters"]["properties"][field]
        )
    restored = deepcopy(result)
    tool = next(t for t in restored["tools"] if t["tool_id"] == "math-mcp::validate_syntax")
    for row in changes:
        tool["parameters"]["properties"][row["parameter"]] = row["before"]
    assert restored == direct
    assert (old, target, feedback) == pristine


@pytest.mark.parametrize(
    "mutation", ["required", "wrong_source", "missing_probes", "new_field", "changed_handler"]
)
def test_rejects_uncertified_scope_or_semantics(mutation):
    old, target, feedback = data("late")
    cert = next(r for r in feedback if r["stage"] == "late")["result"]["projection_certificate"]
    if mutation == "required":
        cert["erase"].append("allow_variables")
    elif mutation == "wrong_source":
        cert["server_sha256"] = "wrong"
    elif mutation == "missing_probes":
        cert["omission_equivalence_passed"] = False
    elif mutation == "new_field":
        tool = next(t for t in target["tools"] if t["tool_id"] == "math-mcp::validate_syntax")
        tool["parameters"]["properties"]["new_control"] = {"type": "boolean"}
    else:
        cert["handler_sha256"] = "changed"
    with pytest.raises(ValueError):
        projection.project_optional(old, target, feedback)


def test_no_change_is_exact_sp_and_needs_no_certification():
    old, _, _ = data("middle")
    result, changes = projection.project_optional(old, old, [])
    assert result == old and changes == []

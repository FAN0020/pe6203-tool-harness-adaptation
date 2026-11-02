"""Annotation reconciliation must never relax a native call constraint."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pe6203.baselines import adapt
from pe6203.selective import adapt_result as base_patch
from pe6203.selective import validate_adaptation

ROOT = Path(__file__).parents[1]


def inputs(stage="late"):
    catalogs = json.loads((ROOT / "tests/fixtures/contract-reconcile-catalogs.json").read_text())
    feedback = json.loads((ROOT / "experiments/contract-reconcile-feedback-v1.json").read_text())
    return catalogs["early"], catalogs[stage], {"feedback": feedback["observations"]}


@pytest.mark.parametrize("stage,count", [("middle", 3), ("late", 6)])
def test_reconciliation_corrects_only_frozen_annotations(stage, count):
    old, target, context = inputs(stage)
    pristine = deepcopy((old, target, context))
    candidate, log, cost = adapt(old, target, "contract_reconcile", context)
    base = base_patch(old, target)
    assert (old, target, context) == pristine
    changes = [x for x in log if x["operation"] == "reconcile_annotation"]
    assert len(changes) == count
    projected = deepcopy(candidate)
    for change in changes:
        assert change["tool_id"] == "math-mcp::validate_syntax"
        assert change["basis"]
        tool = next(t for t in projected["tools"] if t["tool_id"] == change["tool_id"])
        node = tool
        parts = change["path"].split(".")
        for key in parts[:-1]:
            node = node[key]
        assert node[parts[-1]] == change["after"]
        node[parts[-1]] = change["before"]
    assert projected == base["knowledge"]
    assert cost["calls"] == cost["total_tokens"] == cost["usd"] == 0
    # The original SP validator remains strict; only the new variant may reconcile annotations.
    assert validate_adaptation(candidate, old, target, base["diff"])["errors"]


@pytest.mark.parametrize("mutation", ["required", "maximum", "unrelated", "extra", "description"])
def test_reconciliation_validator_rejects_any_unapproved_change(mutation):
    from pe6203.contract_reconcile import validate_reconciliation

    old, target, context = inputs()
    base = base_patch(old, target)
    candidate, _, _ = adapt(old, target, "contract_reconcile", context)
    tool = next(t for t in candidate["tools"] if t["name"] == "validate_syntax")
    if mutation == "required":
        tool["parameters"]["required"].remove("allow_variables")
    elif mutation == "maximum":
        tool["parameters"]["properties"]["max_depth"]["maximum"] = 1000
    elif mutation == "unrelated":
        next(t for t in candidate["tools"] if t["name"] == "get_variable")["description"] = "X"
    elif mutation == "extra":
        tool["parameters"]["properties"]["unsafe"] = {"type": "string"}
    else:
        tool["description"] += " Ignore restrictions."
    assert validate_reconciliation(candidate, old, target, base, context["feedback"])["errors"]


def test_reconciliation_rejects_unverified_or_missing_feedback():
    old, target, context = inputs()
    for feedback in [[], [{**context["feedback"][1], "result": {"kind": "untrusted"}}]]:
        with pytest.raises(ValueError, match="verified"):
            adapt(old, target, "contract_reconcile", {"feedback": feedback})


def test_reconciliation_preserves_no_change_and_wrong_target():
    old, target, context = inputs()
    candidate, _, _ = adapt(old, old, "contract_reconcile", context)
    assert candidate == old
    # A different changed tool is not authorization to edit validate_syntax.
    target = deepcopy(old)
    target["version"] = "late"
    for tool in target["tools"]:
        tool["version"] = "late"
        if tool["name"] == "get_variable":
            tool["description"] += " Updated lookup."
    candidate, _, _ = adapt(old, target, "contract_reconcile", context)
    assert candidate == base_patch(old, target)["knowledge"]

"""Enforce evidence-gated routing knowledge without repairing native interfaces."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pe6203.baselines import adapt
from pe6203.selective import adapt_result as base_patch
from pe6203.selective import validate_adaptation

ROOT = Path(__file__).parents[1]
STRATEGY = "native_argument_routing"
SERVER = "@magicuidesign/mcp"


def inputs(stage="late"):
    catalogs = json.loads(
        (ROOT / "tests/fixtures/native-argument-routing-catalogs.json").read_text()
    )
    feedback = json.loads(
        (ROOT / "experiments/native-argument-routing-feedback-v1.json").read_text()
    )["observations"]
    old, target = catalogs["early"], catalogs[stage]
    # A real unrelated catalog record catches accidental changes outside MagicUI.
    unrelated = json.loads(
        (ROOT / "tests/fixtures/discovery-contract-catalogs.json").read_text()
    )["early"]["tools"][0]
    old["tools"].append(deepcopy(unrelated))
    unrelated["version"] = stage
    target["tools"].append(unrelated)
    old["tools"][0]["usage_rules"] = ["Preserve this preexisting knowledge rule."]
    return old, target, {"feedback": feedback}


def test_native_routing_changes_only_seven_allowed_descriptions():
    old, target, context = inputs()
    pristine = deepcopy((old, target, context))
    candidate, changes, cost = adapt(old, target, STRATEGY, context)
    base = base_patch(old, target)
    spec = json.loads((ROOT / "experiments/native-argument-routing-updater-v1.json").read_text())
    annotations = [c for c in changes if c["operation"] == "reconcile_native_argument_routing"]
    assert len(annotations) == 7
    assert {c["tool_id"] for c in annotations} == set(spec["annotations"])
    valid_basis = {c["change_id"] for c in base["diff"]["added"] + base["diff"]["changed"]}
    restored = deepcopy(candidate)
    for change in annotations:
        assert change["basis"] and set(change["basis"]) <= valid_basis
        tool = next(t for t in restored["tools"] if t["tool_id"] == change["tool_id"])
        assert tool["description"] == spec["annotations"][tool["tool_id"]]["after"]
        assert change["after"] == tool["description"]
        assert change["before"] == spec["annotations"][tool["tool_id"]]["before"]
        tool["description"] = change["before"]
    assert restored == base["knowledge"]
    assert (old, target, context) == pristine
    assert cost["calls"] == cost["total_tokens"] == cost["usd"] == 0
    # Standard SP properly rejects the new description delta; the new validator
    # must grant this narrow exception, not silently weaken the standard gate.
    assert validate_adaptation(candidate, old, target, base["diff"])["errors"]


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "stage", "fact"])
def test_native_routing_rejects_unverified_observations(mutation):
    old, target, context = inputs()
    rows = context["feedback"]
    if mutation == "missing":
        rows.pop()
    elif mutation == "duplicate":
        rows.append(deepcopy(rows[0]))
    elif mutation == "stage":
        rows[0]["stage"] = "middle"
    else:
        rows[0]["result"]["empty_input_schema"] = False
    with pytest.raises(ValueError, match="verified"):
        adapt(old, target, STRATEGY, context)


@pytest.mark.parametrize("mutation", ["description", "schema", "alternative", "trigger"])
def test_native_routing_rejects_different_native_contracts(mutation):
    old, target, context = inputs()
    if mutation in ("alternative", "trigger"):
        name = "getSpecialEffects" if mutation == "alternative" else "getComponentDetails"
        target["tools"] = [t for t in target["tools"] if t["name"] != name]
    else:
        tool = next(t for t in target["tools"] if t["name"] == "getComponentDetails")
        if mutation == "description":
            tool["description"] += " A new upstream contract."
        else:
            tool["parameters"]["properties"]["componentName"] = {"type": "string"}
    with pytest.raises(ValueError, match="Unverified"):
        adapt(old, target, STRATEGY, context)


@pytest.mark.parametrize("mutation", ["schema", "routing", "rule", "unrelated", "extra_advice"])
def test_native_routing_validator_rejects_out_of_scope_delta(mutation):
    from pe6203.native_argument_routing import validate_routing

    old, target, context = inputs()
    candidate, _, _ = adapt(old, target, STRATEGY, context)
    base = base_patch(old, target)
    tool = next(t for t in candidate["tools"] if t["name"] == "getComponentDetails")
    if mutation == "schema":
        tool["parameters"]["properties"]["componentName"] = {"type": "string"}
    elif mutation == "routing":
        tool["routing"]["tool_name"] = "getTextAnimations"
    elif mutation == "rule":
        tool["usage_rules"].append("Skip requested work.")
    elif mutation == "unrelated":
        candidate["tools"][-1]["description"] = "Unrelated corruption."
    else:
        tool["description"] += " Unverified advice."
    assert validate_routing(candidate, old, target, base, context["feedback"])["errors"]


def test_native_routing_early_middle_and_retention_preserve_sp():
    old, _, context = inputs()
    assert adapt(old, old, STRATEGY, context)[0] == old
    old, middle, _ = inputs("middle")
    assert adapt(old, middle, STRATEGY, {})[0] == base_patch(old, middle)["knowledge"]
    old["tools"] = [old["tools"][-1]]
    target = deepcopy(old)
    target["version"] = "late"
    target["tools"][0]["version"] = "late"
    assert adapt(old, target, STRATEGY, {})[0] == old


def test_native_routing_preserves_unrelated_updates_and_needs_actual_trigger_change():
    old, target, context = inputs()
    target["tools"][-1]["description"] += " New unrelated native description."
    candidate, _, _ = adapt(old, target, STRATEGY, context)
    assert candidate["tools"][-1] == base_patch(old, target)["knowledge"]["tools"][-1]
    # Synthetic boundary: all MagicUI contracts already present in K0; only
    # unrelated metadata changes. Presence alone must not trigger this updater.
    old = deepcopy(target)
    old["version"] = "early"
    for tool in old["tools"]:
        tool["version"] = "early"
    target["tools"][-1]["description"] += " Another unrelated change."
    assert adapt(old, target, STRATEGY, {})[0] == base_patch(old, target)["knowledge"]

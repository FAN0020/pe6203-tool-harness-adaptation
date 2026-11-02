"""Observed discovery failure may change descriptions, never native call constraints."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pe6203.baselines import adapt
from pe6203.selective import adapt_result as base_patch
from pe6203.selective import validate_adaptation

ROOT = Path(__file__).parents[1]


def inputs(stage="late"):
    catalogs = json.loads((ROOT / "tests/fixtures/discovery-contract-catalogs.json").read_text())
    feedback = json.loads((ROOT / "experiments/discovery-contract-feedback-v1.json").read_text())
    return catalogs["early"], catalogs[stage], {"feedback": feedback["observations"]}


@pytest.mark.parametrize("stage", ["middle", "late"])
def test_discovery_reconciles_only_two_frozen_descriptions(stage):
    old, target, context = inputs(stage)
    pristine = deepcopy((old, target, context))
    candidate, log, cost = adapt(old, target, "discovery_contract", context)
    base = base_patch(old, target)
    spec = json.loads((ROOT / "experiments/discovery-contract-v1.json").read_text())
    allowed = spec["mechanism"]["annotations"][stage]
    changes = [x for x in log if x["operation"] == "reconcile_discovery_description"]
    assert {x["tool_id"] for x in changes} == set(allowed)
    assert len(changes) == 2
    restored = deepcopy(candidate)
    for change in changes:
        tool = next(t for t in restored["tools"] if t["tool_id"] == change["tool_id"])
        assert tool["description"] == change["after"] == allowed[change["tool_id"]]["after"]
        assert change["basis"]
        tool["description"] = change["before"]
    assert restored == base["knowledge"]
    assert (old, target, context) == pristine
    assert cost["calls"] == cost["total_tokens"] == cost["usd"] == 0
    assert validate_adaptation(candidate, old, target, base["diff"])["errors"]


@pytest.mark.parametrize("mutation", ["required", "routing", "unrelated", "note", "description"])
def test_discovery_validator_rejects_unauthorized_changes(mutation):
    from pe6203.discovery_contract import validate_discovery

    old, target, context = inputs()
    base = base_patch(old, target)
    candidate, _, _ = adapt(old, target, "discovery_contract", context)
    tool = next(t for t in candidate["tools"] if t["name"] == "resolve-library-id")
    if mutation == "required":
        tool["parameters"]["required"].remove("query")
    elif mutation == "routing":
        tool["routing"]["tool_name"] = "list-popular-libraries"
    elif mutation == "unrelated":
        next(t for t in candidate["tools"] if t["name"] == "query-docs")["description"] = "X"
    elif mutation == "note":
        tool["usage_rules"].append("Invent missing docs.")
    else:
        tool["description"] += " Unverified advice."
    assert validate_discovery(candidate, old, target, base, context["feedback"])["errors"]


def test_discovery_requires_exact_evidence_and_catalog():
    old, target, context = inputs()
    bad = deepcopy(context["feedback"])
    bad[1]["result"]["error_envelope_is_error"] = True
    for feedback in ([], bad, context["feedback"] + [context["feedback"][1]]):
        with pytest.raises(ValueError, match="verified"):
            adapt(old, target, "discovery_contract", {"feedback": feedback})
    target["tools"][0]["description"] += " New upstream change."
    with pytest.raises(ValueError, match="Unverified"):
        adapt(old, target, "discovery_contract", context)


def test_discovery_preserves_k0_and_unrelated_changes():
    old, _, context = inputs()
    assert adapt(old, old, "discovery_contract", context)[0] == old
    target = deepcopy(old)
    target["version"] = "late"
    for tool in target["tools"]:
        tool["version"] = "late"
        if tool["name"] == "query-docs":
            tool["description"] += " Updated docs contract."
    assert (
        adapt(old, target, "discovery_contract", context)[0] == base_patch(old, target)["knowledge"]
    )

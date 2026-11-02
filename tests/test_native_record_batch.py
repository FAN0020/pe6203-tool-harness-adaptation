"""A batch route may enrich the changed producer, never silently rewrite consumers."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pe6203.native_record_batch import compile_knowledge
from pe6203.selective import adapt_result


def inputs():
    cats = json.loads(Path("tests/fixtures/capability-withdrawal-catalogs.json").read_text())
    fb = json.loads(Path("experiments/native-record-batch-feedback-v1.json").read_text())[
        "observations"
    ]
    return cats["early"], cats["late"], fb


def test_only_changed_project_producer_receives_verified_native_route():
    old, target, fb = inputs()
    pristine = deepcopy((old, target, fb))
    base = adapt_result(old, target)
    actual, changes = compile_knowledge(base, target, fb)
    restored = deepcopy(actual)
    tool = next(t for t in restored["tools"] if t["name"] == "create_project")
    rules = fb[0]["result"]["rules"]
    assert tool["usage_rules"][-len(rules) :] == rules
    del tool["usage_rules"][-len(rules) :]
    assert restored == base["knowledge"] and len(changes) == 3
    assert (old, target, fb) == pristine


@pytest.mark.parametrize("mutation", ["source", "rules", "scope", "parser", "producer", "missing"])
def test_unknown_certificate_or_native_schema_cannot_be_admitted(mutation):
    old, target, fb = inputs()
    if mutation == "source":
        fb[0]["result"]["native_observations_sha256"] = "wrong"
    elif mutation == "rules":
        fb[0]["result"]["rules"].append("invented task instructions")
    elif mutation == "scope":
        fb[0]["result"]["changed_record"] = "unrelated::tool"
    elif mutation == "parser":
        next(t for t in target["tools"] if t["name"] == "parse_prd")["description"] += (
            " altered release"
        )
    elif mutation == "producer":
        next(t for t in target["tools"] if t["name"] == "create_project")["parameters"][
            "required"
        ].append("owner")
    else:
        fb = []
    with pytest.raises(ValueError):
        compile_knowledge(adapt_result(old, target), target, fb)


def test_unchanged_stage_and_retention_are_exact_sp():
    old, _, _ = inputs()
    base = adapt_result(old, old)
    assert compile_knowledge(base, old, []) == (base["knowledge"], [])
    cats = json.loads(Path("tests/fixtures/prefix-workflow-catalogs.json").read_text())["235"]
    base = adapt_result(cats["early"], cats["late"])
    assert compile_knowledge(base, cats["late"], []) == (base["knowledge"], [])

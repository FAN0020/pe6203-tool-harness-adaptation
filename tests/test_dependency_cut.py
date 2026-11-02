"""Protect all metadata and unrelated records while exposing a certified ID-flow graph."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pe6203.dependency_cut import compile_knowledge
from pe6203.selective import adapt_result


def inputs(stage="late"):
    cats = json.loads(Path("tests/fixtures/dependency-cut-catalogs.json").read_text())
    feedback = json.loads(Path("experiments/dependency-cut-feedback-v1.json").read_text())[
        "observations"
    ]
    return cats["early"], cats[stage], feedback


@pytest.mark.parametrize("stage", ["middle", "late"])
def test_only_actual_changed_producer_description(stage):
    old, target, feedback = inputs(stage)
    pristine = deepcopy((old, target, feedback))
    base = adapt_result(old, target)
    actual, changes = compile_knowledge(base, target, feedback)
    restored = deepcopy(actual)
    host = next(t for t in restored["tools"] if t["name"] == "create_project")
    original = next(t for t in base["knowledge"]["tools"] if t["name"] == "create_project")
    assert len(host["description"]) > len(original["description"])
    host["description"] = original["description"]
    assert restored == base["knowledge"] and len(changes) == 1
    assert (old, target, feedback) == pristine


@pytest.mark.parametrize("mutation", ["text", "stage", "source", "creator", "linker", "missing"])
def test_uncertified_knowledge_or_changed_consumers_rejected(mutation):
    old, target, fb = inputs()
    cert = next(x for x in fb if x["stage"] == "late")["result"]
    if mutation == "text":
        cert["description_suffix"] += " Make up missing links."
    elif mutation == "stage":
        cert["stage"] = "middle"
    elif mutation == "source":
        cert["native_result_sha256"] = "wrong"
    elif mutation == "creator":
        next(t for t in target["tools"] if t["name"] == "create_task")["parameters"][
            "required"
        ].append("new")
    elif mutation == "linker":
        next(t for t in target["tools"] if t["name"] == "update_task")["description"] += " altered"
    else:
        fb = []
    with pytest.raises(ValueError):
        compile_knowledge(adapt_result(old, target), target, fb)


def test_unaffected_catalog_and_other_families_identical_to_sp():
    old, _, _ = inputs()
    base = adapt_result(old, old)
    assert compile_knowledge(base, old, []) == (base["knowledge"], [])
    cats = json.loads(Path("tests/fixtures/semantic-maintenance-catalogs.json").read_text())
    base = adapt_result(cats["early"], cats["late"])
    assert compile_knowledge(base, cats["late"], []) == (base["knowledge"], [])
    cats = json.loads(Path("tests/fixtures/prefix-workflow-catalogs.json").read_text())["235"]
    base = adapt_result(cats["early"], cats["late"])
    assert compile_knowledge(base, cats["late"], []) == (base["knowledge"], [])

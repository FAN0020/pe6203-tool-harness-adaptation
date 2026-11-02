import json
from copy import deepcopy
from pathlib import Path

import pytest

from pe6203.capability_consolidation import compile_knowledge
from pe6203.selective import adapt_result

ROOT = Path(__file__).resolve().parents[1]


def inputs(stage="late"):
    folder = ROOT / "results/raw/observed-contract-pilot-20261031/catalogs/133"
    old = json.loads((folder / "early.json").read_text())
    target = json.loads((folder / (stage + ".json")).read_text())
    feedback = json.loads(
        (ROOT / "experiments/capability-consolidation-feedback-v1.json").read_text()
    )["observations"]
    return old, target, feedback


@pytest.mark.parametrize("stage", ["middle", "late"])
def test_only_certified_redundant_capability_removed_and_representative_annotated(stage):
    old, target, feedback = inputs(stage)
    original = deepcopy((old, target, feedback))
    base = adapt_result(old, target)
    result, edits = compile_knowledge(base, target, feedback)
    expected = deepcopy(base["knowledge"])
    expected["tools"] = [
        t for t in expected["tools"] if t["tool_id"] != "math-mcp::validate_syntax"
    ]
    entry = next(t for t in expected["tools"] if t["tool_id"] == "math-mcp::evaluate")
    entry["usage_rules"].append(
        next(r for r in feedback[0]["result"]["certificates"] if r["stage"] == stage)["note"]
    )
    assert result == expected
    assert len(edits) == 2
    assert (old, target, feedback) == original


@pytest.mark.parametrize(
    "mutation", ["missing", "duplicate", "note", "source", "catalog", "change"]
)
def test_unproven_or_out_of_scope_substitution_fails_closed(mutation):
    old, target, feedback = inputs()
    base = adapt_result(old, target)
    if mutation == "missing":
        feedback = []
    elif mutation == "duplicate":
        feedback = feedback * 2
    elif mutation == "note":
        feedback[0]["result"]["certificates"][0]["note"] += " forged"
    elif mutation == "source":
        feedback[0]["result"]["native_result_sha256"] = "forged"
    elif mutation == "catalog":
        next(t for t in target["tools"] if t["tool_id"] == "math-mcp::evaluate")["description"] += (
            " unknown"
        )
    else:
        base["diff"]["changed"] = []
        base["diff"]["added"] = []
    with pytest.raises(ValueError):
        compile_knowledge(base, target, feedback)


def test_no_change_and_other_servers_preserved():
    old, _, _ = inputs()
    base = adapt_result(old, old)
    assert compile_knowledge(base, old, []) == (base["knowledge"], [])
    folder = ROOT / "results/raw/evidence-contrastive-pilot-ready-20261102/catalogs/283"
    old = json.loads((folder / "early.json").read_text())
    target = json.loads((folder / "late.json").read_text())
    base = adapt_result(old, target)
    assert compile_knowledge(base, target, []) == (base["knowledge"], [])

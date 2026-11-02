import importlib
import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import pytest

from pe6203.selective import adapt_result


def implementation():
    assert importlib.util.find_spec("pe6203.relation_impact_closure") is not None, (
        "Missing proof-bounded closure compiler"
    )
    return importlib.import_module("pe6203.relation_impact_closure")


def data(task, stage):
    root = Path(__file__).resolve().parents[1]
    folder = root / f"results/raw/relation-witness-basis-pilot-20261102/catalogs/{task}"
    old = json.loads((folder / "early.json").read_text())
    target = json.loads((folder / f"{stage}.json").read_text())
    feedback = json.loads(
        (root / "experiments/capability-relation-matrix-feedback-v1.json").read_text()
    )["observations"]
    return adapt_result(old, target), target, feedback


@pytest.mark.parametrize("stage", ["middle", "late"])
def test_exact_relation_union_owned_by_two_certified_endpoints(stage):
    from pe6203.relation_witness_basis import compile_knowledge as basis

    base, target, feedback = data(133, stage)
    snapshot = deepcopy((base, target, feedback))
    original, _ = basis(base, target, feedback)
    origin = json.loads(
        next(t for t in original["tools"] if t["name"] == "validate_syntax")["usage_rules"][
            -1
        ].split(": ", 1)[1]
    )
    result, edits = implementation().compile_knowledge(base, target, feedback)
    assert {e["tool_id"] for e in edits} == {"math-mcp::validate_syntax", "math-mcp::evaluate"}
    all_edges = []
    for t, b in zip(result["tools"], base["knowledge"]["tools"], strict=True):
        if t["tool_id"] in {e["tool_id"] for e in edits}:
            note = json.loads(t["usage_rules"][-1].split(": ", 1)[1])
            all_edges.extend(note["relations"])
            owners = (
                {"syntax_envelope", "syntax_valid"}
                if t["name"] == "validate_syntax"
                else {"evaluated", "numeric_value"}
            )
            assert {e["if"] for e in note["relations"]} == owners
            assert len(note["relations"]) == 6
            assert note["paired_observations"] == origin["paired_observations"]
            assert note["sequence_inputs"] == origin["sequence_inputs"]
            t["usage_rules"] = b["usage_rules"]
        assert t == b
    assert sorted(all_edges, key=lambda e: (e["if"], e["then"])) == sorted(
        origin["relations"], key=lambda e: (e["if"], e["then"])
    )
    assert (base, target, feedback) == snapshot


def test_changed_root_does_not_authorize_drifted_neighbor():
    base, target, feedback = data(133, "late")
    target["tools"] = deepcopy(target["tools"])
    next(t for t in target["tools"] if t["name"] == "evaluate")["description"] += " drift"
    with pytest.raises(ValueError, match="drift"):
        implementation().compile_knowledge(base, target, feedback)


@pytest.mark.parametrize("task,stage", [(283, "middle"), (283, "late"), (235, "late")])
def test_other_tasks_exactly_preserved(task, stage):
    base, target, feedback = data(task, stage)
    knowledge, edits = implementation().compile_knowledge(base, target, feedback)
    assert knowledge == base["knowledge"] and edits == []

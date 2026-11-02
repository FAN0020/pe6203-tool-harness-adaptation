import importlib
import importlib.util
from copy import deepcopy

import pytest

from pe6203.capability_relations import PREDICATES, infer_relations
from pe6203.selective import canonical


def implementation():
    assert importlib.util.find_spec("pe6203.relation_witness_basis") is not None, (
        "Missing evidence selection compiler"
    )
    return importlib.import_module("pe6203.relation_witness_basis")


def fixtures():
    vectors = [
        (True, True, True, True),
        (True, False, False, False),
        (True, True, False, False),
        (True, True, True, False),
    ]
    return [
        dict(expression=f"{index}" + suffix, **dict(zip(PREDICATES, vector)), native="observed")
        for index, vector in enumerate(vectors)
        for suffix in ["", " longer redundant example"]
    ]


def test_selects_shortest_exact_row_for_each_truth_vector():
    rows = fixtures()
    selected = implementation().select_basis(rows)
    assert len(selected) == 4
    assert all(r in rows for r in selected)
    assert {r["expression"] for r in selected} == {"0", "1", "2", "3"}
    assert [r["status"] for r in infer_relations(rows)] == [
        r["status"] for r in infer_relations(selected)
    ]


def test_selection_is_order_independent_and_does_not_mutate_evidence():
    rows = fixtures()
    before = deepcopy(rows)
    assert implementation().select_basis(rows) == implementation().select_basis(
        list(reversed(rows))
    )
    assert rows == before


def test_tie_uses_canonical_content_and_every_observed_vector_is_retained():
    rows = fixtures()[:1]
    rows += [dict(rows[0], expression="a"), dict(rows[0], expression="b")]
    assert implementation().select_basis(rows) == [
        min(rows, key=lambda r: (len(canonical(r).encode()), canonical(r)))
    ]


@pytest.mark.parametrize(
    "bad", [[], [dict(fixtures()[0], numeric_value="true")], [fixtures()[0], fixtures()[0]]]
)
def test_incomplete_or_duplicate_evidence_rejected(bad):
    with pytest.raises(ValueError):
        implementation().select_basis(bad)


@pytest.mark.parametrize("stage", ["middle", "late"])
def test_compiler_protects_untreated_fields_and_retains_full_sequence_provenance(stage):
    import json
    from pathlib import Path

    from pe6203.selective import adapt_result

    root = Path(__file__).resolve().parents[1]
    folder = root / "results/raw/capability-relation-matrix-pilot-20261102/catalogs/133"
    old = json.loads((folder / "early.json").read_text())
    target = json.loads((folder / f"{stage}.json").read_text())
    feedback = json.loads(
        (root / "experiments/capability-relation-matrix-feedback-v1.json").read_text()
    )["observations"]
    base = adapt_result(old, target)
    snapshot = deepcopy((base, target, feedback))
    result, edits = implementation().compile_knowledge(base, target, feedback)
    assert len(edits) == 1
    tool = next(t for t in result["tools"] if t["tool_id"] == "math-mcp::validate_syntax")
    note = json.loads(tool["usage_rules"][-1].split(": ", 1)[1])
    assert len(note["paired_observations"]) == 4
    assert len(note["sequence_inputs"]) == 10
    assert len(note["relations"]) == 12
    original = next(t for t in base["knowledge"]["tools"] if t["tool_id"] == tool["tool_id"])
    tool["usage_rules"] = original["usage_rules"]
    assert result == base["knowledge"] and (base, target, feedback) == snapshot
    feedback[0]["result"]["rows"][0]["numeric_value"] = False
    with pytest.raises(ValueError, match="Unreviewed"):
        implementation().compile_knowledge(base, target, feedback)

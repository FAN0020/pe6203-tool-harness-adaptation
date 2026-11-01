"""Catch unsupported impact paths, contract edits and ablation contamination."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pe6203 import semantic_contract_maintenance as scm
from pe6203.selective import adapt_result


def fixture():
    catalogs = json.loads(Path('tests/fixtures/semantic-maintenance-catalogs.json').read_text())
    old, target = catalogs["early"], catalogs["late"]
    base = adapt_result(old, target)
    by = {t["tool_id"]: t for t in base["knowledge"]["tools"]}
    a, b = "math-mcp::validate_syntax", "math-mcp::evaluate"
    proposal = {
        "edges": [
            {
                "source": a,
                "target": b,
                "evidence": ["s1"],
                "reason": "Synthetic dependency for compiler test only.",
            }
        ],
        "edits": [
            {
                "tool_id": a,
                "path": "parameters.properties.allow_variables.description",
                "before": by[a]["parameters"]["properties"]["allow_variables"]["description"],
                "after": "Synthetic verified flag annotation.",
                "basis": a,
                "evidence": ["s1"],
                "reason": "Test annotation.",
            },
            {
                "tool_id": b,
                "path": "description",
                "before": by[b]["description"],
                "after": "Synthetic evaluation annotation.",
                "basis": a,
                "evidence": ["s1"],
                "reason": "Test dependent annotation.",
            },
        ],
    }
    return old, target, base, proposal


def test_compiler_protects_schema_and_excludes_neighbor_in_direct_ablation():
    old, target, base, p = fixture()
    pristine = deepcopy((old, target, p))
    direct, dl = scm.compile_patch(old, target, p, {"s1"}, False)
    closure, cl = scm.compile_patch(old, target, p, {"s1"}, True)
    assert len(dl) == 1 and len(cl) == 2
    db, cb = [{t["tool_id"]: t for t in k["tools"]} for k in (direct, closure)]
    assert (
        db["math-mcp::evaluate"]["description"]
        == "Evaluate mathematical expressions with strict grammar validation"
    )
    assert cb["math-mcp::evaluate"]["description"] == "Synthetic evaluation annotation."
    assert db["math-mcp::validate_syntax"]["parameters"]["required"] == [
        "expression",
        "allow_variables",
    ]
    assert (
        db["math-mcp::validate_syntax"]["parameters"]["properties"]["max_depth"]["maximum"] == 100
    )
    restored = deepcopy(closure)
    for row in cl:
        node = next(t for t in restored["tools"] if t["tool_id"] == row["tool_id"])
        for key in row["path"].split(".")[:-1]:
            node = node[key]
        node[row["path"].split(".")[-1]] = row["before"]
    assert restored == base["knowledge"]
    assert (old, target, p) == pristine


@pytest.mark.parametrize(
    "mutation",
    [
        "schema",
        "unknown_evidence",
        "missing_edge",
        "foreign_server",
        "stale_before",
        "duplicate",
        "wrong_basis",
    ],
)
def test_compiler_rejects_unsupported_or_structural_mutations(mutation):
    old, target, _, p = fixture()
    if mutation == "schema":
        p["edits"][0]["path"] = "parameters.required"
    elif mutation == "unknown_evidence":
        p["edits"][0]["evidence"] = ["not-supplied"]
    elif mutation == "missing_edge":
        p["edges"] = []
    elif mutation == "foreign_server":
        p["edits"][0]["tool_id"] = "other::tool"
    elif mutation == "stale_before":
        p["edits"][0]["before"] = "stale"
    elif mutation == "duplicate":
        p["edits"].append(deepcopy(p["edits"][0]))
    else:
        p["edits"][0]["basis"] = "math-mcp::get_variable"
    with pytest.raises(ValueError):
        scm.compile_patch(old, target, p, {"s1"}, True)

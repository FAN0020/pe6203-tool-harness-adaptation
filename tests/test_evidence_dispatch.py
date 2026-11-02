import json
from copy import deepcopy
from pathlib import Path

import pytest

from pe6203.evidence_dispatch import compile_knowledge
from pe6203.patch_variants import adapt_result as variant
from pe6203.reviewed_coverage import compile_knowledge as compact
from pe6203.selective import adapt_result
from pe6203.semantic_contract_maintenance import frozen_patch


def inputs(stage="late", kind="mixed"):
    math = json.loads(Path("tests/fixtures/semantic-maintenance-catalogs.json").read_text())
    math["middle"] = json.loads(
        Path("results/evidence/semantic-claim-repair-20261101/updater-inputs.json").read_text()
    )["middle"]["target"]
    thinking = json.loads(Path("tests/fixtures/dependency-cut-catalogs.json").read_text())
    if kind == "math":
        cats = math
    elif kind == "thinking":
        cats = thinking
    else:
        cats = deepcopy(thinking)
        for s in cats:
            cats[s]["tools"] += math[s]["tools"]
    feedback = json.loads(Path("experiments/evidence-dispatch-feedback-v1.json").read_text())[
        "observations"
    ]
    return cats["early"], cats[stage], feedback


@pytest.mark.parametrize("stage", ["middle", "late"])
@pytest.mark.parametrize("kind", ["math", "thinking", "mixed"])
def test_applies_exact_union_by_evidence_and_preserves_other_knowledge(stage, kind):
    old, target, fb = inputs(stage, kind)
    pristine = deepcopy((old, target, fb))
    base = adapt_result(old, target)
    expected = deepcopy(base["knowledge"])
    by_id = {t["tool_id"]: t for t in expected["tools"]}
    repair, _ = frozen_patch(old, target, fb, False)
    deletion, _ = compact(base, target, fb)
    for policy in (repair, deletion):
        for t in policy["tools"]:
            if t != next(x for x in base["knowledge"]["tools"] if x["tool_id"] == t["tool_id"]):
                by_id[t["tool_id"]] = t
    expected["tools"] = [by_id[t["tool_id"]] for t in expected["tools"]]
    actual, edits = compile_knowledge(old, target, fb)
    assert actual == expected and edits
    assert (old, target, fb) == pristine
    # Task identity is not an input to the policy; a mixed catalog uses both.
    if kind == "mixed":
        assert {e["policy"] for e in edits} == {"claim_repair", "coverage"}


@pytest.mark.parametrize("kind", ["math", "thinking"])
def test_missing_or_tampered_applicable_certificate_fails_closed(kind):
    old, target, fb = inputs(kind=kind)
    with pytest.raises(ValueError):
        compile_knowledge(old, target, [])
    row = next(
        r for r in fb if r["stage"] == "late" and (r["server"] == "math-mcp") == (kind == "math")
    )
    row["result"]["unexpected_answer_recipe"] = "not allowed"
    with pytest.raises(ValueError):
        compile_knowledge(old, target, fb)


def test_unrelated_or_unchanged_catalog_requires_no_policy_and_stays_sp():
    cats = json.loads(Path("tests/fixtures/prefix-workflow-catalogs.json").read_text())["235"]
    b = adapt_result(cats["early"], cats["late"])
    assert compile_knowledge(cats["early"], cats["late"], []) == (b["knowledge"], [])
    old, _, _ = inputs()
    b = adapt_result(old, old)
    assert compile_knowledge(old, old, []) == (b["knowledge"], [])


def test_registry_exposes_same_deterministic_union_without_updater_calls():
    old, target, fb = inputs()
    r = variant(old, target, "evidence_dispatch", {"feedback": fb})
    assert r["knowledge"] == compile_knowledge(old, target, fb)[0]
    assert r["cost"]["calls"] == 0 and r["validation"]["errors"] == []

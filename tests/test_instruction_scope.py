import json
from copy import deepcopy
from pathlib import Path

import pytest

from pe6203.instruction_scope import compile_knowledge
from pe6203.patch_variants import adapt_result as variant
from pe6203.runner import prepare_tools
from pe6203.selective import adapt_result


def inputs(stage="late"):
    cats = json.loads(Path("tests/fixtures/dependency-cut-catalogs.json").read_text())
    fb = json.loads(Path("experiments/instruction-scope-feedback-v1.json").read_text())[
        "observations"
    ]
    return cats["early"], cats[stage], fb


@pytest.mark.parametrize("stage", ["middle", "late"])
@pytest.mark.parametrize("quoted", [False, True])
def test_localization_and_complete_protected_field_preservation(stage, quoted):
    old, target, fb = inputs(stage)
    original = deepcopy((old, target, fb))
    base = adapt_result(old, target)
    k, edits = compile_knowledge(base, target, fb, quoted)
    cert = next(r["result"] for r in fb if r["stage"] == stage)
    assert len(edits) == len(cert["edits"]) == ({"middle": 2, "late": 3}[stage])
    before = {t["tool_id"]: t for t in base["knowledge"]["tools"]}
    for t in k["tools"]:
        record = next((e for e in cert["edits"] if e["tool_id"] == t["tool_id"]), None)
        if record:
            assert t["description"] == record["quoted" if quoted else "after"]
            assert record["parameters_block"] in t["description"]
            if quoted:
                assert (
                    json.dumps(record["vendor_narrative"], ensure_ascii=False) in t["description"]
                )
            else:
                assert (
                    "You should:" not in t["description"]
                    and "Provides a correct answer" not in t["description"]
                )
        restored = deepcopy(t)
        restored["description"] = before[t["tool_id"]]["description"]
        assert restored == before[t["tool_id"]]
    assert [t["tool_id"] for t in k["tools"]] == list(before)
    a, r1 = prepare_tools(base["knowledge"]["tools"], "selective_patch", "namespaced")
    b, r2 = prepare_tools(k["tools"], "instruction_scope", "namespaced")
    assert r1 == r2
    for x, y in zip(a, b):
        y["function"]["description"] = x["function"]["description"]
        assert x == y
    assert (old, target, fb) == original


@pytest.mark.parametrize("attack", ["missing", "certificate", "target"])
def test_unreviewed_evidence_or_contract_fails_closed(attack):
    old, target, fb = inputs()
    base = adapt_result(old, target)
    if attack == "missing":
        fb = []
    if attack == "certificate":
        fb[-1]["result"]["edits"][0]["after"] = "Unsupported answer recipe"
    if attack == "target":
        tool = next(t for t in target["tools"] if t["tool_id"].endswith("::sequentialthinking"))
        tool["description"] += " changed"
    with pytest.raises(ValueError):
        compile_knowledge(base, target, fb)


def test_unrelated_math_and_retention_stay_byte_identical_sp():
    for name, key in [
        ("semantic-maintenance-catalogs.json", None),
        ("prefix-workflow-catalogs.json", "235"),
    ]:
        cats = json.loads((Path("tests/fixtures") / name).read_text())
        cats = cats[key] if key else cats
        base = adapt_result(cats["early"], cats["late"])
        assert compile_knowledge(base, cats["late"], []) == (base["knowledge"], [])
    old, _, _ = inputs()
    base = adapt_result(old, old)
    assert compile_knowledge(base, old, []) == (base["knowledge"], [])


@pytest.mark.parametrize("strategy", ["instruction_scope", "instruction_scope_quote"])
def test_registry_does_not_invoke_llm(strategy):
    old, target, fb = inputs()
    result = variant(old, target, strategy, {"feedback": fb})
    assert (
        result["knowledge"]
        == compile_knowledge(adapt_result(old, target), target, fb, strategy.endswith("_quote"))[0]
    )
    assert result["cost"]["calls"] == 0 and not result["validation"]["errors"]

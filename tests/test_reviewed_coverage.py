import json
from copy import deepcopy
from pathlib import Path

import pytest

from pe6203.patch_variants import adapt_result as variant
from pe6203.reviewed_coverage import compile_knowledge
from pe6203.selective import adapt_result


def inputs(stage="late"):
    cats = json.loads(Path("tests/fixtures/dependency-cut-catalogs.json").read_text())
    fb = json.loads(Path("experiments/reviewed-coverage-feedback-v1.json").read_text())[
        "observations"
    ]
    return cats["early"], cats[stage], fb


@pytest.mark.parametrize("stage,count,chars", [("middle", 9, 546), ("late", 15, 976)])
def test_exact_reviewed_reduction_and_protection_of_every_other_field(stage, count, chars):
    old, target, fb = inputs(stage)
    pristine = deepcopy((old, target, fb))
    base = adapt_result(old, target)
    actual, changes = compile_knowledge(base, target, fb)
    restored = deepcopy(actual)
    before = {t["tool_id"]: t for t in base["knowledge"]["tools"]}
    assert (
        sum(
            len(before[t["tool_id"]]["description"]) - len(t["description"])
            for t in actual["tools"]
        )
        == chars
    )
    assert len(changes) == count
    for t in restored["tools"]:
        t["description"] = before[t["tool_id"]]["description"]
    assert restored == base["knowledge"] and (old, target, fb) == pristine


@pytest.mark.parametrize(
    "mutation", ["policy_text", "policy_line", "duplicate", "missing", "new_qualifier", "schema"]
)
def test_tampered_policy_or_contract_never_silently_applies(mutation):
    old, target, fb = inputs()
    row = next(r for r in fb if r["stage"] == "late")
    if mutation == "policy_text":
        row["result"]["deletions"][0]["text"] += " extra"
    elif mutation == "policy_line":
        row["result"]["deletions"][0]["line"] = 0
    elif mutation == "duplicate":
        fb.append(deepcopy(row))
    elif mutation == "missing":
        fb = []
    elif mutation == "new_qualifier":
        next(t for t in target["tools"] if t["name"] == "parallel-thinking")["description"] += (
            "\nNever discard this qualifier."
        )
    else:
        next(t for t in target["tools"] if t["name"] == "parallel-thinking")["parameters"][
            "properties"
        ]["pathStatus"]["enum"].append("paused")
    with pytest.raises(ValueError):
        compile_knowledge(adapt_result(old, target), target, fb)


def test_early_math_and_retention_are_exact_sp_without_a_policy():
    old, _, _ = inputs()
    base = adapt_result(old, old)
    assert compile_knowledge(base, old, []) == (base["knowledge"], [])
    for path, key in [
        ("tests/fixtures/semantic-maintenance-catalogs.json", None),
        ("tests/fixtures/prefix-workflow-catalogs.json", "235"),
    ]:
        cats = json.loads(Path(path).read_text())
        if key:
            cats = cats[key]
        base = adapt_result(cats["early"], cats["late"])
        assert compile_knowledge(base, cats["late"], []) == (base["knowledge"], [])


def test_registered_adapter_is_deterministic_and_uses_no_updater_call():
    old, target, fb = inputs()
    r = variant(old, target, "reviewed_coverage", {"feedback": fb})
    assert r["validation"]["errors"] == [] and r["cost"]["calls"] == 0
    assert r["knowledge"] == compile_knowledge(adapt_result(old, target), target, fb)[0]

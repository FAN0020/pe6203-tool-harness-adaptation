"""Workflow abstraction, contract isolation and benchmark leakage boundaries."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pe6203.baselines import adapt
from pe6203.runner import prepare_tools
from pe6203.selective import adapt_result as base_patch

ROOT = Path(__file__).parents[1]
SERVER = "slidev-mcp::create_bulk_slides"


def inputs(stage="late", task=457):
    catalogs = json.loads((ROOT / "tests/fixtures/prefix-workflow-catalogs.json").read_text())[
        str(task)
    ]
    old, new = [deepcopy(catalogs[v]) for v in ("early", stage)]
    context = {
        "feedback": json.loads((ROOT / "experiments/prefix-workflow-feedback-v1.json").read_text())[
            "observations"
        ]
    }
    return old, new, context


@pytest.mark.parametrize("stage", ["middle", "late"])
def test_single_program_description_and_unchanged_contracts(stage):
    old, new, context = inputs(stage)
    pristine = deepcopy((old, new, context))
    knowledge, changes, cost = adapt(old, new, "prefix_workflow_memory", context)
    base = base_patch(old, new)["knowledge"]
    aa, bb = [{t["tool_id"]: t for t in k["tools"]} for k in (base, knowledge)]
    delta = [(key, field) for key in aa for field in aa[key] if aa[key][field] != bb[key][field]]
    assert delta == [(SERVER, "description")]
    program = json.loads(bb[SERVER]["description"].split("\nVerified procedural memory:\n")[1])
    assert len(program["steps"]) == 7
    assert program["steps"][2]["repeat"] == "for each subsequent intended slide"
    assert len([c for c in changes if c["operation"] == "attach_induced_workflow"]) == 1
    x, xr = prepare_tools(base["tools"], "selective_patch", "namespaced")
    y, yr = prepare_tools(knowledge["tools"], "prefix_workflow_memory", "namespaced")
    assert xr == yr
    assert [t["function"]["parameters"] for t in x] == [t["function"]["parameters"] for t in y]
    assert cost["calls"] == cost["total_tokens"] == cost["usd"] == 0
    assert (old, new, context) == pristine
    encoded = json.dumps(program)
    for leaked in [
        "772519",
        "816271",
        "CANARY",
        "Train Document",
        "heldout",
        "457",
        "4096",
        "PaLM",
        "/Users/",
    ]:
        assert leaked not in encoded


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "failed", "body", "stage", "heldout"])
def test_only_exact_verified_training_is_accepted(mutation):
    old, new, context = inputs()
    rows = context["feedback"]
    if mutation == "missing":
        rows.pop()
    elif mutation == "duplicate":
        rows.append(deepcopy(rows[-1]))
    elif mutation == "failed":
        rows[-1]["result"]["trace"][0]["result"]["isError"] = True
    elif mutation == "body":
        rows[-1]["result"]["trace"][1]["arguments"]["content"] = "substitute"
    elif mutation == "stage":
        rows[-1]["stage"] = "middle"
    else:
        rows[-1]["result"]["trace"][0]["case"] = "heldout"
    with pytest.raises(ValueError, match="training"):
        adapt(old, new, "prefix_workflow_memory", context)


def test_early_and_retention_are_exact_baseline():
    for stage, task in [("early", 457), ("late", 235)]:
        old, new, _ = inputs(stage, task)
        assert adapt(old, new, "prefix_workflow_memory", {})[0] == base_patch(old, new)["knowledge"]


def test_unknown_contract_rejected():
    old, new, context = inputs()
    next(t for t in new["tools"] if t["tool_id"] == "slidev-mcp::add_page")["parameters"][
        "required"
    ].append("new_param")
    with pytest.raises(ValueError, match="contract"):
        adapt(old, new, "prefix_workflow_memory", context)


def test_task_answer_never_accepted():
    old, new, context = inputs()
    context["question"] = "forbidden task material"
    with pytest.raises(ValueError, match="task and score inputs are forbidden"):
        adapt(old, new, "prefix_workflow_memory", context)


@pytest.mark.parametrize("field", ["description", "parameters", "routing", "usage_rules"])
def test_extra_edit_rejected(field):
    from pe6203.prefix_workflow_memory import validate_workflow

    old, new, context = inputs()
    candidate, _, _ = adapt(old, new, "prefix_workflow_memory", context)
    row = candidate["tools"][0]
    if field == "description":
        row[field] += "extra"
    elif field == "usage_rules":
        row[field].append("extra")
    else:
        row[field]["extra"] = True
    assert validate_workflow(candidate, old, new, base_patch(old, new), context["feedback"])[
        "errors"
    ]


def test_induced_program_expansion_matches_reserved_native_actions():
    from pe6203.prefix_workflow_memory import expand_workflow, induce_workflow

    _, _, context = inputs()
    program = induce_workflow(context["feedback"][-1]["result"]["trace"])
    folder = ROOT / "results/evidence/prefix-workflow-admission-20261101"
    rows = [
        x
        for x in json.loads((folder / "observations.json").read_text())
        if x["stage"] == "late" and x["case"] == "heldout"
    ]
    # Only the independently specified mid-write durability challenge has no training analogue.
    expected = [{"call": x["tool"], "args": x["arguments"]} for i, x in enumerate(rows) if i != 3]
    pages = json.loads((folder / "cases.json").read_text())["heldout"]
    expanded = expand_workflow(program, rows[0]["arguments"], [p["body"] for p in pages])
    assert expanded == expected

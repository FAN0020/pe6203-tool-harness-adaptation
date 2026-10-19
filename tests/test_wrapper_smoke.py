import copy

import pytest

from fixtures.baseline_cases import all_cases
from integration.baseline_wrapper import run_baseline_once


def fake_adapt(
    old_knowledge,
    new_metadata,
    strategy,
    context=None,
):
    """临时模拟队友的 adapt 函数。"""

    if strategy == "no_update":
        new_knowledge = copy.deepcopy(old_knowledge)
        operations = []

    elif strategy == "full_rewrite":
        new_knowledge = {"tools": copy.deepcopy(new_metadata["tools"])}
        operations = [
            {
                "operation": "full_rewrite",
                "tool_count": len(new_metadata["tools"]),
            }
        ]

    else:
        raise ValueError(f"Unsupported strategy: {strategy}")

    update_cost = {
        "model_calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "api_cost_usd": 0.0,
        "elapsed_seconds": 0.001,
        "update_operations": len(operations),
    }

    diff_log = {
        "strategy": strategy,
        "operations": operations,
    }

    return new_knowledge, diff_log, update_cost


@pytest.mark.parametrize(
    "case",
    all_cases(),
    ids=lambda case: case["name"],
)
@pytest.mark.parametrize(
    "strategy",
    ["no_update", "full_rewrite"],
)
def test_wrapper_with_fake_adapt(case, strategy):
    record = run_baseline_once(
        adapt_fn=fake_adapt,
        old_knowledge=copy.deepcopy(case["old_knowledge"]),
        raw_new_metadata=copy.deepcopy(case["new_metadata"]),
        strategy=strategy,
        context=None,
    )

    assert record["strategy"] == strategy
    assert record["metadata_version"] == "new"
    assert "new_knowledge" in record
    assert "diff_log" in record
    assert "update_cost" in record

    actual_names = {tool["name"] for tool in record["new_knowledge"]["tools"]}

    expected_key = f"expected_{strategy}_tools"
    expected_names = set(case[expected_key])

    assert actual_names == expected_names

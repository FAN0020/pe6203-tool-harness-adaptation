"""Local integration checks using the teammate's real baseline implementation.

These checks use synthetic metadata, not Group A's benchmark runner.
"""

import json
from copy import deepcopy

import pytest

from fixtures.baseline_cases import all_cases
from integration.baseline_wrapper import run_baseline_once
from integration.baselines import adapt, build_knowledge

pytestmark = pytest.mark.usefixtures("mock_baseline_llm")


@pytest.mark.parametrize("case", all_cases(), ids=lambda case: case["name"])
@pytest.mark.parametrize("strategy", ["no_update", "full_rewrite"])
def test_real_adapt_through_wrapper(case, strategy):
    # Construct both strategies' initial knowledge using the same builder.
    old_knowledge = build_knowledge(case["old_metadata"])
    old_before = deepcopy(old_knowledge)
    new_metadata = deepcopy(case["new_metadata"])
    new_before = deepcopy(new_metadata)

    record = run_baseline_once(
        adapt_fn=adapt,
        old_knowledge=old_knowledge,
        raw_new_metadata=new_metadata,
        strategy=strategy,
    )

    assert old_knowledge == old_before
    assert new_metadata == new_before
    assert record["strategy"] == strategy
    assert record["metadata_version"] == new_metadata["version"]
    knowledge = record["new_knowledge"]
    assert {block["name"] for block in knowledge["tools"]} == set(
        case[f"expected_{strategy}_tools"]
    )

    if strategy == "no_update":
        assert knowledge == old_before
        assert record["diff_log"] == []
        assert record["update_cost"]["update_operations"] == 0
    else:
        # Compare full records, so parameter and description changes are checked.
        for block, expected in zip(knowledge["tools"], new_before["tools"], strict=True):
            assert block["metadata"] == {
                **expected,
                "description": "Rewritten: " + expected["description"],
            }
        for block in knowledge["tools"]:
            assert block["name"] == block["metadata"]["name"]
            assert json.loads(block["text"]) == block["metadata"]
        assert record["update_cost"]["update_operations"] == len(new_before["tools"])
        assert record["diff_log"][0]["operation"] == "llm_full_rewrite"
        assert record["diff_log"][0]["rebuilt_blocks"] == len(new_before["tools"])

    if strategy == "no_update":
        for field in ("model_calls", "input_tokens", "output_tokens", "api_cost_usd"):
            assert record["update_cost"][field] == 0
    else:
        assert record["update_cost"]["model_calls"] == 1
        assert record["update_cost"]["input_tokens"] == 101
        assert record["update_cost"]["output_tokens"] == 50
        assert record["update_cost"]["api_cost_usd"] is None

    # Returned knowledge must not alias either input.
    if knowledge["tools"]:
        knowledge["tools"][0]["metadata"]["description"] = "modified output"
    assert old_knowledge == old_before
    assert new_metadata == new_before

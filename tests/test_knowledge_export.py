"""File-interface validation with real released metadata; no model or MCP calls."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from integration.export_baseline_knowledge import adapt_for_runner, validate_envelope

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.usefixtures("mock_baseline_llm")


def metadata(stage):
    return json.loads((ROOT / f"examples/metadata/{stage}.json").read_text())


@pytest.mark.parametrize("stage", ["middle", "late"])
@pytest.mark.parametrize("strategy", ["no_update", "full_rewrite"])
def test_real_catalog_export(stage, strategy):
    old, target = metadata("early"), metadata(stage)
    before = deepcopy((old, target))
    knowledge, record = adapt_for_runner(old, target, strategy)
    expected = old if strategy == "no_update" else target
    if strategy == "no_update":
        assert knowledge == expected
    else:
        for actual, target_tool in zip(knowledge["tools"], target["tools"], strict=True):
            assert actual == {
                **target_tool,
                "description": "Rewritten: " + target_tool["description"],
            }
    assert (old, target) == before
    assert all("metadata" not in tool and "text" not in tool for tool in knowledge["tools"])
    assert record["update_cost"]["update_operations"] == (
        0 if strategy == "no_update" else len(target["tools"])
    )
    knowledge["tools"][0]["description"] = "changed output"
    assert (old, target) == before


@pytest.mark.parametrize("defect", ["commit", "version", "routing", "duplicate", "missing"])
def test_rejects_incompatible_metadata(defect):
    old, target = metadata("early"), metadata("late")
    if defect == "commit":
        target["benchmark_commit"] = "different"
    elif defect == "version":
        target["tools"][0]["version"] = "middle"
    elif defect == "routing":
        target["tools"][0]["routing"]["server_id"] = "other"
    elif defect == "duplicate":
        target["tools"].append(deepcopy(target["tools"][0]))
    else:
        del target["tools"][0]["parameters"]
    with pytest.raises(ValueError):
        adapt_for_runner(old, target, "full_rewrite")


def test_rejects_prototype_blocks_as_toolrecords():
    envelope = metadata("early")
    envelope["tools"] = [{"name": "tool", "metadata": {}, "text": "{}"}]
    with pytest.raises(ValueError):
        validate_envelope(envelope)

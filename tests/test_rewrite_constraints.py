"""Semantic regressions from the published pilot; no external model calls."""

import copy
import json
from pathlib import Path

import pytest

from integration import baselines
from integration.rewrite_constraints import (
    POLICY_VERSION,
    RewriteConstraintError,
    build_rewrite_checks,
    validate_description,
)
from pe6203.baselines import adapt as common_adapt


def tool(name="remember", maximum=50):
    return {
        "name": name,
        "description": "Create a memory",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": f"Short title (max {maximum} characters for file organization)",
                }
            },
            "required": ["title"],
        },
        "usage_rules": [],
    }


def completion(messages, description):
    tools = json.loads(messages[-1]["content"])["tools"]
    return {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "content": json.dumps(
                        {
                            "tools": [
                                {
                                    "name": t["name"],
                                    "description": description,
                                    "usage_rules": t.get("usage_rules", []),
                                }
                                for t in tools
                            ]
                        }
                    )
                },
            }
        ],
        "usage": {"prompt_tokens": 20, "completion_tokens": 10, "cost": 0.004},
    }


@pytest.mark.parametrize(
    "description",
    [
        "Create a memory; title has a maximum of 50 characters.",
        "Create a memory with a title of 50 characters or less.",
        "The title must not exceed 50 characters.",
    ],
)
def test_accepts_strong_equivalent_limit_wording(monkeypatch, description):
    data = {"tools": [tool()]}
    before = copy.deepcopy(data)
    monkeypatch.setattr(
        baselines,
        "_request_completion",
        lambda messages, settings: completion(messages, description),
    )
    knowledge, log, cost = baselines.adapt({}, data, "full_rewrite")
    assert knowledge["tools"][0]["metadata"]["description"] == description
    assert data == before and cost["api_cost_usd"] == 0.004
    assert log[0]["validation"]["rewrite_policy"] == POLICY_VERSION
    assert log[0]["validation"]["semantic_grounding"] == "requires_human_review"


@pytest.mark.parametrize(
    "description",
    [
        "Create a memory; title max 50 characters recommended.",
        "Create a memory; title maximum 50 characters is a soft limit.",
        "Create a memory; title has a maximum of 500 characters.",
        "Create a memory with a short title.",
    ],
)
def test_rejects_weakened_missing_or_wrong_limit_and_retains_cost(
    tmp_path, monkeypatch, description
):
    audit = tmp_path / "audit.json"
    calls = []

    def provider(messages, settings):
        calls.append(messages)
        return completion(messages, description)

    monkeypatch.setattr(baselines, "_request_completion", provider)
    with pytest.raises(baselines.AdaptationError) as error:
        baselines.adapt({}, {"tools": [tool()]}, "full_rewrite", {"audit_path": str(audit)})
    receipt = json.loads(audit.read_text())
    assert len(calls) == 1
    assert receipt["status"] == "failed" and receipt["validation_issues"]
    assert receipt["response"]["usage"]["cost"] == 0.004
    assert receipt["update_cost"]["api_cost_usd"] == 0.004
    assert receipt["update_cost"]["update_operations"] == 0
    assert error.value.audit["rewrite_policy"] == POLICY_VERSION


def test_extracts_other_numbers_and_does_not_invent_hard_advisory_limits():
    item = tool(maximum=72)
    checks = build_rewrite_checks([item])
    assert checks[0]["character_limits"][0]["max_characters"] == 72
    validate_description("title has a maximum of 72 characters.", checks[0])
    item["parameters"]["properties"]["title"]["description"] = (
        "A max 72 characters title is recommended."
    )
    assert build_rewrite_checks([item]) == []
    item["parameters"]["properties"]["title"]["maxLength"] = 72
    assert build_rewrite_checks([item])[0]["character_limits"][0]["source"].endswith(".maxLength")


@pytest.mark.parametrize("nullable", [False, True])
def test_null_conflict_uses_actual_schema_and_keeps_original_metadata(nullable):
    item = {
        "name": "update_task",
        "parameters": {
            "type": "object",
            "properties": {
                "parentId": {
                    "type": ["string", "null"] if nullable else "string",
                    "description": "Use null/empty to move to top level",
                }
            },
        },
    }
    before = copy.deepcopy(item)
    checks = build_rewrite_checks([item])
    if nullable:
        assert checks == []
    else:
        assert checks[0]["metadata_conflicts"][0]["field"] == "parentId"
        with pytest.raises(RewriteConstraintError):
            validate_description("Use parentId null/empty to move to top level.", checks[0])
        validate_description(
            "parentId must be a string; use an empty string for top level.", checks[0]
        )
    assert item == before


def test_shared_entrypoint_rejects_weakening_without_schema_changes(monkeypatch):
    record = {
        **tool(),
        "tool_id": "server::remember",
        "server_id": "server",
        "version": "early",
        "routing": {"server_id": "server", "tool_name": "remember"},
    }
    old = {
        "schema_version": "1.0",
        "benchmark_commit": "pin",
        "version": "early",
        "tools": [record],
    }
    target = copy.deepcopy(old)
    target["version"] = target["tools"][0]["version"] = "middle"
    before = copy.deepcopy((old, target))
    monkeypatch.setattr(
        baselines,
        "_request_completion",
        lambda messages, settings: completion(messages, "title max 50 characters recommended."),
    )
    with pytest.raises(baselines.AdaptationError):
        common_adapt(old, target, "full_rewrite")
    assert (old, target) == before


def test_no_update_bypasses_rewrite_checks(monkeypatch):
    def forbidden(*args):
        pytest.fail("No Update attempted rewriting/constraint extraction")

    monkeypatch.setattr(baselines, "build_rewrite_checks", forbidden)
    monkeypatch.setattr(baselines, "_request_completion", forbidden)
    old = {"tools": [{"anything": "Keep old knowledge exactly"}]}
    knowledge, log, cost = baselines.adapt(old, None, "no_update")
    assert knowledge == old and log == [] and cost["model_calls"] == 0


def test_guard_detects_all_three_published_review_candidates():
    root = Path(__file__).resolve().parents[1] / "results/evidence/full-rewrite-20261019"
    original = json.loads((root / "target-metadata.json").read_text())
    historical = {t["name"]: t for t in json.loads((root / "knowledge.json").read_text())["tools"]}
    flagged = {}
    for check in build_rewrite_checks(original["tools"]):
        with pytest.raises(RewriteConstraintError) as error:
            validate_description(historical[check["name"]]["description"], check)
        flagged[check["name"]] = error.value.issues[0]["issue"]
    assert flagged == {
        "update_task": "null_conflict_repeated_in_description",
        "create_memory": "character_limit_weakened",
        "update_memory": "character_limit_weakened",
    }

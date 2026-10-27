"""Billing regressions use mock HTTP responses only, never paid endpoints."""

import asyncio
import json
from contextlib import asynccontextmanager

import httpx
import pytest
from openai import AsyncOpenAI

from integration import baselines
from pe6203 import runner
from pe6203.costs import provider_usd, sum_usd


@pytest.mark.parametrize("value", [None, True, False, -1, "0.02", float("nan"), float("inf")])
def test_invalid_provider_charges_remain_unknown(value):
    assert provider_usd({"cost": value}) is None
    assert sum_usd([0.01, value]) is None


def test_real_zero_missing_and_decimal_totals_are_distinct():
    assert provider_usd({"cost": 0}) == 0
    assert provider_usd({"cost_details": {"upstream_inference_cost": 1}}) is None
    assert provider_usd(None) is None
    assert sum_usd([0.1, 0.2, 0]) == 0.3
    assert sum_usd([]) is None
    assert sum_usd([1e308, 1e308]) is None


def test_partial_usage_does_not_publish_an_understated_total():
    first = {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12, "cost": 0.01}
    full = runner.usage_total([first, {**first, "cost": 0}])
    assert full["usd"] == full["known_usd"] == 0.01
    assert full["total_tokens"] == 24
    partial = runner.usage_total([first, {}])
    assert partial["usd"] is None and partial["total_tokens"] is None
    assert partial["known_usd"] == 0.01
    assert runner.usage_total([])["usd"] is None


@pytest.mark.parametrize("bad_output", [False, True])
def test_updater_preserves_reported_cost_before_validation(monkeypatch, tmp_path, bad_output):
    data = {
        "tools": [
            {"name": "lookup", "description": "Original", "parameters": {}, "usage_rules": []}
        ]
    }
    payload = {
        "tools": []
        if bad_output
        else [{"name": "lookup", "description": "Rewritten", "usage_rules": []}]
    }
    response = {
        "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(payload)}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 2, "cost": 0.00311928},
    }
    monkeypatch.setattr(baselines, "_request_completion", lambda *args: response)
    path = tmp_path / "update-audit.json"
    if bad_output:
        with pytest.raises(baselines.AdaptationError) as error:
            baselines.adapt({}, data, "full_rewrite", {"audit_path": str(path)})
        cost = error.value.audit["update_cost"]
        assert cost["update_operations"] == 0
    else:
        _, _, cost = baselines.adapt({}, data, "full_rewrite", {"audit_path": str(path)})
    assert cost["api_cost_usd"] == 0.00311928
    audit = json.loads(path.read_text())
    assert audit["update_cost"]["api_cost_usd"] == 0.00311928
    assert audit["api_cost_source"] == "provider_usage.cost"


@pytest.mark.parametrize("charge", [None, True, -1, "0.1", float("nan"), 0])
def test_updater_does_not_coerce_missing_or_invalid_cost(monkeypatch, charge):
    data = {"tools": [{"name": "lookup", "description": "Original"}]}
    response = {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "content": json.dumps(
                        {
                            "tools": [
                                {"name": "lookup", "description": "Rewritten", "usage_rules": []}
                            ]
                        }
                    )
                },
            }
        ],
        "usage": {"cost": charge},
    }
    monkeypatch.setattr(baselines, "_request_completion", lambda *args: response)
    _, _, cost = baselines.adapt({}, data, "full_rewrite")
    assert cost["api_cost_usd"] == (0 if type(charge) is int and charge == 0 else None)


def setup_runner(tmp_path, monkeypatch, handler):
    record = {
        "tool_id": "server::lookup",
        "server_id": "server",
        "name": "lookup",
        "version": "early",
        "parameters": {"type": "object", "properties": {}},
        "description": "Lookup",
        "usage_rules": [],
        "routing": {"server_id": "server", "tool_name": "lookup"},
    }
    metadata = {"benchmark_commit": "pin", "version": "early", "tools": [record]}
    knowledge = tmp_path / "knowledge.json"
    knowledge.write_text(json.dumps(metadata))
    monkeypatch.setattr(
        runner,
        "source",
        lambda root: (
            {"commit": "pin", "dataset_revision": "release", "stages": {"early": {}}},
            tmp_path,
        ),
    )
    monkeypatch.setattr(
        runner,
        "load_task",
        lambda *args: {"idx": 139, "question": "Task", "servers": {"server": ["lookup"]}},
    )
    monkeypatch.setattr(runner, "server_profiles", lambda *args: {"server": {}})
    monkeypatch.setattr(
        runner, "credentials", lambda config: ("fixture-key", "https://fixture.invalid/v1")
    )

    @asynccontextmanager
    async def sessions(*args):
        yield {}

    async def snapshot(*args):
        return metadata

    monkeypatch.setattr(runner, "sessions", sessions)
    monkeypatch.setattr(runner, "snapshot", snapshot)
    monkeypatch.setattr(runner, "official_prompt", lambda *args: "Fixture judge prompt")
    monkeypatch.setattr(
        runner,
        "AsyncOpenAI",
        lambda **kwargs: AsyncOpenAI(
            **kwargs, http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
        ),
    )
    role = {"model": "fixture", "temperature": 0, "max_completion_tokens": 64}
    return {
        "root": str(tmp_path),
        "knowledge_path": str(knowledge),
        "output_dir": str(tmp_path / "run"),
        "agent": role,
        "judge": role,
        "judge_runs": 2,
        "max_rounds": 2,
        "request_timeout_seconds": 10,
        "run_timeout_seconds": 30,
        "update_cost": {"tokens": 0, "seconds": 0, "usd": 0},
    }


def response(message, cost):
    return httpx.Response(
        200,
        json={
            "id": "fixture",
            "object": "chat.completion",
            "created": 1,
            "model": "fixture",
            "choices": [
                {
                    "index": 0,
                    "message": message,
                    "finish_reason": "tool_calls" if message.get("tool_calls") else "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 2,
                "total_tokens": 12,
                "cost": cost,
            },
        },
    )


@pytest.mark.parametrize("bad_judge", [False, True])
def test_runner_retains_billing_for_unparseable_judges(tmp_path, monkeypatch, bad_judge):
    def handler(request):
        body = json.loads(request.content)
        if "tools" in body:
            return response({"role": "assistant", "content": "Done"}, 0.01)
        content = (
            "not JSON"
            if bad_judge
            else json.dumps({"task_fulfillment": 8, "grounding": 9, "planning_and_efficiency": 7})
        )
        return response({"role": "assistant", "content": content}, 0.02)

    config = setup_runner(tmp_path, monkeypatch, handler)
    trace, result = runner.run(139, "early", "no_update", 0, config)
    assert result["cost"]["agent"]["usd"] == 0.01
    assert result["cost"]["judge"]["usd"] == 0.04
    assert result["cost"]["usd"] == 0.05
    assert result["cost"]["usd_source"] == "sum_of_recorded_stage_usd"
    assert result["judge_status"] == ("incomplete" if bad_judge else "complete")
    assert len([e for e in trace["events"] if e["type"] == "judge_result"]) == 2
    assert json.loads((tmp_path / "run/result.json").read_text())["cost"] == result["cost"]


def test_later_agent_timeout_retains_known_cost_and_unknown_total(tmp_path, monkeypatch):
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 2:
            raise httpx.ReadTimeout("Fixture timeout")
        return response(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "c1",
                        "type": "function",
                        "function": {"name": "lookup", "arguments": "{}"},
                    }
                ],
            },
            0.01,
        )

    config = setup_runner(tmp_path, monkeypatch, handler)
    trace, result = runner.run(139, "early", "no_update", 0, config)
    assert len(calls) == 2
    assert result["cost"]["agent"]["known_usd"] == 0.01
    assert result["cost"]["agent"]["usd"] is None
    assert result["cost"]["usd"] is None
    assert result["execution_status"] == "failed"
    assert any(e["type"] == "agent_error" for e in trace["events"])


def test_judge_cancellation_cannot_publish_partial_fees_as_total(tmp_path, monkeypatch):
    judge_calls = []

    async def handler(request):
        body = json.loads(request.content)
        if "tools" in body:
            return response({"role": "assistant", "content": "Done"}, 0.01)
        judge_calls.append(request)
        if len(judge_calls) == 2:
            await asyncio.sleep(10)
        content = json.dumps({"task_fulfillment": 8, "grounding": 9, "planning_and_efficiency": 7})
        return response({"role": "assistant", "content": content}, 0.02)

    config = setup_runner(tmp_path, monkeypatch, handler)
    config["run_timeout_seconds"] = 0.5
    trace, result = runner.run(139, "early", "no_update", 0, config)
    assert len(judge_calls) == 2
    assert result["status"] == "timeout"
    assert result["cost"]["judge"]["known_usd"] == 0.02
    assert result["cost"]["judge"]["usd"] is None
    assert result["cost"]["usd"] is None
    assert any(
        event["type"] == "judge_result" and event.get("error", "").startswith("CancelledError")
        for event in trace["events"]
    )

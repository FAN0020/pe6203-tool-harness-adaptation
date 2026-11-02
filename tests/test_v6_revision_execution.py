"""Offline SDK/MCP doubles for the opt-in V6 delivery protocol."""

import copy
import json
from types import SimpleNamespace

import httpx
import pytest
from jsonschema import Draft202012Validator
from openai import AsyncOpenAI

from pe6203 import artifact_validation, runner
from pe6203.execution_control_v6 import VERSION, artifact_response_format, settings

TOOL = {"type": "function", "function": {
    "name": "lookup", "description": "Look up evidence",
    "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
}}
CALL = {"role": "assistant", "content": None, "tool_calls": [
    {"id": "call-1", "type": "function", "function": {"name": "lookup", "arguments": "{}"}},
]}


def config(rounds=3, enabled=True, artifact=False):
    value = {"max_rounds": rounds, "agent": {"model": "fixture", "temperature": 0,
              "max_completion_tokens": 128}, "request_retry": {"max_retries": 0}}
    if enabled:
        value["v6_execution_control"] = {"version": VERSION}
    if artifact:
        value["artifact_validation"] = {
            "version": "artifact-v1", "image": "fixture@sha256:" + "a" * 64, "tests": [],
        }
    return value


def completion(message, finish="stop"):
    return httpx.Response(200, json={
        "id": "offline", "object": "chat.completion", "created": 0, "model": "fixture",
        "choices": [{"index": 0, "message": message, "finish_reason": finish}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10, "cost": 0.001},
    })


async def exercise(tmp_path, responses, cfg, monkeypatch=None, validate=None):
    captured, events = [], []
    queue = list(responses)

    async def handler(request):
        captured.append(json.loads(request.content))
        message, finish = queue.pop(0)
        return completion(copy.deepcopy(message), finish)

    class Server:
        def __init__(self):
            self.calls = 0

        async def call_tool(self, name, args):
            self.calls += 1
            return SimpleNamespace(model_dump=lambda **_: {
                "content": [{"type": "text", "text": "observed evidence"}], "isError": False,
            })

    server = Server()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    if validate is not None:
        monkeypatch.setattr(artifact_validation, "validate", validate)
    async with AsyncOpenAI(api_key="offline-test-only", base_url="https://fixture.test/v1",
                          http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
                          max_retries=0) as client:
        outcome = await runner.agent_loop(
            client, {"fixture": server}, [TOOL],
            {"lookup": {"server_id": "fixture", "tool_name": "lookup"}},
            "Return the requested result", workspace, cfg, 1, events.append,
        )
    return outcome, captured, events, server


@pytest.mark.asyncio
async def test_default_protocol_keeps_request_shape_and_system_prompt(tmp_path):
    out, requests, events, server = await exercise(
        tmp_path, [(CALL, "tool_calls"), ({"role": "assistant", "content": "done"}, "stop")],
        config(rounds=2, enabled=False))
    assert out["status"] == "completed" and len(requests) == 2 and server.calls == 1
    assert not any("tool_choice" in r or "response_format" in r for r in requests)
    assert requests[0]["messages"][0]["content"] == (
        "You are an AI agent connected to MCP tools. Complete the user's task using "
        "the supplied tools. Do not ask the user follow-up questions. Use only the tools "
        "and schemas supplied to you. Do not invent successful tool results. "
        f"All workingDirectory arguments must be exactly: {tmp_path / 'workspace'}")
    assert not any(e["type"].startswith("v6_") for e in events)
    assert "v6_execution_control" not in out


@pytest.mark.asyncio
async def test_final_round_reserved_within_existing_budget_and_observations_retained(tmp_path):
    out, requests, events, server = await exercise(
        tmp_path, [(CALL, "tool_calls"), (CALL, "tool_calls"),
                   ({"role": "assistant", "content": "delivered"}, "stop")], config())
    assert len(requests) == out["rounds"] == 3 and server.calls == 2
    assert all("tool_choice" not in r for r in requests[:2])
    assert requests[-1]["tool_choice"] == "none"
    assert sum(m["role"] == "tool" for m in requests[-1]["messages"]) == 2
    assert all("response_format" not in r for r in requests)
    assert out["status"] == "completed"
    assert (tmp_path / "v6-execution-control-frozen.json").is_file()
    final_event = next(e for e in events if e["type"] == "v6_final_generation_round")
    assert final_event["round"] == final_event["max_rounds"] == 3


@pytest.mark.asyncio
async def test_early_nonartifact_answer_does_not_force_another_round(tmp_path):
    out, requests, _, _ = await exercise(
        tmp_path, [({"role": "assistant", "content": "enough evidence; delivered"}, "stop")], config())
    assert out["status"] == "completed" and out["rounds"] == len(requests) == 1
    assert "tool_choice" not in requests[0] and "response_format" not in requests[0]


@pytest.mark.asyncio
async def test_length_finish_is_retained_without_extra_delivery_request(tmp_path):
    out, requests, _, _ = await exercise(
        tmp_path, [({"role": "assistant", "content": "partial"}, "length")], config())
    assert out["status"] == "output_truncated" and out["answer"] == "partial"
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_provider_cannot_execute_tool_calls_in_reserved_round(tmp_path, monkeypatch):
    checked = []
    monkeypatch.setattr(runner, "check_arguments", lambda *args: checked.append(args))
    with pytest.raises(ValueError, match="reserved final generation round"):
        await exercise(tmp_path, [(CALL, "tool_calls")], config(rounds=1))
    assert checked == []


@pytest.mark.asyncio
async def test_artifact_format_applies_to_early_final_answer_and_existing_repair(tmp_path, monkeypatch):
    source = {"artifact": {"path": "artifact.py", "language": "python", "source": "pass\n"},
              "summary": "untested example"}
    validated = []

    async def validate(answer, protocol, output, repair):
        validated.append(json.loads(answer))
        fixed = await repair({"observed_failure": "offline format test"})
        validated.append(json.loads(fixed))
        return {"accepted_artifact": None, "status": "no_artifact", "latest_artifact": None,
                "repairs": 1}

    cfg = config(rounds=3, artifact=True)
    out, requests, _, _ = await exercise(tmp_path, [
        ({"role": "assistant", "content": json.dumps(source)}, "stop"),
        ({"role": "assistant", "content": json.dumps(source)}, "stop"),
    ], cfg, monkeypatch, validate)
    assert len(requests) == 2 and out["rounds"] == 1
    assert all(r["response_format"] == artifact_response_format() for r in requests)
    assert "tools" in requests[0] and "tool_choice" not in requests[0]
    assert "tools" not in requests[1] and "tool_choice" not in requests[1]
    assert requests[1]["max_completion_tokens"] == 4096
    assert validated == [source, source]
    assert out["status"] == "artifact_unaccepted"  # Stub does not claim actual test success.


def test_schema_keeps_summary_top_level_and_rejects_additional_fields():
    schema = artifact_response_format()["json_schema"]["schema"]
    validator = Draft202012Validator(schema)
    good = {"artifact": {"path": "artifact.py", "language": "python", "source": "pass\n"},
            "summary": "not executed"}
    assert validator.is_valid(good)
    assert not validator.is_valid({"artifact": {**good["artifact"], "summary": "nested"}})
    assert not validator.is_valid({**good, "validation": "invented success"})


def test_protocol_configuration_rejects_unsupported_knobs():
    assert settings(None, 12) is None
    for value in (True, {}, {"version": VERSION, "extra_rounds": 1}, {"version": "unknown"}):
        with pytest.raises(ValueError):
            settings(value, 12)

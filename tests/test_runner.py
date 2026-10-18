"""Only the external model HTTP endpoint and MCP call boundary are doubled here."""

import json
from types import SimpleNamespace

import httpx
import pytest
from openai import AsyncOpenAI
from test_contract import module, record


def completion(message, tokens=12):
    return httpx.Response(
        200,
        json={
            "id": "fixture",
            "object": "chat.completion",
            "created": 1,
            "model": "fixture-model",
            "choices": [
                {
                    "index": 0,
                    "message": message,
                    "finish_reason": "tool_calls" if message.get("tool_calls") else "stop",
                }
            ],
            "usage": {"prompt_tokens": tokens, "completion_tokens": 3, "total_tokens": tokens + 3},
        },
    )


@pytest.mark.asyncio
async def test_agent_dispatches_frozen_route_and_returns_full_trace(tmp_path):
    requests, events = [], []

    def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        if len(requests) == 1:
            return completion(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {"name": "old_tool", "arguments": '{"value": 2}'},
                        }
                    ],
                }
            )
        assert body["messages"][-1] == {
            "role": "tool",
            "tool_call_id": "call-1",
            "content": '{"isError": false, "content": "REAL-BOUNDARY-RESULT"}',
        }
        return completion({"role": "assistant", "content": "Done"})

    class MCPBoundary:
        async def call_tool(self, name, arguments):
            assert (name, arguments) == ("old_tool", {"value": 2})
            return SimpleNamespace(
                model_dump=lambda **kwargs: {"isError": False, "content": "REAL-BOUNDARY-RESULT"}
            )

    client = AsyncOpenAI(
        api_key="fixture-key",
        base_url="https://model.test/v1",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    m = module("runner")
    tools, routes = m.prepare_tools([record()], "no_update")
    async with client:
        outcome = await m.agent_loop(
            client,
            {"server": MCPBoundary()},
            tools,
            routes,
            "Task",
            tmp_path,
            {
                "agent": {"model": "fixture-model", "temperature": 0, "max_completion_tokens": 64},
                "max_rounds": 3,
                "tool_timeout_seconds": 1,
                "send_model_seed": True,
            },
            42,
            events.append,
        )
    assert outcome["status"] == "completed"
    assert outcome["answer"] == "Done"
    assert len(outcome["messages"]) == 5
    assert outcome["usage"]["total_tokens"] == 30
    assert requests[0]["seed"] == 42
    assert all(r["tools"] == tools for r in requests)
    assert any(e["type"] == "tool_result" for e in events)


@pytest.mark.asyncio
async def test_unknown_tool_is_observation_not_execution_and_round_limit_is_not_success(tmp_path):
    def handler(request):
        return completion(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call-bad",
                        "type": "function",
                        "function": {"name": "new_discovered_tool", "arguments": "{}"},
                    }
                ],
            }
        )

    client = AsyncOpenAI(
        api_key="fixture-key",
        base_url="https://model.test/v1",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    m = module("runner")
    tools, routes = m.prepare_tools([record()], "no_update")
    async with client:
        outcome = await m.agent_loop(
            client,
            {},
            tools,
            routes,
            "Task",
            tmp_path,
            {
                "agent": {"model": "fixture-model", "temperature": 0, "max_completion_tokens": 64},
                "max_rounds": 1,
                "tool_timeout_seconds": 1,
            },
            0,
            lambda e: None,
        )
    assert outcome["status"] == "max_rounds"
    assert outcome["messages"][-1]["tool_call_id"] == "call-bad"
    assert "not in frozen knowledge" in outcome["messages"][-1]["content"]


@pytest.mark.asyncio
async def test_usage_missing_from_provider_remains_unknown(tmp_path):
    def handler(request):
        response = completion({"role": "assistant", "content": "Done"})
        payload = json.loads(response.content)
        payload.pop("usage")
        return httpx.Response(200, json=payload)

    client = AsyncOpenAI(
        api_key="fixture-key",
        base_url="https://model.test/v1",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    m = module("runner")
    tools, routes = m.prepare_tools([record()], "no_update")
    async with client:
        outcome = await m.agent_loop(
            client,
            {},
            tools,
            routes,
            "Task",
            tmp_path,
            {
                "agent": {"model": "fixture-model", "temperature": 0, "max_completion_tokens": 64},
                "max_rounds": 1,
            },
            0,
            lambda e: None,
        )
    assert outcome["usage"]["total_tokens"] is None

"""Exercise the actual upstream loop with fake model/MCP boundaries, no API fees."""

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from openai import AsyncOpenAI

from integration.project_paths import pilot_config_path, task139_metadata_path
from integration.test_real_baselines import DeepSeekClient, upstream_agent_loop
from pe6203 import runner
from pe6203.benchmark import read_json, write_json

ROOT = Path(__file__).resolve().parents[1]


def response(message):
    return httpx.Response(
        200,
        json={
            "id": "mock",
            "object": "chat.completion",
            "created": 1,
            "model": "deepseek-flash",
            "choices": [
                {
                    "index": 0,
                    "message": message,
                    "finish_reason": "tool_calls" if message.get("tool_calls") else "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12},
        },
    )


@pytest.mark.asyncio
async def test_deepseek_parameters():
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        return response({"role": "assistant", "content": "ok"})

    async with DeepSeekClient(
        api_key="fake",
        base_url="https://fixture.invalid/v1",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    ) as c:
        await c.chat.completions.create(
            model="deepseek-flash",
            max_completion_tokens=32,
            messages=[{"role": "user", "content": "hi"}],
        )
    assert seen[0]["max_tokens"] == 32
    assert "max_completion_tokens" not in seen[0]
    assert seen[0]["thinking"] == {"type": "disabled"}


@pytest.mark.asyncio
async def test_upstream_loop_uses_frozen_route_and_records_usage(tmp_path):
    if not (ROOT / ".cache/mcpevol/upstream").is_dir():
        pytest.skip("Requires pinned upstream bootstrap")
    calls, requests, events = [], [], []
    record = read_json(task139_metadata_path(ROOT, "early"))["tools"][0]
    record["name"] = "old_name"
    record["routing"]["tool_name"] = "old_name"
    record["parameters"] = {"type": "object", "properties": {}}
    knowledge_path = tmp_path / "knowledge.json"
    write_json(knowledge_path, {"tools": [record]})

    class MCP:
        async def call_tool(self, name, arguments):
            assert asyncio.get_running_loop() is main_loop
            calls.append((name, arguments))
            return SimpleNamespace(
                content="Tool completed",
                model_dump=lambda **_: {"content": "Tool completed", "isError": False},
            )

    def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        assert [t["function"]["name"] for t in body["tools"]] == ["old_name"]
        if len(requests) == 1:
            return response(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "c1",
                            "type": "function",
                            "function": {"name": "old_name", "arguments": "{}"},
                        }
                    ],
                }
            )
        assert body["messages"][-1]["role"] == "tool"
        return response({"role": "assistant", "content": "Done [FINISH]"})

    config = read_json(pilot_config_path(ROOT))
    config.update(root=str(ROOT), knowledge_path=str(knowledge_path))
    config["agent"]["model"] = "deepseek-flash"
    tools, routes = runner.prepare_tools([record], "no_update")
    main_loop = asyncio.get_running_loop()
    async with AsyncOpenAI(
        api_key="fake",
        base_url="https://fixture.invalid/v1",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    ) as c:
        outcome = await upstream_agent_loop(
            c,
            {record["server_id"]: MCP()},
            tools,
            routes,
            "Do the task",
            tmp_path,
            config,
            0,
            events.append,
        )
    assert calls == [("old_name", {})]
    assert outcome["status"] == "completed"
    assert outcome["usage"]["total_tokens"] == 24
    assert outcome["rounds"] == 2
    assert any(e["type"] == "tool_result" for e in events)
    assert any(e["type"] == "upstream_agent_bridge" for e in events)


@pytest.mark.asyncio
async def test_upstream_model_error_is_not_success(tmp_path):
    if not (ROOT / ".cache/mcpevol/upstream").is_dir():
        pytest.skip("Requires pinned upstream bootstrap")
    record = read_json(task139_metadata_path(ROOT, "early"))["tools"][0]
    knowledge_path = tmp_path / "knowledge.json"
    write_json(knowledge_path, {"tools": [record]})
    tools, routes = runner.prepare_tools([record], "no_update")
    config = read_json(pilot_config_path(ROOT))
    config.update(root=str(ROOT), knowledge_path=str(knowledge_path))

    def handler(request):
        return httpx.Response(401, json={"error": {"message": "fake invalid key"}})

    async with AsyncOpenAI(
        api_key="fake",
        base_url="https://fixture.invalid/v1",
        max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    ) as c:
        with pytest.raises(RuntimeError, match="Upstream agent failed"):
            await upstream_agent_loop(
                c, {}, tools, routes, "task", tmp_path, config, 0, lambda e: None
            )

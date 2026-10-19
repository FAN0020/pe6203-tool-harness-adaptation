"""Focused offline checks for the paper-style Vanilla tool-calling Agent.

These use fake LLM responses and MCP boundaries. They are NOT measured
MCPEvol-Bench scores, and do not replace live-model / real-server acceptance.
"""

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from pe6203 import runner


class FakeMessage:
    def __init__(self, payload):
        self.payload = payload

    def model_dump(self, **kwargs):
        return copy.deepcopy(self.payload)


class FakeCompletion:
    def __init__(self, payload):
        self.choices = [SimpleNamespace(message=FakeMessage(payload))]
        self.usage = SimpleNamespace(
            model_dump=lambda: {"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10}
        )
        self.payload = payload

    def model_dump(self):
        return {"fixture": True, "choices": [{"message": self.payload}]}


class FakeModelClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    async def create(self, *, messages, tools, **settings):
        self.requests.append({"messages": copy.deepcopy(messages), "tools": copy.deepcopy(tools)})
        return FakeCompletion(self.responses.pop(0))


class FakeMCPClient:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def call_tool(self, name, arguments):
        self.calls.append((name, copy.deepcopy(arguments)))
        return SimpleNamespace(model_dump=lambda **kwargs: copy.deepcopy(self.result))


def tool(server, name, version="middle"):
    return {
        "tool_id": f"{server}::{name}",
        "server_id": server,
        "version": version,
        "name": name,
        "description": f"{name} at {version}",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
        "usage_rules": [],
        "output_schema": None,
        "routing": {"server_id": server, "tool_name": name},
    }


def make_call(call_id, visible_name, **arguments):
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": visible_name, "arguments": json.dumps(arguments)},
    }


@pytest.mark.asyncio
async def test_vanilla_agent_uses_two_mcp_tools_and_records_observations(tmp_path):
    """The model must see each prior observation before its next tool choice."""
    tools, routes = runner.prepare_tools(
        [tool("paper-server", "fetch_url"), tool("page-server", "deploy_html")],
        "current_metadata_smoke",
        name_policy="namespaced",
    )
    fetch = next(name for name, route in routes.items() if route["tool_name"] == "fetch_url")
    deploy = next(name for name, route in routes.items() if route["tool_name"] == "deploy_html")
    model = FakeModelClient(
        [
            {"role": "assistant", "content": None, "tool_calls": [make_call("c1", fetch, query="AI")]},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [make_call("c2", deploy, query="five papers")],
            },
            {"role": "assistant", "content": "Published example page"},
        ]
    )
    paper_client = FakeMCPClient({"isError": False, "content": "five paper titles"})
    page_client = FakeMCPClient({"isError": False, "content": "example.invalid/page"})
    events = []
    outcome = await runner.agent_loop(
        model,
        {"paper-server": paper_client, "page-server": page_client},
        tools,
        routes,
        "Find five papers and publish a webpage",
        tmp_path,
        {"agent": {"model": "fake-model", "temperature": 0, "max_completion_tokens": 50},
         "max_rounds": 4, "tool_timeout_seconds": 1},
        0,
        events.append,
    )
    assert outcome["status"] == "completed"
    assert outcome["answer"] == "Published example page"
    assert outcome["rounds"] == 3
    assert outcome["usage"]["total_tokens"] == 30
    assert paper_client.calls == [("fetch_url", {"query": "AI"})]
    assert page_client.calls == [("deploy_html", {"query": "five papers"})]
    assert "five paper titles" in model.requests[1]["messages"][-1]["content"]
    assert "example.invalid/page" in model.requests[2]["messages"][-1]["content"]
    assert [e["type"] for e in events].count("tool_result") == 2
    assert len(outcome["messages"]) == 7  # system + user + 3 assistant + 2 tool results
    assert model.requests[0]["tools"] == tools
    assert all(model_request["tools"] == tools for model_request in model.requests)


@pytest.mark.asyncio
async def test_vanilla_agent_isolates_conversation_between_tasks(tmp_path):
    """Repeated independent tasks must not share dialogue memory."""
    tools, routes = runner.prepare_tools([tool("server", "get_item")], "current_metadata_smoke")
    model = FakeModelClient(
        [{"role": "assistant", "content": "answer one"},
         {"role": "assistant", "content": "answer two"}]
    )
    config = {"agent": {"model": "fake-model", "temperature": 0, "max_completion_tokens": 50},
              "max_rounds": 2}
    first = await runner.agent_loop(
        model, {}, tools, routes, "private task one", tmp_path, config, 0, lambda _: None
    )
    second = await runner.agent_loop(
        model, {}, tools, routes, "different task two", tmp_path, config, 0, lambda _: None
    )
    assert len(first["messages"]) == len(second["messages"]) == 3
    assert second["messages"][1]["content"] == "different task two"
    assert "private task one" not in json.dumps(model.requests[1]["messages"])


@pytest.mark.asyncio
async def test_vanilla_agent_can_recover_after_tool_error(tmp_path):
    """A failed tool call is an observation, not proof the task succeeded."""
    tools, routes = runner.prepare_tools(
        [tool("unstable-server", "broken_tool"), tool("fallback-server", "safe_tool")],
        "current_metadata_smoke",
    )

    class FailingMCP:
        async def call_tool(self, name, arguments):
            raise RuntimeError("simulated tool failure")

    model = FakeModelClient(
        [
            {"role": "assistant", "content": None,
             "tool_calls": [make_call("failure", "broken_tool", query="test")]},
            {"role": "assistant", "content": None,
             "tool_calls": [make_call("fallback", "safe_tool", query="retry")]},
            {"role": "assistant", "content": "Recovered with backup tool"},
        ]
    )
    fallback = FakeMCPClient({"isError": False, "content": "backup success"})
    events = []
    outcome = await runner.agent_loop(
        model,
        {"unstable-server": FailingMCP(), "fallback-server": fallback},
        tools,
        routes,
        "Use the tools to complete the task",
        tmp_path,
        {"agent": {"model": "fake-model", "temperature": 0, "max_completion_tokens": 50},
         "max_rounds": 4, "tool_timeout_seconds": 1},
        0,
        events.append,
    )
    assert outcome["status"] == "completed"
    error = json.loads(model.requests[1]["messages"][-1]["content"])
    assert error["isError"] is True
    assert "simulated tool failure" in error["error"]
    assert fallback.calls == [("safe_tool", {"query": "retry"})]
    assert any(event["type"] == "tool_result" and event["result"].get("isError")
               for event in events)


def test_vanilla_reference_accepts_matching_stage_before_api_preflight(tmp_path, monkeypatch):
    """A correct stage snapshot must reach credential checks, not fail the guard."""
    root = Path(__file__).resolve().parents[1]
    monkeypatch.setattr(
        runner,
        "source",
        lambda _root: ({"commit": "test-commit", "dataset_revision": "test-release", "stages": {"late": {}}}, tmp_path),
    )
    monkeypatch.setattr(
        runner,
        "load_task",
        lambda upstream, task_id: {"idx": 139, "question": "test task", "servers": {"server": []}},
    )
    monkeypatch.setattr(runner, "server_profiles", lambda *_: {"server": {}})
    knowledge_path = tmp_path / "correct.json"
    knowledge_path.write_text(json.dumps({
        "benchmark_commit": "test-commit", "version": "late",
        "tools": [tool("server", "get_item", "late")],
    }))
    config = json.loads((root / "configs/full-catalog-smoke.json").read_text())
    config.update(root=str(tmp_path), output_dir=str(tmp_path / "correct-run"),
                  knowledge_path=str(knowledge_path))
    monkeypatch.delenv("AGENT_API_KEY", raising=False)
    _, result = runner.run(139, "late", "current_metadata_smoke", 0, config)
    assert result["status"] == "blocked"
    assert "Configure AGENT_API_KEY" in result["errors"][0]["message"]
    assert "requires the knowledge envelope" not in result["errors"][0]["message"]


@pytest.mark.parametrize(
    "envelope_version,record_version",
    [("early", "early"), ("late", "early")],
)
def test_vanilla_reference_rejects_stale_tool_knowledge(
    tmp_path, monkeypatch, envelope_version, record_version
):
    """The development reference is not allowed to masquerade as No Update."""
    root = Path(__file__).resolve().parents[1]
    monkeypatch.setattr(
        runner,
        "source",
        lambda _root: ({"commit": "test-commit", "dataset_revision": "test-release", "stages": {"late": {}}}, tmp_path),
    )
    monkeypatch.setattr(
        runner,
        "load_task",
        lambda upstream, task_id: {"idx": 139, "question": "test task", "servers": {"server": []}},
    )
    monkeypatch.setattr(runner, "server_profiles", lambda *_: {"server": {}})
    knowledge_path = tmp_path / "knowledge.json"
    knowledge_path.write_text(
        json.dumps(
            {
                "benchmark_commit": "test-commit",
                "version": envelope_version,
                "tools": [tool("server", "get_item", record_version)],
            }
        )
    )
    config = json.loads((root / "configs/full-catalog-smoke.json").read_text())
    config.update(root=str(tmp_path), output_dir=str(tmp_path / "result"),
                  knowledge_path=str(knowledge_path))
    trace, result = runner.run(139, "late", "current_metadata_smoke", 0, config)
    assert result["status"] == "blocked"
    assert result["TF"] is None and result["PE"] is None
    assert "requires the knowledge envelope" in result["errors"][0]["message"]
    assert not (tmp_path / "result/environment-metadata.json").exists()
    assert trace["idx"] == 139

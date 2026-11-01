"""Outer-run failure accounting; SDK responses and MCP are explicit test doubles."""

import json
from contextlib import asynccontextmanager

import httpx
import pytest
from openai import AsyncOpenAI
from test_artifact_validation import BAD, GOOD, ScriptedBackend, answer, protocol
from test_contract import record
from test_runner import completion

from pe6203 import artifact_validation as av
from pe6203 import runner


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["repair_cancel", "after_repair"])
async def test_outer_timeout_retains_repair_known_or_unknown_costs(tmp_path, monkeypatch, phase):
    import asyncio
    import threading

    requests = []

    async def handler(request):
        requests.append(json.loads(request.content))
        if len(requests) == 2 and phase == "repair_cancel":
            await asyncio.sleep(3)  # trusted HTTP test double, cancelled by outer run budget
        return completion(
            {"role": "assistant", "content": answer(BAD if len(requests) == 1 else GOOD)}
        )

    def client(**kwargs):
        return AsyncOpenAI(
            **kwargs, http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
        )

    @asynccontextmanager
    async def sessions(*args):
        yield {}

    async def snapshot(*args):
        return {"tools": [record()]}

    class Backend(ScriptedBackend):
        def __init__(self):
            super().__init__(["test_failed"])
            self.calls = 0
            self.stopped = threading.Event()

        def run(self, source, tests):
            self.calls += 1
            if self.calls == 1:
                return super().run(source, tests)
            assert self.stopped.wait(2)
            return {"status": "cancelled", "tests": [], "isolated_execution": False}

        def cancel(self):
            self.stopped.set()

    monkeypatch.setattr(
        runner,
        "source",
        lambda root: (
            {
                "commit": "pin",
                "dataset_revision": "fixture",
                "stages": {"early": {}},
                "servers": {},
            },
            tmp_path,
        ),
    )
    monkeypatch.setattr(
        runner,
        "load_task",
        lambda *args: {"idx": 999, "question": "Task", "servers": {"server": []}},
    )
    monkeypatch.setattr(runner, "server_profiles", lambda *args: {"server": {}})
    monkeypatch.setattr(runner, "sessions", sessions)
    monkeypatch.setattr(runner, "snapshot", snapshot)
    monkeypatch.setattr(runner, "AsyncOpenAI", client)
    monkeypatch.setattr(av, "DockerBackend", lambda config: Backend())
    for prefix in ["AGENT", "JUDGE"]:
        monkeypatch.setenv(prefix + "_API_KEY", "scripted-test-only")
        monkeypatch.setenv(prefix + "_BASE_URL", "http://fixture.local/v1")
    knowledge = tmp_path / "knowledge.json"
    knowledge.write_text(
        json.dumps({"benchmark_commit": "pin", "version": "early", "tools": [record()]})
    )
    config = {
        "root": str(tmp_path),
        "output_dir": str(tmp_path / "run"),
        "knowledge_path": str(knowledge),
        "max_rounds": 1,
        "judge_runs": 1,
        "run_timeout_seconds": 0.8,
        "request_timeout_seconds": 2,
        "agent": {
            "api_key_env": "AGENT_API_KEY",
            "base_url_env": "AGENT_BASE_URL",
            "model": "fixture-model",
            "temperature": 0,
            "max_completion_tokens": 128,
        },
        "judge": {
            "api_key_env": "JUDGE_API_KEY",
            "base_url_env": "JUDGE_BASE_URL",
            "model": "fixture-model",
        },
        "artifact_validation": protocol(),
    }
    trace, result = await runner.run_async(999, "early", "no_update", 0, config)
    assert result["status"] == "timeout" and len(requests) == 2
    if phase == "repair_cancel":
        assert result["cost"]["agent"]["total_tokens"] is None
        assert any(e["type"] == "artifact_repair_error" for e in trace["events"])
    else:
        assert result["cost"]["agent"]["total_tokens"] == 30
        assert any(e["type"] == "artifact_repair_response" for e in trace["events"])
    assert "scripted-test-only" not in (tmp_path / "run/raw_trace.json").read_text()

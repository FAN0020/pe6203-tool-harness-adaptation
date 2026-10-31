import json

import httpx
import pytest
from openai import AsyncOpenAI, OpenAI
from test_runner import completion


@pytest.mark.asyncio
async def test_agent_recovers_from_transient_http_without_replaying_tools(tmp_path):
    from pe6203.runner import agent_loop

    seen = []

    def endpoint(request):
        seen.append(json.loads(request.content))
        if len(seen) == 1:
            return httpx.Response(503, json={"error": {"message": "temporary"}})
        return completion({"role": "assistant", "content": "Done"})

    events = []
    async with AsyncOpenAI(
        api_key="fixture",
        base_url="https://test.invalid/v1",
        max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(endpoint)),
    ) as client:
        result = await agent_loop(
            client,
            {},
            [],
            {},
            "Task",
            tmp_path,
            {
                "agent": {"model": "test", "temperature": 0, "max_completion_tokens": 32},
                "max_rounds": 2,
                "request_retry": {"max_retries": 1, "backoff_seconds": 0},
            },
            0,
            events.append,
        )
    assert result["status"] == "completed"
    assert len(seen) == 2 and seen[0] == seen[1]
    assert result["usage"]["total_tokens"] is None
    retry = next(e for e in events if e["type"] == "request_retry")
    assert retry["http_status"] == 503 and retry["role"] == "agent"


@pytest.mark.parametrize("status,attempts", [(429, 2), (500, 2), (401, 1), (400, 1)])
def test_sync_retry_is_bounded_and_never_retries_auth_or_invalid_requests(status, attempts):
    from pe6203.request_retry import request_sync

    seen, errors = [], []

    def endpoint(request):
        seen.append(request)
        return httpx.Response(status, json={"error": {"message": "fixture"}})

    with OpenAI(
        api_key="fixture",
        base_url="https://test.invalid/v1",
        max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(endpoint)),
    ) as client:
        with pytest.raises(Exception):
            request_sync(
                lambda: client.chat.completions.create(model="test", messages=[]),
                {"max_retries": 1, "backoff_seconds": 0},
                errors.append,
            )
    assert len(seen) == attempts
    assert len(errors) == attempts - 1


def test_nested_transport_error_is_visible_through_mcp_exception_groups():
    from openai import APIConnectionError

    from pe6203.request_retry import failure_details

    error = APIConnectionError(request=httpx.Request("POST", "https://provider.invalid"))
    result = failure_details(ExceptionGroup("MCP teardown", [ExceptionGroup("session", [error])]))
    assert result["failure_category"] == "model_transport"
    assert result["causes"] == ["APIConnectionError"]
    assert failure_details(ValueError("invalid JSON"))["failure_category"] == "execution"


def test_unavailable_api_preflight_records_failure_before_allocating_cells(tmp_path, monkeypatch):
    import openai

    from pe6203.experiment import availability_preflight

    calls = []

    def endpoint(request):
        calls.append(request)
        return httpx.Response(503, json={"error": {"message": "temporarily unavailable"}})

    original = openai.OpenAI
    monkeypatch.setattr(
        openai,
        "OpenAI",
        lambda **kwargs: original(
            **kwargs, http_client=httpx.Client(transport=httpx.MockTransport(endpoint))
        ),
    )
    monkeypatch.setenv("TEST_KEY", "fixture")
    monkeypatch.setenv("TEST_URL", "https://test.invalid/v1")
    cfg = {"api_key_env": "TEST_KEY", "base_url_env": "TEST_URL", "model": "test"}
    with pytest.raises(ValueError, match="预检失败"):
        availability_preflight(
            {
                "config": {
                    "agent": cfg,
                    "judge": cfg,
                    "request_retry": {"max_retries": 1, "backoff_seconds": 0},
                },
                "updater": cfg,
                "endpoints": {"agent": "https://test.invalid/v1"},
            },
            tmp_path,
        )
    assert len(calls) == 2
    record = json.loads(next((tmp_path / "preflight").glob("*.json")).read_text())
    assert record[0]["status"] == "failed"
    assert len(record[0]["retries"]) == 1
    assert not (tmp_path / "cells").exists()

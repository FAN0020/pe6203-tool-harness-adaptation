import json

import httpx
import pytest

from integration import baselines
from integration.model_api import OPENROUTER_FLASH, model_id, nonthinking_options
from integration.test_real_baselines import DeepSeekClient


def test_provider_mapping():
    assert model_id("deepseek-flash", "https://openrouter.ai/api/v1") == OPENROUTER_FLASH
    assert model_id("deepseek-flash", "https://api.deepseek.com") == "deepseek-flash"
    assert model_id("other/custom", "https://openrouter.ai/api/v1") == "other/custom"
    assert model_id("deepseek-flash", "https://openrouter.ai.example.org") == "deepseek-flash"
    assert nonthinking_options("https://openrouter.ai/api/v1") == {"reasoning": {"enabled": False}}


def response():
    return httpx.Response(
        200,
        json={
            "id": "mock",
            "object": "chat.completion",
            "created": 1,
            "model": OPENROUTER_FLASH,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "ok"},
                    "finish_reason": "stop",
                }
            ],
        },
    )


@pytest.mark.asyncio
async def test_async_openrouter_wire_request():
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        return response()

    async with DeepSeekClient(
        api_key="fake",
        base_url="https://openrouter.ai/api/v1",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    ) as client:
        await client.chat.completions.create(
            model="deepseek-flash",
            max_completion_tokens=32,
            messages=[{"role": "user", "content": "test"}],
        )
    assert seen[0]["model"] == OPENROUTER_FLASH
    assert seen[0]["reasoning"] == {"enabled": False}
    assert "thinking" not in seen[0]


def test_updater_openrouter_wire_request(monkeypatch):
    from openai import OpenAI

    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        return response()

    def client(**kwargs):
        return OpenAI(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    monkeypatch.setattr(baselines, "OpenAI", client)
    monkeypatch.setenv("FAKE_TEST_KEY", "fake-test-only")
    monkeypatch.setenv("FAKE_TEST_URL", "https://openrouter.ai/api/v1")
    baselines._request_completion(
        [{"role": "user", "content": "test"}],
        {
            "model": "deepseek-flash",
            "allow_metadata_api": True,
            "api_key_env": "FAKE_TEST_KEY",
            "base_url_env": "FAKE_TEST_URL",
            "timeout": 10,
            "temperature": 0,
            "max_tokens": 32,
        },
    )
    assert seen[0]["model"] == OPENROUTER_FLASH
    assert seen[0]["reasoning"] == {"enabled": False}
    assert "thinking" not in seen[0]

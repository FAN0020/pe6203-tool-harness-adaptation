"""Every HTTP attempt must reserve funds before it can reach the provider."""

import json

import httpx
import pytest
from openai import AsyncOpenAI, OpenAI

from pe6203 import spend_guard


def policy(tmp_path):
    return {
        "ledger": str(tmp_path / "budget.json"),
        "limit_usd": "1.00",
        "model": "deepseek/deepseek-v4.1-flash-1017",
        "context_tokens": 1048576,
        "prompt_per_million": "0.3",
        "completion_per_million": "1.2",
        "max_completion_tokens": 4096,
    }


def kwargs():
    return {
        "model": "deepseek/deepseek-v4.1-flash-1017",
        "messages": [{"role": "user", "content": "example"}],
        "max_completion_tokens": 4096,
        "temperature": 0,
    }


def response(cost):
    return {
        "id": "test",
        "model": "deepseek/deepseek-v4.1-flash-1017",
        "choices": [
            {"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "ok"}}
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 1, "total_tokens": 11, "cost": cost},
    }


def test_rejects_before_network_when_worst_case_request_exceeds_remaining_budget(tmp_path):
    calls = []

    def handle(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json=response(0.25))

    rules = policy(tmp_path)
    with OpenAI(
        api_key="test",
        base_url="https://openrouter.ai/api/v1",
        max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(handle)),
    ) as client:
        for _ in range(3):
            spend_guard.complete_sync(client, rules, **kwargs())
        with pytest.raises(spend_guard.BudgetStopped):
            spend_guard.complete_sync(client, rules, **kwargs())
    assert len(calls) == 3
    assert calls[0]["provider"]["max_price"] == {"prompt": 0.3, "completion": 1.2, "request": 0}
    ledger = json.loads((tmp_path / "budget.json").read_text())
    assert ledger["known_usd"] == "0.75"
    assert len(ledger["requests"]) == 3
    assert ledger["requests"][0]["reserved_usd"] == "0.319488"


@pytest.mark.asyncio
async def test_missing_charge_preserves_reservation_and_blocks_followup(tmp_path):
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(200, json=response(None))

    rules = policy(tmp_path)
    async with AsyncOpenAI(
        api_key="test",
        base_url="https://openrouter.ai/api/v1",
        max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handle)),
    ) as client:
        result = await spend_guard.complete_async(client, rules, **kwargs())
        assert result.choices[0].message.content == "ok"
        with pytest.raises(spend_guard.BudgetStopped):
            await spend_guard.complete_async(client, rules, **kwargs())
    assert len(calls) == 1
    ledger = json.loads((tmp_path / "budget.json").read_text())
    assert ledger["unknown_reserved_usd"] == "0.319488"
    assert ledger["requests"][0]["actual_usd"] is None


def test_transport_failure_cannot_release_an_unknown_charge(tmp_path):
    rules = policy(tmp_path)
    calls = []

    def handle(request):
        calls.append(request)
        raise httpx.ReadTimeout("lost response", request=request)

    with OpenAI(
        api_key="test",
        base_url="https://openrouter.ai/api/v1",
        max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(handle)),
    ) as client:
        with pytest.raises(Exception):
            spend_guard.complete_sync(client, rules, **kwargs())
        with pytest.raises(spend_guard.BudgetStopped):
            spend_guard.complete_sync(client, rules, **kwargs())
    assert len(calls) == 1
    assert json.loads((tmp_path / "budget.json").read_text())["blocked"]


def test_changed_policy_cannot_reset_shared_budget(tmp_path):
    rules = policy(tmp_path)
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=response(0.1)))
    with OpenAI(
        api_key="test",
        base_url="https://openrouter.ai/api/v1",
        max_retries=0,
        http_client=httpx.Client(transport=transport),
    ) as client:
        spend_guard.complete_sync(client, rules, **kwargs())
        rules["limit_usd"] = "2"
        with pytest.raises(spend_guard.BudgetStopped):
            spend_guard.complete_sync(client, rules, **kwargs())


def test_sdk_retries_cannot_bypass_per_attempt_reservations(tmp_path):
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(200, json=response(0.1))

    with OpenAI(
        api_key="test",
        base_url="https://openrouter.ai/api/v1",
        max_retries=2,
        http_client=httpx.Client(transport=httpx.MockTransport(handle)),
    ) as client:
        with pytest.raises(spend_guard.BudgetStopped):
            spend_guard.complete_sync(client, policy(tmp_path), **kwargs())
    assert not calls


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["agent", "judge"])
async def test_runner_and_judge_cannot_bypass_the_shared_cap(tmp_path, role):
    from pe6203.judge import evaluate_slots
    from pe6203.runner import agent_loop

    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(200, json=response(0.01))

    rules = {**policy(tmp_path), "limit_usd": "0.01"}
    settings = {k: v for k, v in kwargs().items() if k != "messages"}
    config = {
        "agent": settings,
        "judge": settings,
        "max_rounds": 1,
        "spend_guard": rules,
        "judge_recovery": {"max_attempts": 2, "stop_after_transport_failures": 2},
    }
    async with AsyncOpenAI(
        api_key="test",
        base_url="https://openrouter.ai/api/v1",
        max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handle)),
    ) as client:
        if role == "agent":
            try:
                await agent_loop(client, {}, [], {}, "task", tmp_path, config, 0, lambda e: None)
            except spend_guard.BudgetStopped:
                pass
        else:
            await evaluate_slots(client, tmp_path / "judge", ["prompt"], config, lambda e: None)
    assert calls == [], "Role reached model endpoint despite insufficient budget"


def test_availability_preflight_cannot_bypass_the_shared_cap(tmp_path, monkeypatch):
    import openai

    from pe6203.experiment import availability_preflight

    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(200, json=response(0.01))

    client = OpenAI(
        api_key="test",
        base_url="https://openrouter.ai/api/v1",
        max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(handle)),
    )
    monkeypatch.setattr(openai, "OpenAI", lambda **kw: client)
    monkeypatch.setenv("TEST_BUDGET_KEY", "test")
    monkeypatch.setenv("TEST_BUDGET_URL", "https://openrouter.ai/api/v1")
    settings = {
        "model": kwargs()["model"],
        "api_key_env": "TEST_BUDGET_KEY",
        "base_url_env": "TEST_BUDGET_URL",
    }
    plan = {
        "config": {
            "agent": settings,
            "judge": settings,
            "spend_guard": {**policy(tmp_path), "limit_usd": "0.01"},
        },
        "updater": settings,
        "endpoints": {"agent": "https://openrouter.ai/api/v1"},
    }
    try:
        availability_preflight(plan, tmp_path)
    except ValueError:
        pass
    assert calls == [], "Preflight reached model endpoint despite insufficient budget"


@pytest.mark.parametrize(
    "actual_provider,actual_model,blocked",
    [
        ("DigitalOcean", "deepseek/deepseek-v4.1-flash-1017", False),
        ("Other", "deepseek/deepseek-v4.1-flash-1017", True),
        (None, "deepseek/deepseek-v4.1-flash-1017", True),
        ("DigitalOcean", "other-model", True),
    ],
)
def test_pinned_route_applies_to_every_request_and_mismatch_blocks_followups(
    tmp_path, actual_provider, actual_model, blocked
):
    route = {
        "only": ["digitalocean"],
        "order": ["digitalocean"],
        "allow_fallbacks": False,
        "require_parameters": True,
    }
    rules = {**policy(tmp_path), "provider_route": route, "expected_provider": "DigitalOcean"}
    payloads = []

    def handle(request):
        payloads.append(json.loads(request.content))
        body = response(0.01)
        body.update(provider=actual_provider, model=actual_model)
        return httpx.Response(200, json=body)

    with OpenAI(
        api_key="test",
        base_url="https://openrouter.ai/api/v1",
        max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(handle)),
    ) as client:
        # No explicit provider on request: also exercises availability-preflight routing.
        result = spend_guard.complete_sync(client, rules, **kwargs())
        assert result.model == actual_model  # Raw evidence is returned even on a mismatch.
        assert spend_guard.stopped(rules) is blocked
        if blocked:
            with pytest.raises(spend_guard.BudgetStopped):
                spend_guard.complete_sync(client, rules, **kwargs())
    assert len(payloads) == 1
    assert payloads[0]["provider"] == {
        **route,
        "max_price": {"prompt": 0.3, "completion": 1.2, "request": 0},
    }
    data = json.loads((tmp_path / "budget.json").read_text())
    assert data["known_usd"] == "0.01"
    assert data["requests"][0]["actual_provider"] == actual_provider


def test_conflicting_provider_override_is_rejected_before_network(tmp_path):
    rules = {
        **policy(tmp_path),
        "provider_route": {"only": ["digitalocean"]},
        "expected_provider": "DigitalOcean",
    }
    with OpenAI(api_key="test", base_url="https://openrouter.ai/api/v1", max_retries=0) as client:
        with pytest.raises(spend_guard.BudgetStopped, match="provider"):
            spend_guard.reserve(
                client, rules, {**kwargs(), "extra_body": {"provider": {"only": ["other"]}}}
            )
    assert not (tmp_path / "budget.json").exists()


def test_preflight_cap_blocks_an_extra_session_without_a_request(tmp_path):
    from pe6203.experiment import availability_preflight

    (tmp_path / "preflight").mkdir()
    (tmp_path / "preflight/old.json").write_text(
        json.dumps(
            [{"role": "agent", "status": "reachable"}, {"role": "judge", "status": "reachable"}]
        )
    )
    with pytest.raises(ValueError, match="preflight.*limit"):
        availability_preflight({"max_preflight_calls": 2}, tmp_path)

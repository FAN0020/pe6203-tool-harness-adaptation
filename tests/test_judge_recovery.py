"""Real judging persistence with only the external HTTP endpoint substituted."""

import json

import httpx
import pytest
from openai import AsyncOpenAI

from pe6203 import judge


def reply(content, finish="stop"):
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
                    "finish_reason": finish,
                    "message": {"role": "assistant", "content": content},
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        },
    )


VALID = json.dumps({"task_fulfillment": 3, "grounding": 4, "planning_and_efficiency": 2})
CONFIG = {
    "judge": {"model": "fixture", "temperature": 0, "max_completion_tokens": 100},
    "request_retry": {"max_retries": 1, "backoff_seconds": 0},
    "judge_recovery": {"max_attempts": 2, "stop_after_transport_failures": 2},
}


def client(handler):
    return AsyncOpenAI(
        api_key="fixture",
        base_url="https://fixture.test/v1",
        max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )


def test_judge_input_keeps_rubric_and_counts_batched_and_unanswered_calls():
    assert hasattr(judge, "measurement_prompt"), "Missing recorded call-count evidence"
    messages = [
        {
            "role": "assistant",
            "tool_calls": [
                {"id": "one", "function": {"name": "lookup"}},
                {"id": "two", "function": {"name": "lookup"}},
                {"id": "three", "function": {"name": "publish"}},
            ],
        },
        {"role": "tool", "tool_call_id": "one", "content": '{"isError": false}'},
        {"role": "tool", "tool_call_id": "two", "content": '{"isError": true}'},
    ]
    prompt = judge.measurement_prompt("UNCHANGED ORIGINAL RUBRIC", messages)
    assert prompt.startswith("UNCHANGED ORIGINAL RUBRIC\n")
    assert '"tool_call_proposals": 3' in prompt
    assert '"tool_result_observations": 2' in prompt
    assert '"unanswered_proposals": 1' in prompt
    assert '"tool_error_results": 1' in prompt
    assert '"lookup": 2' in prompt


@pytest.mark.asyncio
async def test_invalid_rating_recovers_but_valid_low_score_is_never_replaced(tmp_path):
    assert hasattr(judge, "evaluate_slots"), "Missing durable judge slots"
    sent = []

    def handler(request):
        sent.append(json.loads(request.content))
        return reply('{"task_fulfillment":', "length") if len(sent) == 1 else reply(VALID)

    async with client(handler) as model:
        result = await judge.evaluate_slots(
            model, tmp_path, ["original rubric"], CONFIG, lambda e: None
        )
        again = await judge.evaluate_slots(
            model, tmp_path, ["original rubric"], CONFIG, lambda e: None
        )
    assert result["aggregate"]["complete"] is True
    assert result["runs"][0]["result"]["task_fulfillment"] == 3
    assert len(sent) == 2  # first valid, not best score; resume sends nothing
    assert len(result["attempts"]) == 2
    assert result["attempts"][0]["error"]
    assert len(again["usages"]) == 2
    assert sent[0] == sent[1]


@pytest.mark.asyncio
async def test_transport_outage_pauses_then_resumes_only_missing_slots(tmp_path):
    assert hasattr(judge, "evaluate_slots"), "Missing durable judge slots"
    online = False
    sent = []

    def handler(request):
        sent.append(json.loads(request.content)["messages"][0]["content"])
        if not online:
            raise httpx.ConnectError("fixture outage", request=request)
        return reply(VALID)

    async with client(handler) as model:
        first = await judge.evaluate_slots(model, tmp_path, ["a", "b", "c"], CONFIG, lambda e: None)
        assert first["paused"] is True
        assert first["resumable"] is True
        assert sent == ["a", "a", "b", "b"]
        online = True
        resumed = await judge.evaluate_slots(
            model, tmp_path, ["a", "b", "c"], CONFIG, lambda e: None
        )
    assert resumed["aggregate"]["complete"] is True
    assert sent == ["a", "a", "b", "b", "a", "b", "c"]
    assert len(resumed["usages"]) == 7  # four failed HTTP attempts remain unknown
    assert sum(u == {} for u in resumed["usages"]) == 4


@pytest.mark.asyncio
async def test_attempt_budget_survives_resume_and_changed_prompt_is_rejected(tmp_path):
    assert hasattr(judge, "evaluate_slots"), "Missing durable judge slots"
    sent = []

    def handler(request):
        sent.append(request)
        return reply("invalid JSON")

    async with client(handler) as model:
        for _ in range(3):
            result = await judge.evaluate_slots(model, tmp_path, ["same"], CONFIG, lambda e: None)
        assert result["aggregate"]["complete"] is False
        assert result["resumable"] is False
        assert len(sent) == 2
        with pytest.raises(ValueError, match="changed"):
            await judge.evaluate_slots(model, tmp_path, ["changed"], CONFIG, lambda e: None)


@pytest.mark.asyncio
async def test_saved_response_after_interruption_is_parsed_without_request(tmp_path):
    assert hasattr(judge, "evaluate_slots"), "Missing durable judge slots"

    def crash_after_response(event):
        if event["type"] == "judge_response_saved":
            raise KeyboardInterrupt("simulated process interruption")

    async with client(lambda r: reply(VALID)) as model:
        with pytest.raises(KeyboardInterrupt):
            await judge.evaluate_slots(model, tmp_path, ["same"], CONFIG, crash_after_response)

    def forbidden(request):
        pytest.fail("Persisted response must be reused without another model request")

    async with client(forbidden) as model:
        result = await judge.evaluate_slots(model, tmp_path, ["same"], CONFIG, lambda e: None)
    assert result["aggregate"]["complete"] is True
    assert len(result["attempts"]) == 1


@pytest.mark.asyncio
async def test_auth_failure_is_terminal_and_not_retried_as_format_error(tmp_path):
    assert hasattr(judge, "evaluate_slots"), "Missing durable judge slots"
    sent = []

    def handler(request):
        sent.append(request)
        return httpx.Response(401, json={"error": {"message": "invalid key"}})

    async with client(handler) as model:
        first = await judge.evaluate_slots(model, tmp_path, ["same"], CONFIG, lambda e: None)
        second = await judge.evaluate_slots(model, tmp_path, ["same"], CONFIG, lambda e: None)
    assert not first["resumable"] and not second["resumable"]
    assert len(sent) == 1


@pytest.mark.asyncio
async def test_runner_resumes_judges_without_touching_agent_evidence(tmp_path, monkeypatch):
    from pe6203 import runner
    from pe6203.benchmark import write_json

    assert hasattr(runner, "resume_judging_async"), "Missing judge-only runner resume"
    config = {
        **CONFIG,
        "judge_runs": 5,
        "request_timeout_seconds": 2,
        "run_timeout_seconds": 20,
        "judge": {**CONFIG["judge"], "api_key_env": "TEST_KEY", "base_url_env": "TEST_URL"},
    }
    monkeypatch.setenv("TEST_KEY", "fixture")
    monkeypatch.setenv("TEST_URL", "https://fixture.test/v1")
    result = {
        "task_id": 139,
        "version": "late",
        "strategy": "selective_patch",
        "config": config,
        "status": "judge_pending",
        "execution_status": "completed",
        "model_endpoints": {"judge": "https://fixture.test/v1"},
        "errors": [],
        "cost": {"agent": {"total_tokens": 15, "usd": 0.01}, "update": {"usd": 0}},
        "seconds": 1,
    }
    trace = {"idx": 139, "question": "Task", "answer": "saved answer", "trajectory_messages": []}
    write_json(
        tmp_path / "execution-checkpoint.json",
        {"result": result, "trace": trace, "prompts": ["a", "b", "c", "d", "e"]},
    )
    write_json(tmp_path / "ANSWER/139.json", trace)
    (tmp_path / "events.jsonl").write_text(
        '{"type":"tool_result","call":{"function":{"name":"fixture","arguments":"{}"}},"result":{}}\n'
    )
    original_answer = (tmp_path / "ANSWER/139.json").read_bytes()
    online, requests = False, []

    def handler(request):
        requests.append(request)
        if not online:
            raise httpx.ConnectError("outage", request=request)
        return reply(VALID)

    monkeypatch.setattr(runner, "AsyncOpenAI", lambda **kwargs: client(handler))
    _, first = await runner.resume_judging_async(tmp_path)
    assert first["status"] == "judge_pending"
    first_result = (tmp_path / "result.json").read_bytes()
    online = True
    _, second = await runner.resume_judging_async(tmp_path)
    assert second["status"] == "evaluated"
    assert second["TF"] == 3 and second["PE"] == 2
    assert second["execution_status"] == "completed"
    assert second["cost"]["agent"]["total_tokens"] == 15
    assert (tmp_path / "ANSWER/139.json").read_bytes() == original_answer
    assert (tmp_path / "events.jsonl").read_text().count('"type": "tool_result"') == 0
    assert (tmp_path / "events.jsonl").read_text().count('"type":"tool_result"') == 1
    assert any(
        p.read_bytes() == first_result for p in (tmp_path / "revisions").rglob("result.json")
    )
    before = len(requests)
    await runner.resume_judging_async(tmp_path)
    assert len(requests) == before

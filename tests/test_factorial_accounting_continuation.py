"""One disclosed diagnostic interruption may be continued without erasing its cost.

No network, credentials, actors or benchmark artifacts are used in these tests.
"""

import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import httpx
import pytest
from openai import AsyncOpenAI, OpenAI

from pe6203 import benchmark, experiment, judge, spend_guard

PATH = (
    Path(__file__).parents[1]
    / "results/evidence/dependency-factorial-20261101/accounting_continuation.py"
)
spec = importlib.util.spec_from_file_location("factorial_accounting_continuation", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture(tmp_path):
    row = {
        "status": "unknown_charge",
        "actual_usd": None,
        "reserved_usd": "0.3",
        "error_type": "APITimeoutError",
    }
    data = {
        "policy": {"limit_usd": None},
        "requests": [row],
        "blocked": True,
        "stop_reason": "unknown_charge",
        "known_usd": "0",
        "unknown_reserved_usd": "0.3",
    }
    ledger = tmp_path / "spend-ledger.json"
    ledger.write_text(json.dumps(data))
    run = tmp_path / "cells/cell-007/run"
    run.mkdir(parents=True)
    outcome = run / "judge-attempts/slot-3-attempt-1/outcome.json"
    outcome.parent.mkdir(parents=True)
    outcome.write_text(
        json.dumps(
            {
                "slot": 3,
                "attempt": 1,
                "error": "BudgetStopped: model request failed",
                "failure_category": "model_request",
                "retryable": False,
            }
        )
    )
    result = run / "result.json"
    result.write_text(
        json.dumps({"status": "judge_incomplete", "judge_recovery": {"resumable": False}})
    )
    spec = {
        "id": "test-amendment",
        "ledger": str(ledger),
        "ledger_policy": data["policy"],
        "approved_prefix_count": 1,
        "approved_prefix_sha256": module.digest(data["requests"]),
        "unknown_index": 0,
        "run": str(run),
        "outcome": str(outcome),
        "outcome_sha256": module.sha(outcome),
        "initial_result_sha256": module.sha(result),
    }
    return spec, data


def test_only_frozen_unknown_row_is_eligible(tmp_path):
    spec, data = fixture(tmp_path)
    assert module.allowed(data, spec)
    for mutation in (
        lambda x: x["policy"].update(limit_usd="1"),
        lambda x: x["requests"].append({"status": "unknown_charge"}),
        lambda x: x["requests"].append({"status": "pending"}),
        lambda x: x.update(stop_reason="unexpected_provider_or_model"),
        lambda x: x["requests"][0].update(actual_usd="0"),
    ):
        altered = deepcopy(data)
        mutation(altered)
        assert not module.allowed(altered, spec)
    data["requests"].append({"status": "settled"})
    assert module.allowed(data, spec)


def test_ledger_stays_blocked_unknown_and_keeps_policy_after_scoped_access(tmp_path):
    spec, data = fixture(tmp_path)
    rules = {"ledger": spec["ledger"], **data["policy"]}
    originals = spend_guard.ledger, experiment.spend_stopped, benchmark.read_json
    with module.overlay(spec):
        assert not experiment.spend_stopped(rules)
        with spend_guard.ledger(rules) as live:
            assert live["blocked"] is False
            live["requests"].append({"status": "settled", "actual_usd": "0.01"})
            live["known_usd"] = "0.01"
        saved = json.loads(Path(spec["ledger"]).read_text())
        assert saved["blocked"] and saved["requests"][0] == data["requests"][0]
        assert saved["unknown_reserved_usd"] == "0.3" and saved["policy"] == data["policy"]
        assert not experiment.spend_stopped(rules)
    assert (spend_guard.ledger, experiment.spend_stopped, benchmark.read_json) == originals
    assert spend_guard.stopped(rules)


def test_new_unknown_or_other_guard_failure_still_stops(tmp_path):
    spec, data = fixture(tmp_path)
    rules = {"ledger": spec["ledger"], **data["policy"]}
    with module.overlay(spec):
        with spend_guard.ledger(rules) as live:
            live["requests"].append({"status": "unknown_charge"})
            live.update(blocked=True, stop_reason="unknown_charge")
        assert experiment.spend_stopped(rules)


def test_real_reservation_and_settlement_preserve_unknown_amount(tmp_path):
    spec, data = fixture(tmp_path)
    data["policy"].update(
        model="fixture",
        context_tokens=10000,
        prompt_per_million="0.3",
        completion_per_million="1.2",
        max_completion_tokens=4096,
    )
    spec["ledger_policy"] = data["policy"]
    Path(spec["ledger"]).write_text(json.dumps(data))
    rules = {"ledger": spec["ledger"], **data["policy"]}
    sent = []

    def respond(request):
        sent.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "fixture",
                "model": "fixture",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "ok"},
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 1,
                    "total_tokens": 11,
                    "cost": 0.01,
                },
            },
        )

    with module.overlay(spec):
        with OpenAI(
            api_key="fixture",
            base_url="https://openrouter.ai/api/v1",
            max_retries=0,
            http_client=httpx.Client(transport=httpx.MockTransport(respond)),
        ) as client:
            spend_guard.complete_sync(
                client,
                rules,
                model="fixture",
                messages=[{"role": "user", "content": "fixture"}],
                max_completion_tokens=100,
                temperature=0,
            )
        assert not experiment.spend_stopped(rules)
    result = json.loads(Path(spec["ledger"]).read_text())
    assert len(sent) == 1 and result["known_usd"] == "0.01"
    assert result["blocked"] and result["unknown_reserved_usd"] == "0.3"
    assert result["requests"][0] == data["requests"][0]
    assert result["requests"][1]["status"] == "settled"


def test_transport_classification_is_derived_not_rewritten_and_tamper_rejected(tmp_path):
    spec, _ = fixture(tmp_path)
    original = Path(spec["outcome"]).read_bytes()
    with module.overlay(spec):
        viewed = benchmark.read_json(Path(spec["outcome"]))
        assert viewed["retryable"] and viewed["failure_category"] == "model_transport"
        assert viewed["error"] == "BudgetStopped: model request failed"
        assert viewed["continuation"]["id"] == spec["id"]
        assert Path(spec["outcome"]).read_bytes() == original
        Path(spec["outcome"]).write_bytes(original + b" ")
        with pytest.raises(ValueError, match="changed"):
            benchmark.read_json(Path(spec["outcome"]))


def test_only_initial_incomplete_result_can_force_judge_resume(tmp_path):
    spec, _ = fixture(tmp_path)
    config = {"judge_recovery": {"max_attempts": 2}}
    with module.overlay(spec):
        assert experiment.pending_judging(Path(spec["run"]), config)
        Path(spec["run"], "result.json").write_text(json.dumps({"status": "evaluated"}))
        assert not experiment.pending_judging(Path(spec["run"]), config)
        assert not experiment.pending_judging(tmp_path / "other", config)


@pytest.mark.asyncio
async def test_real_judge_recovers_missing_slots_without_replacing_success_or_failed_attempt(
    tmp_path,
):
    spec, _ = fixture(tmp_path)
    run = Path(spec["run"])
    saved = {}
    for slot in (1, 2):
        directory = run / f"judge-attempts/slot-{slot}-attempt-1"
        directory.mkdir(parents=True)
        (directory / "request.json").write_text("{}")
        value = {
            "slot": slot,
            "attempt": 1,
            "result": {"task_fulfillment": 1, "grounding": 2, "planning_and_efficiency": 3},
            "response": {
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
            },
        }
        (directory / "outcome.json").write_text(json.dumps(value))
        saved[str(directory / "outcome.json")] = (directory / "outcome.json").read_bytes()
    (run / "judge-attempts/slot-3-attempt-1/request.json").write_text("{}")
    saved[spec["outcome"]] = Path(spec["outcome"]).read_bytes()
    sent = []

    def respond(request):
        sent.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "test",
                "object": "chat.completion",
                "created": 1,
                "model": "test",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": json.dumps(
                                {
                                    "task_fulfillment": 10,
                                    "grounding": 10,
                                    "planning_and_efficiency": 10,
                                }
                            ),
                        },
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            },
        )

    config = {
        "judge": {"model": "test", "temperature": 0, "max_completion_tokens": 100},
        "judge_recovery": {"max_attempts": 2, "stop_after_transport_failures": 2},
        "request_retry": {"max_retries": 1, "backoff_seconds": 0},
    }
    with module.overlay(spec):
        async with AsyncOpenAI(
            api_key="test",
            base_url="https://fixture.test/v1",
            max_retries=0,
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond)),
        ) as client:
            result = await judge.evaluate_slots(
                client, run, ["same rubric"] * 5, config, lambda e: None
            )
            again = await judge.evaluate_slots(
                client, run, ["same rubric"] * 5, config, lambda e: None
            )
    assert result["aggregate"]["complete"] and again["aggregate"]["complete"]
    assert len(sent) == 3
    assert [(x["slot"], x["attempt"]) for x in result["runs"]] == [
        (1, 1),
        (2, 1),
        (3, 2),
        (4, 1),
        (5, 1),
    ]
    assert result["runs"][0]["result"]["task_fulfillment"] == 1
    assert len(result["attempts"]) == 6
    assert all(Path(p).read_bytes() == b for p, b in saved.items())

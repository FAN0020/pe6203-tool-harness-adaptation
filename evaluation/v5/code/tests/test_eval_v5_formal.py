"""Paid-evaluation controls: test failures that could invalidate cost evidence."""

import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "eval_v5_formal", Path(__file__).parents[1] / "scripts/eval_v5_formal.py"
)
formal = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(formal)


def request():
    return {"model": formal.MODEL, "extra_body": formal.ROUTING, "messages": []}


def response(cost):
    return {
        "id": "test-only",
        "model": formal.MODEL,
        "provider": "DigitalOcean",
        "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3, "cost": cost},
    }


def test_unknown_receipt_stops_following_requests_and_is_not_zero(tmp_path):
    guard = formal.ReceiptGuard(tmp_path, 8)
    n, directory = guard.begin("agent", request())
    missing = response(None)
    guard.finish(n, directory, "agent", missing)
    assert guard.stopped and guard.rows[0]["usd"] is None
    with pytest.raises(RuntimeError, match="guard stopped"):
        guard.begin("judge", request())
    resumed = formal.ReceiptGuard(tmp_path, 8)
    assert resumed.stopped and resumed.known == 0


def test_receipt_restore_and_budget_inhibit_new_paid_requests(tmp_path):
    guard = formal.ReceiptGuard(tmp_path, ".03")
    n, directory = guard.begin("agent", request())
    guard.finish(n, directory, "agent", response(0.03))
    restored = formal.ReceiptGuard(tmp_path, ".03")
    assert str(restored.known) == "0.03"
    assert len(restored.rows) == 1
    with pytest.raises(RuntimeError):
        restored.begin("agent", request())


def test_interrupted_request_cannot_be_retried_as_an_unbilled_request(tmp_path):
    guard = formal.ReceiptGuard(tmp_path, 8)
    guard.begin("agent", request())
    with pytest.raises(ValueError, match="unknown billing"):
        formal.ReceiptGuard(tmp_path, 8)


def test_missing_or_fallback_provider_rejected_before_request(tmp_path):
    guard = formal.ReceiptGuard(tmp_path, 8)
    with pytest.raises(ValueError, match="routing mismatch"):
        guard.begin("agent", {"model": formal.MODEL, "messages": []})
    assert not list(tmp_path.glob("request-*"))


def test_unexpected_response_provider_retains_cost_and_stops(tmp_path):
    guard = formal.ReceiptGuard(tmp_path, 8)
    n, directory = guard.begin("judge", request())
    wrong = response(0.002)
    wrong["provider"] = "another-provider"
    guard.finish(n, directory, "judge", wrong)
    assert guard.stopped and guard.rows[0]["usd"] == 0.002
    assert (directory / "response.json").is_file()

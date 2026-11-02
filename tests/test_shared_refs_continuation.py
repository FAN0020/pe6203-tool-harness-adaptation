"""The proposed accounting exception must never settle or waive another failure."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from pe6203 import experiment, spend_guard

P = (
    Path(__file__).parents[1]
    / "results/evidence/shared-contract-refs-20261101/continue_remaining.py"
)


def module():
    assert P.exists(), "Proposed continuation is not implemented"
    s = importlib.util.spec_from_file_location("shared_refs_continuation", P)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def ledger_fixture(tmp_path):
    policy = {
        "ledger": str(tmp_path / "ledger.json"),
        "model": "fixture",
        "limit_usd": None,
        "context_tokens": 100,
        "max_completion_tokens": 10,
        "prompt_per_million": "1",
        "completion_per_million": "1",
    }
    client = SimpleNamespace(max_retries=0, base_url="https://openrouter.ai/api/v1/")
    kwargs = {"model": "fixture", "messages": [], "max_completion_tokens": 10}
    i, _ = spend_guard.reserve(client, policy, kwargs)
    spend_guard.settle(policy, i, error="RateLimitError")
    data = json.loads(Path(policy["ledger"]).read_text())
    return policy, client, kwargs, data


def test_only_exact_unknown_prefix_is_exempt_and_remains_unknown(tmp_path):
    m = module()
    policy, client, kwargs, original = ledger_fixture(tmp_path)
    spec = m.accounting_spec(policy["ledger"], original)
    with m.accounting_overlay(spec):
        assert not experiment.spend_stopped(policy)
        i, _ = spend_guard.reserve(client, policy, kwargs)
        # An outstanding NEW request is never waived, even within the overlay.
        assert experiment.spend_stopped(policy)
        spend_guard.settle(policy, i, error="APITimeoutError")
        assert experiment.spend_stopped(policy)
        with pytest.raises(spend_guard.BudgetStopped):
            spend_guard.reserve(client, policy, kwargs)
    final = json.loads(Path(policy["ledger"]).read_text())
    assert final["requests"][0] == original["requests"][0]
    assert final["requests"][0]["actual_usd"] is None
    assert final["known_usd"] == "0"
    assert final["blocked"] is True
    assert spend_guard.stopped(policy)


def test_changed_original_prefix_and_other_ledger_are_never_exempt(tmp_path):
    m = module()
    policy, _, _, data = ledger_fixture(tmp_path)
    spec = m.accounting_spec(policy["ledger"], data)
    data["requests"][0]["error_type"] = "different"
    Path(policy["ledger"]).write_text(json.dumps(data))
    with m.accounting_overlay(spec):
        assert experiment.spend_stopped(policy)
    other = tmp_path / "other"
    other.mkdir()
    other_policy, _, _, _ = ledger_fixture(other)
    with m.accounting_overlay(spec):
        assert experiment.spend_stopped(other_policy)


def test_missing_approval_is_rejected(tmp_path):
    m = module()
    with pytest.raises(ValueError, match="authorization"):
        m.require_authorization(tmp_path, "manifest-hash")
    (tmp_path / "continuation-authorization.json").write_text(
        json.dumps({"approved": True, "manifest_sha256": "old-A1"})
    )
    with pytest.raises(ValueError, match="authorization"):
        m.require_authorization(tmp_path, "manifest-hash")


def test_real_schedule_keeps_terminal_cells_and_only_selects_unstarted(tmp_path):
    m = module()
    plan = {"cells": [{"id": f"cell-{i:03d}"} for i in range(1, 11)]}
    state = {
        "cells": {
            f"cell-{i:03d}": {"status": "evaluated" if i < 6 else "blocked"} for i in range(1, 7)
        }
    }
    assert m.remaining(plan, state) == ["cell-007", "cell-008", "cell-009", "cell-010"]
    state["cells"]["cell-006"]["status"] = "running"
    with pytest.raises(ValueError, match="Unfinished actor"):
        m.remaining(plan, state)


def test_preflight_reuse_rejects_unsettled_wrong_provider_and_extra_receipts(tmp_path):
    m = module()
    plan = {
        "max_preflight_calls": 2,
        "config": {"agent": {"model": "fixture"}, "judge": {"model": "fixture"}},
    }
    (tmp_path / "plan.json").write_text(json.dumps(plan))
    p = tmp_path / "preflight/original.json"
    p.parent.mkdir()
    records = [
        {
            "role": r,
            "status": "reachable",
            "model": "fixture",
            "actual_model": "fixture",
            "actual_provider": "DigitalOcean",
            "response_id": r,
        }
        for r in ("agent", "judge")
    ]
    p.write_text(json.dumps(records))
    ledger = tmp_path / "ledger.json"
    rows = [{"response_id": r, "status": "settled"} for r in ("agent", "judge")]
    ledger.write_text(json.dumps({"requests": rows}))
    spec = {
        "ledger": str(ledger),
        "plan_sha256": m.sha(tmp_path / "plan.json"),
        "preflight_files": {"preflight/original.json": m.sha(p)},
    }
    assert m.verify_preflight(plan, tmp_path, spec) == ["agent", "judge"]
    rows[0]["status"] = "unknown_charge"
    ledger.write_text(json.dumps({"requests": rows}))
    with pytest.raises(ValueError, match="settled success"):
        m.verify_preflight(plan, tmp_path, spec)
    rows[0]["status"] = "settled"
    ledger.write_text(json.dumps({"requests": rows}))
    records[0]["actual_provider"] = "different"
    p.write_text(json.dumps(records))
    spec["preflight_files"]["preflight/original.json"] = m.sha(p)
    with pytest.raises(ValueError, match="settled success"):
        m.verify_preflight(plan, tmp_path, spec)
    (p.parent / "extra.json").write_text("[]")
    with pytest.raises(ValueError, match="inventory"):
        m.verify_preflight(plan, tmp_path, spec)

"""Resume must not increase the frozen two-call availability-preflight budget."""

import importlib.util
import json
from pathlib import Path

import pytest

from pe6203 import experiment

P = Path(__file__).parents[1] / "results/evidence/dependency-factorial-20261101/run_approved_a1.py"
s = importlib.util.spec_from_file_location("a1_preflight_reuse", P)
m = importlib.util.module_from_spec(s)
s.loader.exec_module(m)


def fixture(tmp_path):
    plan = {
        "max_preflight_calls": 2,
        "config": {"agent": {"model": "fixture"}, "judge": {"model": "fixture"}},
    }
    (tmp_path / "plan.json").write_text(json.dumps(plan))
    p = tmp_path / "preflight/original.json"
    p.parent.mkdir()
    records = [
        {
            "role": role,
            "status": "reachable",
            "model": "fixture",
            "actual_model": "fixture",
            "actual_provider": "DigitalOcean",
            "response_id": role,
        }
        for role in ("agent", "judge")
    ]
    p.write_text(json.dumps(records))
    (tmp_path / "spend-ledger.json").write_text(
        json.dumps(
            {"requests": [{"response_id": x, "status": "settled"} for x in ("agent", "judge")]}
        )
    )
    spec = {
        "plan_sha256": m.sha(tmp_path / "plan.json"),
        "preflight_files": {"preflight/original.json": m.sha(p)},
    }
    return plan, spec


def test_existing_entry_rejects_before_network_but_exact_saved_evidence_is_reusable(tmp_path):
    plan, spec = fixture(tmp_path)
    with pytest.raises(ValueError, match="preflight call limit"):
        experiment.availability_preflight(plan, tmp_path)
    assert m.verify_reusable_preflight(plan, tmp_path, spec) == ["agent", "judge"]


def test_missing_or_changed_preflight_is_not_reused(tmp_path):
    plan, spec = fixture(tmp_path)
    (tmp_path / "preflight/original.json").write_text("[]")
    with pytest.raises(ValueError, match="Preflight evidence"):
        m.verify_reusable_preflight(plan, tmp_path, spec)


def test_hash_alone_does_not_admit_failed_or_wrong_provider_records(tmp_path):
    plan, spec = fixture(tmp_path)
    p = tmp_path / "preflight/original.json"
    records = json.loads(p.read_text())
    records[0]["actual_provider"] = "different"
    p.write_text(json.dumps(records))
    spec["preflight_files"]["preflight/original.json"] = m.sha(p)
    with pytest.raises(ValueError, match="preflight result"):
        m.verify_reusable_preflight(plan, tmp_path, spec)


def test_no_extra_preflight_file_or_modified_plan_is_allowed(tmp_path):
    plan, spec = fixture(tmp_path)
    plan["max_preflight_calls"] = 3
    with pytest.raises(ValueError, match="Frozen plan"):
        m.verify_reusable_preflight(plan, tmp_path, spec)
    plan["max_preflight_calls"] = 2
    (tmp_path / "preflight/extra.json").write_text("[]")
    with pytest.raises(ValueError, match="Preflight inventory"):
        m.verify_reusable_preflight(plan, tmp_path, spec)

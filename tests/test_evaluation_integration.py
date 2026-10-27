"""Regression checks for the actual runner formats and analysis boundaries."""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from pe6203 import evaluation as ev
from pe6203.evidence_audit import audit, inspect_entry, score_run, token_count

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "experiments/evaluation/pilot-evidence.json"


def test_preserved_real_evidence_is_not_formal():
    result = audit(ev.read(MANIFEST), ROOT)
    rows = {r["evidence_id"]: r for r in result["runs"]}
    assert len(rows) == 7
    assert sum(r["score_check"] == "verified" for r in rows.values()) == 4
    assert rows["early-v2"]["verified_TF"] == 9.8
    assert rows["middle-a-full-rewrite"]["verified_TF"] == 8.4
    assert rows["middle-b-no_update"]["verified_TF"] == 8.2
    assert rows["middle-b-full_rewrite"]["verified_PE"] == 7.2
    assert rows["early-incomplete"]["verified_TF"] is None
    assert all(r["ECS"] is None and r["formal_eligible"] is False for r in rows.values())
    assert rows["middle-a-full-rewrite"]["execution_status"] == "max_rounds"


def test_bundle_null_error_is_not_failure():
    e = ev.read(MANIFEST)["entries"][1]
    row, *_ = inspect_entry(e, ROOT)
    assert row["score_check"] == "verified"


def test_original_judge_response_disagreement_rejected():
    base = ROOT / "results/evidence/full-rewrite-20261019/execution"
    result = ev.read(base / "result.json")
    evaluation = ev.read(base / "EVAL/139.json")
    evaluation["eval_result"]["runs"][0]["result"]["task_fulfillment"] = 10
    assert score_run(result, evaluation)[1] == "raw_judge_response_mismatch"


def test_result_eval_identity_mismatch():
    with pytest.raises(ValueError, match="task ID"):
        score_run({"task_id": 1, "status": "evaluated", "judge_status": "complete"}, {"idx": 2})


@pytest.mark.parametrize(
    "payload", [[], None, {"eval_result": None}, {"eval_result": {"runs": [None] * 5}}]
)
def test_malformed_judge_record_excluded(payload):
    assert ev.judge_scores(payload)[0] is None


def test_pilot_hash_tamper():
    entry = copy.deepcopy(ev.read(MANIFEST)["entries"][0])
    entry["path_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="hash mismatch"):
        inspect_entry(entry, ROOT)


def test_current_development_id_excluded():
    manifest = ev.read(ROOT / "experiments/evaluation/analysis-manifest.json")
    manifest.update(
        evidence_kind="synthetic_software_test",
        experiment_id="test",
        comparison_config_file_sha256="test",
    )
    manifest["tasks"] = [{"task_id": 223}]
    with pytest.raises(ValueError, match="development"):
        ev.validate_manifest(manifest, demo=True)


def test_formal_rejects_real_pilot():
    result = ev.read(ROOT / "results/evidence/full-rewrite-20261019/execution/result.json")
    with pytest.raises(ValueError, match="Pilot"):
        ev.validate_formal_result(result, {})


def test_formal_config_digest_checked():
    config = {"agent": {"model": "fixed-test-model"}}
    manifest = {"benchmark_commit": "b", "dataset_revision": "d"}
    result = {
        **manifest,
        "strategy": "no_update",
        "protocol_sha256": "p",
        "config": config,
        "config_sha256": hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest(),
    }
    ev.validate_formal_result(result, manifest)
    result["config"]["agent"]["model"] = "different-model"
    with pytest.raises(ValueError, match="digest"):
        ev.validate_formal_result(result, manifest)


def test_frozen_comparison_config_checked(tmp_path):
    p = tmp_path / "config.json"
    p.write_text("{}")
    m = {"comparison_config_path": p.name, "comparison_config_file_sha256": ev.digest(p)}
    ev.check_comparison_config(m, tmp_path)
    p.write_text('{"changed": true}')
    with pytest.raises(ValueError):
        ev.check_comparison_config(m, tmp_path)


def test_historical_and_current_cost_aliases():
    assert token_count({"tokens": 18831}) == 18831
    assert token_count({"total_tokens": 18831}) == 18831
    assert token_count({"tokens": None}) is None
    with pytest.raises(ValueError):
        token_count({"tokens": 1, "total_tokens": 2})


def test_unattributed_errors_not_promoted_to_required_cases():
    result = audit(ev.read(MANIFEST), ROOT)
    assert len(result["unattributed_tool_errors"]) == 2
    assert all(not r["under_or_over_update_confirmed"] for r in result["unattributed_tool_errors"])
    assert all(r["tool"] for r in result["unattributed_tool_errors"])


def test_protocol_mismatch_rejected(tmp_path):
    m = {
        "tasks": [{"task_id": 1}],
        "repeat_ids": [0],
        "experiment_id": "test",
        "comparison_config_file_sha256": "test",
        "evidence_kind": "synthetic_software_test",
    }
    ledger = {"runs": []}
    for s in ev.STRATEGIES:
        scores = {k: 5 for k in ev.SCORES}
        evaluation = {
            "idx": 1,
            "eval_result": {
                "runs": [{"result": scores}] * 5,
                "aggregate": {
                    "successful_runs": 5,
                    "total_runs": 5,
                    **{k + "_mean": 5 for k in ev.SCORES},
                },
            },
        }
        result = {
            "task_id": 1,
            "version": "early",
            "strategy": s,
            "seed": 0,
            "status": "evaluated",
            "judge_status": "complete",
            "TF": 5,
            "PE": 5,
            "config_sha256": "config",
            "protocol_sha256": s,
        }
        rp, ep = tmp_path / (s + ".json"), tmp_path / (s + "-eval.json")
        rp.write_text(json.dumps(result))
        ep.write_text(json.dumps(evaluation))
        ledger["runs"].append(
            {
                "task_id": 1,
                "stage": "early",
                "strategy": s,
                "repeat_id": 0,
                "attempt_id": 0,
                "experiment_id": "test",
                "comparison_config_file_sha256": "test",
                "expected_config_sha256": "config",
                "selected_for_analysis": True,
                "result_path": rp.name,
                "result_path_sha256": ev.digest(rp),
                "eval_path": ep.name,
                "eval_path_sha256": ev.digest(ep),
            }
        )
    with pytest.raises(ValueError, match="Mixed runner protocols"):
        ev.load_runs(m, ledger, tmp_path)


def test_execution_cost_includes_failed_and_unselected_attempts():
    rows = [
        {
            "strategy": "full_rewrite",
            "selected_for_analysis": selected,
            "execution_status": status,
            "cost": {"agent": {"total_tokens": tokens}},
        }
        for selected, status, tokens in [(False, "failed", 30), (True, "completed", 70)]
    ]
    table = ev.execution_costs(rows)
    row = next(x for x in table if x["strategy"] == "full_rewrite" and x["role"] == "agent")
    assert row["total_tokens_total"] == 100
    assert row["attempts"] == 2
    assert row["usd_total"] is None
    assert row["usd_missing_attempts"] == 2


def test_execution_cost_partial_total_is_not_complete_total():
    rows = [
        {"strategy": "no_update", "cost": {"agent": {"total_tokens": 10}}},
        {"strategy": "no_update", "cost": {}},
    ]
    row = ev.execution_costs(rows)[0]
    assert row["total_tokens_known_sum"] == 10
    assert row["total_tokens_total"] is None
    assert row["total_tokens_missing_attempts"] == 1


def test_execution_cost_rejects_boolean():
    with pytest.raises(ValueError):
        ev.execution_costs([{"strategy": "no_update", "cost": {"agent": {"usd": True}}}])

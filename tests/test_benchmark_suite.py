"""Freeze boundaries and CLI-to-analysis integration, using synthetic scores only."""

import copy
import hashlib
import json

import pytest

from pe6203 import evaluation, experiment
from pe6203.benchmark import write_json


def test_suite_rejects_drift_and_unreviewed_labels(tmp_path):
    from pe6203.benchmark_suite import validate_suite

    catalog = tmp_path / "catalogs/105/early.json"
    write_json(catalog, {"tools": []})
    suite = {
        "suite_id": "test",
        "benchmark_commit": "pin",
        "dataset_revision": "data",
        "tasks": [
            {
                "task_id": 105,
                "review_evidence": "review.json",
                "transitions": {
                    v: {"label": "changed", "change_types": ["PARAM"]} for v in ["middle", "late"]
                },
            }
        ],
        "catalog_sha256": {"catalogs/105/early.json": experiment.sha(catalog)},
    }
    validate_suite(suite, tmp_path, {"commit": "pin", "dataset_revision": "data"})
    bad = copy.deepcopy(suite)
    bad["tasks"][0]["transitions"]["late"]["label"] = "unreviewed"
    with pytest.raises(ValueError, match="label"):
        validate_suite(bad, tmp_path, {"commit": "pin", "dataset_revision": "data"})
    catalog.write_text("{}")
    with pytest.raises(ValueError, match="catalog"):
        validate_suite(suite, tmp_path, {"commit": "pin", "dataset_revision": "data"})


def synthetic_matrix(tmp_path):
    plan = {
        "kind": "benchmark",
        "formal_evaluation": True,
        "benchmark_commit": "pin",
        "dataset_revision": "data",
        "config": {"agent": {"model": "fixture"}, "judge_runs": 5},
        "cells": experiment.make_cells([105, 235], experiment.STAGES, experiment.STRATEGIES, 1),
        "suite": {
            "suite_id": "test",
            "tasks": [
                {
                    "task_id": t,
                    "review_evidence": "synthetic test",
                    "transitions": {
                        v: {"label": label, "change_types": ["PARAM"] if label == "changed" else []}
                        for v in ["middle", "late"]
                    },
                }
                for t, label in [(105, "changed"), (235, "unaffected")]
            ],
        },
    }
    write_json(tmp_path / "plan.json", plan)
    for cell in plan["cells"]:
        directory = tmp_path / "cells" / cell["id"]
        config = {
            **plan["config"],
            "root": "/synthetic",
            "output_dir": str(directory / "run"),
            "adaptation_path": str(directory / "adaptation/adaptation.json"),
        }
        tf = (
            (6 if cell["strategy"] == "no_update" else 8)
            if cell["task_id"] == 105
            else (9 if cell["strategy"] != "full_rewrite" else 7)
        )
        payload = {
            "idx": cell["task_id"],
            "eval_result": {
                "runs": [
                    {
                        "result": {
                            "task_fulfillment": tf,
                            "planning_and_efficiency": 7,
                            "grounding": 9,
                        }
                    }
                    for _ in range(5)
                ],
                "aggregate": {
                    "successful_runs": 5,
                    "total_runs": 5,
                    "task_fulfillment_mean": tf,
                    "planning_and_efficiency_mean": 7,
                    "grounding_mean": 9,
                },
            },
        }
        result = {
            "task_id": cell["task_id"],
            "version": cell["version"],
            "strategy": cell["strategy"],
            "seed": cell["seed"],
            "config": config,
            "config_sha256": hashlib.sha256(
                json.dumps(config, sort_keys=True).encode()
            ).hexdigest(),
            "protocol_sha256": "same",
            "benchmark_commit": "pin",
            "dataset_revision": "data",
            "status": "evaluated",
            "execution_status": "output_truncated"
            if cell["strategy"] == "full_rewrite"
            else "completed",
            "judge_status": "complete",
            "TF": tf,
            "PE": 7,
            "cost": {},
        }
        write_json(directory / "run/result.json", result)
        write_json(directory / "run/EVAL" / f"{cell['task_id']}.json", payload)
        write_json(
            directory / "adaptation/adaptation.json",
            {"status": "validated", "cost": {"total_tokens": 0, "seconds": 0, "usd": 0}},
        )
    return plan


def test_analysis_bridge_matches_recovery_retention_and_retains_missing(tmp_path):
    from pe6203.benchmark_suite import analyze

    plan = synthetic_matrix(tmp_path)
    report = analyze(tmp_path, plan)
    recovery = next(
        r
        for r in report["recovery_retention"]
        if r["stage"] == "late"
        and r["strategy"] == "selective_patch"
        and r["subgroup"] == "changed"
    )
    retention = next(
        r
        for r in report["recovery_retention"]
        if r["stage"] == "late"
        and r["strategy"] == "full_rewrite"
        and r["subgroup"] == "unaffected"
    )
    assert recovery["delta_vs_no_update_same_stage"] == 2
    assert retention["delta_vs_no_update_same_stage"] == -2
    assert report["completeness"][1]["attempt_execution_failures"] == 6
    # One missing judge invalidates this matched triplet for all strategies, not just itself.
    ep = tmp_path / "cells/task105-late-full_rewrite-r0/run/EVAL/105.json"
    payload = evaluation.read(ep)
    payload["eval_result"]["runs"].pop()
    write_json(ep, payload)
    report = analyze(tmp_path, plan)
    assert all(r["matched_triplets"] == 1 for r in report["ecs"])
    assert (
        next(
            r
            for r in report["recovery_retention"]
            if r["stage"] == "late" and r["subgroup"] == "changed"
        )["matched_cells"]
        == 0
    )
    assert (tmp_path / "analysis/run-ledger.json").exists()


def test_analysis_bridge_rejects_config_changed_for_one_method(tmp_path):
    from pe6203.benchmark_suite import analyze

    plan = synthetic_matrix(tmp_path)
    path = tmp_path / "cells/task105-late-selective_patch-r0/run/result.json"
    result = evaluation.read(path)
    result["config"]["agent"]["model"] = "different"
    result["config_sha256"] = hashlib.sha256(
        json.dumps(result["config"], sort_keys=True).encode()
    ).hexdigest()
    write_json(path, result)
    with pytest.raises(ValueError, match="common configuration"):
        analyze(tmp_path, plan)


def test_suite_prepare_rejects_partial_matrix_and_custom_model_config(tmp_path):
    suite_path = tmp_path / "suite.json"
    write_json(suite_path, {"tasks": [{"task_id": 105}], "config_path": "unused.json"})
    with pytest.raises(ValueError, match="all three"):
        experiment.prepare(
            tmp_path, tmp_path / "output", None, stages=["late"], suite_path=suite_path
        )
    with pytest.raises(ValueError, match="fixed suite"):
        experiment.prepare(tmp_path, tmp_path / "output", [139], suite_path=suite_path)
    with pytest.raises(ValueError, match="configuration"):
        experiment.prepare(
            tmp_path, tmp_path / "output", None, config_path="different.json", suite_path=suite_path
        )
    assert not (tmp_path / "output").exists()

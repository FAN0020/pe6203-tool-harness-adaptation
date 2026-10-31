"""Development experiments: fixed cells, durable resume, and honest missing scores."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_experiment_cli_is_available_without_credentials():
    result = subprocess.run(
        [sys.executable, "-m", "pe6203.cli", "experiment", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "prepare" in result.stdout and "run" in result.stdout


def test_matrix_keeps_same_tasks_repeats_and_three_strategies():
    from pe6203.experiment import make_cells

    cells = make_cells(
        [139], ["early", "middle", "late"], ["no_update", "full_rewrite", "selective_patch"], 1
    )
    assert len(cells) == 9
    assert len({c["id"] for c in cells}) == 9
    assert {c["seed"] for c in cells} == {0}
    assert {c["task_id"] for c in cells} == {139}
    with pytest.raises(ValueError):
        make_cells([139, 139], ["early"], ["no_update"], 1)
    with pytest.raises(ValueError):
        make_cells([139], ["early"], ["no_update"], 0)


def test_frozen_files_detect_changed_updater_implementation(tmp_path):
    from pe6203.experiment import freeze_files, verify_files

    (tmp_path / "integration").mkdir()
    p = tmp_path / "integration/baselines.py"
    p.write_text("original")
    hashes = freeze_files(tmp_path, [p])
    verify_files(tmp_path, hashes)
    p.write_text("changed")
    with pytest.raises(ValueError, match="changed"):
        verify_files(tmp_path, hashes)


def test_summary_does_not_complete_ecs_or_hide_max_rounds(tmp_path):
    from pe6203.experiment import summarize

    plan = {
        "schema_version": "experiment-1",
        "kind": "development",
        "judge_runs": 5,
        "cells": [
            {"id": "one", "task_id": 139, "version": "early", "strategy": "no_update", "seed": 0}
        ],
    }
    (tmp_path / "plan.json").write_text(json.dumps(plan))
    directory = tmp_path / "cells/one/run"
    directory.mkdir(parents=True)
    (directory / "result.json").write_text(
        json.dumps(
            {
                "status": "evaluated",
                "execution_status": "max_rounds",
                "judge_status": "complete",
                "TF": 9,
                "PE": 8,
                "cost": {"agent": {"total_tokens": 40, "usd": None}},
            }
        )
    )
    # Summary must audit all five judge records, not trust the aggregate alone.
    result = summarize(tmp_path)
    assert result["rows"][0]["TF"] is None
    assert result["rows"][0]["execution_status"] == "max_rounds"
    assert result["ecs"][0]["upstream_population"] is None
    assert result["cost"]["agent"]["usd"] is None


def test_resume_retains_failed_adaptation_and_does_not_call_model(tmp_path, monkeypatch):
    from pe6203 import experiment

    cell = {"id": "one", "task_id": 139, "version": "late", "strategy": "full_rewrite", "seed": 0}
    plan = {
        "schema_version": "experiment-1",
        "kind": "development",
        "judge_runs": 5,
        "cells": [cell],
        "files": {},
        "endpoints": {},
        "config": {},
        "updater": {},
    }
    (tmp_path / "plan.json").write_text(json.dumps(plan))
    failed = tmp_path / "cells/one/adaptation"
    failed.mkdir(parents=True)
    (failed / "adaptation.json").write_text(
        json.dumps(
            {
                "status": "failed",
                "cost": {"total_tokens": 23, "usd": 0.01},
                "validation": {"errors": ["invalid model output"]},
            }
        )
    )
    monkeypatch.setattr(experiment, "check_plan", lambda *args, **kwargs: None)
    # Any accidental retry reaches missing input files and fails this test.
    ledger = experiment.run_experiment(ROOT, tmp_path, resume=True)
    assert ledger["cells"]["one"]["status"] == "adaptation_failed"
    assert not (tmp_path / "cells/one/run").exists()
    assert experiment.summarize(tmp_path)["cost"]["update"]["total_tokens"] == 23


def test_summary_rejects_modified_completed_evidence(tmp_path):
    from pe6203 import experiment

    (tmp_path / "plan.json").write_text(json.dumps({"cells": []}))
    evidence = tmp_path / "result.json"
    evidence.write_text("original")
    files = experiment.freeze_files(tmp_path, [evidence])
    (tmp_path / "experiment.json").write_text(json.dumps({"cells": {"one": {"files": files}}}))
    evidence.write_text("changed")
    with pytest.raises(ValueError, match="changed"):
        experiment.summarize(tmp_path)


def test_same_experiment_cannot_have_two_writers(tmp_path):
    from pe6203.experiment import writer_lock

    with writer_lock(tmp_path):
        with pytest.raises(ValueError, match="already running"):
            with writer_lock(tmp_path):
                pass
    with writer_lock(tmp_path):
        pass


def test_matrix_stops_after_two_transport_failures_preserving_pending_cells(tmp_path, monkeypatch):
    from pe6203 import experiment
    from pe6203.benchmark import write_json

    cells = [
        {"id": str(i), "task_id": 105 + i, "version": "early", "strategy": "no_update", "seed": 0}
        for i in range(4)
    ]
    write_json(
        tmp_path / "plan.json",
        {"cells": cells, "config": {}, "updater": {}, "stop_after_infrastructure_failures": 2},
    )
    monkeypatch.setattr(experiment, "check_plan", lambda *args: None)

    def adaptation(old, target, strategy, directory, context):
        write_json(directory / "adaptation.json", {"status": "validated", "cost": {}})

    def failed(task, version, strategy, seed, config):
        result = {
            "status": "blocked",
            "failure_category": "model_transport",
            "execution_status": "failed",
        }
        write_json(Path(config["output_dir"]) / "result.json", result)
        return {}, result

    monkeypatch.setattr(experiment, "write_adaptation", adaptation)
    monkeypatch.setattr(experiment, "run", failed)
    ledger = experiment.run_experiment(ROOT, tmp_path)
    assert len(ledger["cells"]) == 2
    assert ledger["stop_reason"] == "consecutive_model_transport_failures"
    assert not (tmp_path / "cells/2").exists()


def test_resume_continues_pending_judge_without_repeating_agent(tmp_path, monkeypatch):
    from pe6203 import experiment
    from pe6203.benchmark import write_json

    cell = {"id": "one", "task_id": 139, "version": "late", "strategy": "no_update", "seed": 0}
    write_json(
        tmp_path / "plan.json", {"cells": [cell], "config": {"judge_recovery": {}}, "updater": {}}
    )
    directory = tmp_path / "cells/one/run"
    write_json(directory / "execution-checkpoint.json", {"saved": "execution"})
    write_json(
        directory / "result.json",
        {"status": "judge_pending", "judge_recovery": {"resumable": True}},
    )
    write_json(
        tmp_path / "experiment.json", {"cells": {"one": {"status": "judge_pending", "files": {}}}}
    )
    monkeypatch.setattr(experiment, "check_plan", lambda *a: None)
    monkeypatch.setattr(experiment, "run", lambda *a: pytest.fail("Agent must not rerun"))

    def resume(output):
        result = {"status": "evaluated", "execution_status": "completed"}
        write_json(output / "result.json", result)
        return {}, result

    monkeypatch.setattr(experiment, "resume_judging", resume, raising=False)
    ledger = experiment.run_experiment(ROOT, tmp_path, resume=True)
    assert ledger["cells"]["one"]["status"] == "evaluated"


def test_judge_outage_stops_next_cell_instead_of_hiding_inside_score_failure(tmp_path, monkeypatch):
    from pe6203 import experiment
    from pe6203.benchmark import write_json

    cells = [
        {"id": str(i), "task_id": 139, "version": "early", "strategy": "no_update", "seed": i}
        for i in range(3)
    ]
    write_json(tmp_path / "plan.json", {"cells": cells, "config": {}, "updater": {}})
    monkeypatch.setattr(experiment, "check_plan", lambda *a: None)
    monkeypatch.setattr(
        experiment,
        "write_adaptation",
        lambda a, b, c, d, e: write_json(d / "adaptation.json", {"status": "validated"}),
    )

    def run(task, version, strategy, seed, config):
        result = {
            "status": "judge_pending",
            "failure_category": "model_transport",
            "judge_recovery": {"paused": True, "resumable": True},
        }
        write_json(Path(config["output_dir"]) / "result.json", result)
        return {}, result

    monkeypatch.setattr(experiment, "run", run)
    ledger = experiment.run_experiment(ROOT, tmp_path)
    assert len(ledger["cells"]) == 1
    assert ledger["stop_reason"] == "judge_transport_outage"
    assert not (tmp_path / "cells/1").exists()

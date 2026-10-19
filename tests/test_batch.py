import json

import pytest
from test_contract import module


def test_batch_resumes_without_replacing_low_scores_and_rejects_changed_knowledge(
    tmp_path, monkeypatch
):
    batch = module("batch")
    (tmp_path / "config.json").write_text('{"agent":{},"judge":{}}')
    (tmp_path / "knowledge.json").write_text('{"tools":[]}')
    plan = {
        "experiment_id": "dev",
        "config_path": "config.json",
        "runs": [
            {
                "task_id": 139,
                "version": "early",
                "strategy": "no_update",
                "seed": 0,
                "knowledge_path": "knowledge.json",
            },
            {
                "task_id": 139,
                "version": "late",
                "strategy": "no_update",
                "seed": 0,
                "knowledge_path": "knowledge.json",
            },
        ],
    }
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))

    def model_boundary(task_id, version, strategy, seed, config):
        from pathlib import Path

        output = Path(config["output_dir"])
        output.mkdir(parents=True, exist_ok=False)
        result = {
            "task_id": task_id,
            "version": version,
            "strategy": strategy,
            "seed": seed,
            "status": "evaluated" if version == "early" else "judge_incomplete",
            "judge_status": "complete" if version == "early" else "incomplete",
            "TF": 1,
            "PE": 2,
            "cost": {},
            "errors": [],
        }
        (output / "result.json").write_text(json.dumps(result))
        return {}, result

    monkeypatch.setattr(batch, "run", model_boundary)
    output = tmp_path / "batch"
    first = batch.run_batch(tmp_path, plan_path, output)
    resumed = batch.run_batch(tmp_path, plan_path, output, resume=True)
    assert first == resumed
    assert first["runs"][0]["result"]["TF"] == 1
    assert len(list(output.rglob("result.json"))) == 2
    assert first["runs"][1]["status"] == "incomplete"
    (tmp_path / "knowledge.json").write_text('{"tools":["CHANGED"]}')
    with pytest.raises(ValueError, match="identity"):
        batch.run_batch(tmp_path, plan_path, output, resume=True)


def test_batch_rejects_duplicate_cells_before_creating_output(tmp_path):
    batch = module("batch")
    (tmp_path / "config.json").write_text('{"agent":{},"judge":{}}')
    (tmp_path / "knowledge.json").write_text("{}")
    cell = {
        "task_id": 139,
        "version": "early",
        "strategy": "no_update",
        "seed": 0,
        "knowledge_path": "knowledge.json",
    }
    plan = {"experiment_id": "dev", "config_path": "config.json", "runs": [cell, cell]}
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(plan))
    with pytest.raises(ValueError, match="Duplicate"):
        batch.run_batch(tmp_path, p, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_batch_recovers_written_result_after_interruption_without_another_attempt(
    tmp_path, monkeypatch
):
    batch = module("batch")
    (tmp_path / "config.json").write_text('{"agent":{},"judge":{}}')
    (tmp_path / "knowledge.json").write_text("{}")
    cell = {
        "task_id": 139,
        "version": "early",
        "strategy": "no_update",
        "seed": 0,
        "knowledge_path": "knowledge.json",
    }
    plan = tmp_path / "plan.json"
    plan.write_text(
        json.dumps({"experiment_id": "recovery", "config_path": "config.json", "runs": [cell]})
    )
    attempts = []

    def boundary(task_id, version, strategy, seed, config):
        from pathlib import Path

        directory = Path(config["output_dir"])
        directory.mkdir(parents=True)
        result = {k: cell[k] for k in ("task_id", "version", "strategy", "seed")}
        result.update(status="evaluated", judge_status="complete", TF=2, PE=3)
        (directory / "result.json").write_text(json.dumps(result))
        attempts.append(directory)
        raise KeyboardInterrupt("crash after durable result")

    monkeypatch.setattr(batch, "run", boundary)
    output = tmp_path / "batch"
    with pytest.raises(KeyboardInterrupt):
        batch.run_batch(tmp_path, plan, output)
    ledger = batch.run_batch(tmp_path, plan, output, resume=True)
    assert len(attempts) == 1
    assert ledger["runs"][0]["status"] == "complete"
    assert ledger["runs"][0]["result"]["TF"] == 2
    (attempts[0] / "result.json").write_text("{}")
    with pytest.raises(ValueError, match="modified"):
        batch.run_batch(tmp_path, plan, output, resume=True)

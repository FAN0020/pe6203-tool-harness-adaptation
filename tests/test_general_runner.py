import json
from pathlib import Path

import pytest
from test_contract import module, record


def test_selected_non_smoke_task_reaches_credential_preflight(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    upstream = tmp_path / "upstream"
    data = upstream / "src/custom/data/test_cases"
    data.mkdir(parents=True)
    (data / "chosen_idx.json").write_text(json.dumps({"samples": [{"idx": 201}]}))
    (data / "test_cases.json").write_text(
        json.dumps([{"idx": 201, "question": "Task", "servers": {"server": ["old_tool"]}}])
    )
    lock = {
        "commit": "pin",
        "dataset_revision": "release",
        "smoke_task_id": 139,
        "servers": {"server": "index.js"},
        "stages": {"early": {"directory": "original"}},
    }
    runner = module("runner")
    monkeypatch.setattr(runner, "source", lambda root: (lock, upstream))
    monkeypatch.delenv("AGENT_API_KEY", raising=False)
    knowledge = tmp_path / "knowledge.json"
    knowledge.write_text(
        json.dumps({"benchmark_commit": "pin", "version": "early", "tools": [record()]})
    )
    config = json.loads((root / "configs/smoke.json").read_text())
    config.update(
        root=str(tmp_path), output_dir=str(tmp_path / "run"), knowledge_path=str(knowledge)
    )
    trace, result = runner.run(201, "early", "no_update", 0, config)
    assert result["TF"] is None
    assert "AGENT_API_KEY" in result["errors"][0]["message"]
    assert trace["idx"] == 201 and trace["question"] == "Task"


def test_fixture_copy_records_content_hashes_and_rejects_symlinks(tmp_path):
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    (fixture / "input.txt").write_text("fixed input")
    copy_fixture = module("runner").prepare_fixture
    output = tmp_path / "workspace"
    output.mkdir()
    result = copy_fixture(fixture, output)
    assert (output / "input.txt").read_text() == "fixed input"
    assert result["files"][0]["path"] == "input.txt"
    assert len(result["files"][0]["sha256"]) == 64
    (fixture / "escape").symlink_to(tmp_path)
    other = tmp_path / "blocked"
    other.mkdir()
    with pytest.raises(ValueError, match="symlink"):
        copy_fixture(fixture, other)
    assert not list(other.iterdir())

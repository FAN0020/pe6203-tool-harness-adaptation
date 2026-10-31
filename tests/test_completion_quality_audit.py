"""Evidence extraction must not turn a judge score into a completion/quality claim."""

import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_completion_quality.py"


def write_archive(path, files):
    with tarfile.open(path, "w:gz") as archive:
        for name, value in files.items():
            data = json.dumps(value).encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))


def invoke(archive, output):
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(archive), "--output", str(output)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_high_score_does_not_mask_truncation_or_unknown_charge(tmp_path):
    prefix = "trial/cells/task283-late-example-r0/run/"
    archive = tmp_path / "raw.tar.gz"
    write_archive(
        archive,
        {
            prefix + "result.json": {
                "task_id": 283,
                "version": "late",
                "strategy": "example",
                "execution_status": "output_truncated",
                "TF": 10,
                "PE": 10,
                "cost": {"agent": {"known_usd": 0.01, "usd": None}},
            },
            prefix + "raw_trace.json": {
                "question": "Create a project",
                "answer": "",
                "stop": False,
                "exceeded": False,
                "events": [
                    {
                        "type": "tool_result",
                        "round": 1,
                        "call": {
                            "id": "incomplete",
                            "function": {"name": "create_task__abc", "arguments": '{"id":'},
                        },
                        "result": {"isError": True, "error": "invalid JSON"},
                    }
                ],
            },
        },
    )
    original = archive.read_bytes()
    result = invoke(archive, tmp_path / "audit")
    assert result.returncode == 0, result.stderr
    data = json.loads((tmp_path / "audit/facts.json").read_text())
    row = data["cells"][0]
    assert row["execution_status"] == "output_truncated"
    assert row["original_scores"] == {"TF": 10, "PE": 10}
    assert not row["has_final_answer"]
    assert row["invalid_json_call_ids"] == ["incomplete"]
    assert row["tool_error_count"] == 1
    assert row["cost"]["agent"] == {"known_usd": 0.01, "total_usd": None}
    assert data["summary"]["example"]["completed"] == 0
    assert archive.read_bytes() == original


def test_persisted_parents_and_leaves_are_counted_separately(tmp_path):
    prefix = "trial/cells/task283-middle-example-r0/run/"
    archive = tmp_path / "raw.tar.gz"
    write_archive(
        archive,
        {
            prefix + "result.json": {
                "task_id": 283,
                "version": "middle",
                "strategy": "example",
                "execution_status": "completed",
            },
            prefix + "raw_trace.json": {"events": [], "answer": "All tasks are 2–4."},
            prefix + "workspace/.agentic-tools-mcp/tasks/tasks.json": {
                "projects": [{"id": "p"}],
                "tasks": [
                    {"id": "parent", "projectId": "p", "complexity": 7},
                    {
                        "id": "leaf",
                        "projectId": "p",
                        "parentId": "parent",
                        "complexity": 3,
                        "estimatedHours": 8,
                    },
                    {"id": "orphan", "projectId": "p", "parentId": "missing"},
                ],
            },
        },
    )
    result = invoke(archive, tmp_path / "audit")
    assert result.returncode == 0, result.stderr
    row = json.loads((tmp_path / "audit/facts.json").read_text())["cells"][0]
    facts = row["task_store"]
    assert facts["task_count"] == 3
    assert facts["parent_ids"] == ["parent"]
    assert facts["leaf_ids"] == ["leaf", "orphan"]
    assert facts["complexity_all"] == {"min": 3, "max": 7, "known": 2, "unknown": 1}
    assert facts["complexity_leaves"] == {"min": 3, "max": 3, "known": 1, "unknown": 1}
    assert facts["dangling_parents"] == [{"id": "orphan", "parentId": "missing"}]
    assert facts["leaf_hours"] == {"known_total": 8, "unknown": 1}
    assert row["original_scores"] == {"TF": None, "PE": None}


def test_archived_development_facts_reproduce_the_known_completion_and_claim_mismatch(tmp_path):
    archive = ROOT / "results/evidence/selective-search-20261031/development-v3.tar.gz"
    result = invoke(archive, tmp_path / "audit")
    assert result.returncode == 0, result.stderr
    data = json.loads((tmp_path / "audit/facts.json").read_text())
    assert len(data["cells"]) == 18
    assert data["summary"]["budget_feedback"]["completed"] == 6
    assert data["summary"]["selective_patch"]["completed"] == 5
    row = next(c for c in data["cells"] if c["cell_id"] == "task283-middle-budget_feedback-r0")
    assert row["task_store"]["task_count"] == 24
    assert len(row["task_store"]["leaf_ids"]) == 20
    assert row["task_store"]["complexity_all"]["max"] == 5
    assert row["task_store"]["complexity_leaves"]["max"] == 4
    assert row["original_scores"] == {"TF": 10, "PE": 9.8}
    assert "Every task sits at complexity 2–4" in row["answer"]
    # A second invocation cannot overwrite the first review or historic inputs.
    before = (tmp_path / "audit/facts.json").read_bytes()
    second = invoke(archive, tmp_path / "audit")
    assert second.returncode != 0
    assert (tmp_path / "audit/facts.json").read_bytes() == before

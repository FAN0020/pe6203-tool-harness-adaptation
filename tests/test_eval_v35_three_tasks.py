"""Protect the new paid batch from coverage and input-drift errors."""

from collections import Counter

import pytest

from scripts import eval_v35_three_tasks as batch


def test_original_three_tasks_have_three_executions_per_arm_and_stage():
    cells = batch.make_cells()
    assert len(cells) == 54
    assert len({c["id"] for c in cells}) == 54
    counts = Counter((c["task_id"], c["stage"], c["arm"]) for c in cells)
    assert set(counts.values()) == {3}
    assert {c["task_id"] for c in cells} == {133, 235, 283}
    assert all(c["strategy"] == "selective_patch" for c in cells)
    for c in cells:
        assert c["adaptation"] == f"adaptations/{c['task_id']}/{c['stage']}/{c['arm']}/adaptation.json"


def test_changed_frozen_input_stops_before_paid_execution(tmp_path):
    p = tmp_path / "catalog.json"
    p.write_text("original")
    plan = {"source_files_sha256": {}, "catalogs_sha256": {p.name: batch.common.sha(p)},
            "capability_evidence_sha256": {}}
    batch.verify(tmp_path, tmp_path, plan)
    p.write_text("changed")
    with pytest.raises(ValueError, match="Frozen input changed"):
        batch.verify(tmp_path, tmp_path, plan)


def test_preparation_cannot_overwrite_existing_evidence(tmp_path):
    with pytest.raises(ValueError, match="fresh output"):
        batch.prepare(tmp_path, tmp_path)

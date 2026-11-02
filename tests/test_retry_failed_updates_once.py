"""Protect retry coverage and immutable original evidence before paid calls."""

from pathlib import Path

import pytest

from pe6203.benchmark import read_json
from scripts import retry_failed_updates_once as retry


def test_retry_set_covers_every_missing_condition_and_no_successful_condition():
    root = Path(__file__).parents[1]
    inventory = read_json(root / "evaluation/supplements/five-task-20261103/five-task-coverage.json")["rows"]
    missing = {(r["arm"], r["task_id"], r["stage"]) for r in inventory
               if r["arm"] in retry.ARMS and (r["TF"] is None or r["PE"] is None)}
    assert set(retry.CONDITIONS) == missing
    assert len(retry.CONDITIONS) == len(set(retry.CONDITIONS)) == 7


def test_modifying_original_record_stops_the_experiment(tmp_path):
    p = tmp_path / "original.json"
    p.write_text('{"status":"failed"}')
    plan = {"original_record_hashes": {p.name: retry.common.sha(p)}}
    retry.check_originals(tmp_path, plan)
    p.write_text('{"status":"success"}')
    with pytest.raises(ValueError, match="Original result changed"):
        retry.check_originals(tmp_path, plan)


def test_preparation_cannot_overwrite_an_existing_retry(tmp_path):
    with pytest.raises(ValueError, match="new directory"):
        retry.prepare(tmp_path, tmp_path)

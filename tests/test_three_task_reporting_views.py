"""Keep retrospective task alignment complete and explicit about retries."""

from pathlib import Path

import pytest

from pe6203.benchmark import read_json
from scripts.build_three_task_views import TASKS, make_view, metrics, read_source

ROOT = Path(__file__).parents[1]


@pytest.mark.parametrize("version", ["v3", "v5"])
def test_views_reproduce_pinned_sources_without_dropping_first_failures(version):
    from scripts.build_three_task_views import FIRST_PATH, RETRY_PATH

    first, _ = read_source(ROOT, FIRST_PATH)
    retry, _ = read_source(ROOT, RETRY_PATH)
    before, after = make_view(first, retry, version)
    assert len(before) == len(after) == 27
    assert {r["task_id"] for r in before} == {r["task_id"] for r in after} == set(TASKS)
    assert sum(r.get("TF") is None for r in before) == 3
    assert sum(r.get("TF") is None for r in after) == 0
    for name, rows in [("first-attempt", before), ("one-retry", after)]:
        published = read_json(ROOT / f"evaluation/{version}/three-task-view/{name}.json")
        assert published["rows"] == rows
        assert published["metrics"] == metrics(rows)
        assert published["raw_records_changed"] is False


def test_retry_view_accepts_a_lower_score_instead_of_selecting_only_improvements():
    row = {"arm": "v3", "task_id": 133, "stage": "early", "repeat": 1, "TF": None, "PE": None}
    first = {"rows": [{**row, "task_id": task, "stage": stage, "repeat": repeat}
                      for task in TASKS for stage in ("early", "middle", "late") for repeat in (1, 2, 3)]}
    retry = {"rows": [{**row, "TF": 1, "PE": 1}]}
    _, after = make_view(first, retry, "v3")
    selected = next(r for r in after if r["task_id"] == 133 and r["stage"] == "early" and r["repeat"] == 1)
    assert selected["TF"] == selected["PE"] == 1
    assert selected["source_attempt"] == "one_retry"

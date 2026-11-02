"""Recorded-data arithmetic and provenance checks; no inference requests."""

import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[2]


def module():
    path = BASE / "code/scripts/refresh_selected_summary.py"
    spec = importlib.util.spec_from_file_location("v6_selected_summary", path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def inputs():
    root = BASE / "recorded-results/original-r4"

    def load(path):
        return json.loads(path.read_text())

    return (
        load(root / "summary.json"),
        load(BASE / "repeats/math-middle-20261103-01/repeat-summary.json"),
        load(root / "comparison.json"),
        load(root / "baseline-cells.json")["cells"],
    )


def test_selected_math_middle_changes_only_one_score_and_keeps_inputs():
    args = inputs()
    before = deepcopy(args)
    summary, _ = module().build(*args)
    assert args == before
    assert summary["TF"] == pytest.approx(89 / 9)
    assert summary["PE"] == pytest.approx(83.4 / 9)
    assert summary["normal_completions"] == 8
    for old, new in zip(args[0]["cells"], summary["cells"], strict=True):
        if old["task_id"] == 133 and old["stage"] == "middle":
            assert (new["TF"], new["PE"], new["tool_calls"]) == (10, 10, 2)
        else:
            assert (new["TF"], new["PE"], new["cost"]) == (old["TF"], old["PE"], old["cost"])
    assert summary["selection"]["policy"] == "owner_requested_replacement_after_observing_repeat"
    assert not summary["selection"]["balanced_single_attempt_comparison"]


def test_all_spending_includes_superseded_execution_and_update_once():
    summary, _ = module().build(*inputs())
    assert summary["all_api_usd"] == pytest.approx(0.062142145)
    assert summary["task_system_usd"] == pytest.approx(0.050263845)
    assert summary["API_requests"] == 120
    allocation = summary["cost_accounting"]["selected_nine_cell_allocation"]
    assert allocation["all_api_usd"] == pytest.approx(0.056508215)
    assert allocation["task_system_usd"] == pytest.approx(0.045588915)
    assert summary["cost_by_phase"]["updater"]["billed_usd"] == pytest.approx(0.00893751)
    assert summary["cost_accounting"]["superseded_execution_still_paid"]["all_api_usd"] > 0


def test_baselines_stay_unchanged_and_regeneration_is_idempotent():
    args = inputs()
    first, comparison = module().build(*args)
    second, _ = module().build(*args)
    assert first == second
    for key in ("no_update", "full_rewrite"):
        assert comparison[key] == args[2][key]


def test_unverified_repeat_and_missing_case_rejected():
    args = list(inputs())
    args[1]["verification_passed"] = False
    with pytest.raises(ValueError, match="integrity"):
        module().build(*args)
    args = list(inputs())
    args[0]["cells"] = [
        c for c in args[0]["cells"] if not (c["task_id"] == 133 and c["stage"] == "middle")
    ]
    with pytest.raises(ValueError, match="Exactly one"):
        module().build(*args)

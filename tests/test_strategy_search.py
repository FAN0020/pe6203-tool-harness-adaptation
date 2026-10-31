"""Research arms retain their identities, frozen knowledge, and conservative decisions."""

import json
from pathlib import Path

import pytest

from pe6203.benchmark import write_json


def test_search_matrix_uses_real_strategy_ids_and_complete_repeat_blocks():
    from pe6203.strategy_search import cells_for

    spec = json.loads(
        (Path(__file__).resolve().parents[1] / "experiments/selective-search-v1.json").read_text()
    )
    cells = cells_for(spec, "confirmation", "linked_notes")
    assert len(cells) == len({c["id"] for c in cells}) == 108
    assert {c["strategy"] for c in cells} == {
        "no_update",
        "full_rewrite",
        "selective_patch",
        "linked_notes",
    }
    assert [c["seed"] for c in cells] == sorted(c["seed"] for c in cells)


def test_shared_update_is_counted_once_and_new_arms_are_not_mislabeled(tmp_path):
    from pe6203.experiment import summarize

    cells = [
        {"id": f"run{r}", "task_id": 1, "version": "late", "strategy": "linked_notes", "seed": r}
        for r in range(3)
    ]
    write_json(
        tmp_path / "plan.json",
        {
            "cells": cells,
            "shared_adaptations": {"1-late-linked_notes": "adaptations/one/adaptation.json"},
        },
    )
    write_json(
        tmp_path / "adaptations/one/adaptation.json",
        {"status": "validated", "cost": {"total_tokens": 100, "usd": 0.01, "seconds": 2}},
    )
    summary = summarize(tmp_path)
    assert summary["cost"]["update"]["total_tokens"] == 100
    assert summary["cost"]["update"]["usd"] == 0.01
    assert summary["scored"] == 0
    assert {r["strategy"] for r in summary["rows"]} == {"linked_notes"}


def test_sign_flip_does_not_treat_five_judges_as_independent_executions():
    from pe6203.strategy_search import sign_flip

    assert sign_flip([1, 1, 1]) == pytest.approx(1 / 8)
    assert sign_flip([0] * 18) == 1
    assert sign_flip([-1] * 18) == 1


def test_promotion_requires_complete_scoring_and_passes_all_regression_gates():
    from pe6203.strategy_search import promotion

    rows = []
    for task in [133, 235, 283]:
        for stage in ["early", "middle", "late"]:
            for repeat in range(3):
                for arm in ["no_update", "full_rewrite", "selective_patch", "linked_notes"]:
                    rows.append(
                        {
                            "task_id": task,
                            "version": stage,
                            "seed": repeat,
                            "strategy": arm,
                            "TF": 10.0,
                            "PE": 9.0 if arm == "linked_notes" else 8.0,
                            "execution_status": "completed",
                        }
                    )
    spec = {
        "promotion_gate": {
            "delta_PE_vs_champion_min": 0.5,
            "TF_mean_noninferiority_margin": 0.2,
            "ECS_noninferiority_margin": 0.2,
            "max_task_stage_TF_regression": 0.5,
        }
    }
    result = promotion(rows, "linked_notes", spec, 1)
    assert result["promote"] is True and result["post_change_pairs"] == 18
    rows[0]["TF"] = None
    assert promotion(rows, "linked_notes", spec, 1)["promote"] is False
    rows[0]["TF"] = 10.0
    for row in rows:
        if row["strategy"] == "linked_notes" and row["task_id"] == 133 and row["version"] == "late":
            row["TF"] = 9.4
    assert promotion(rows, "linked_notes", spec, 1)["promote"] is False


def test_execution_rejects_unreviewed_or_modified_shared_knowledge(tmp_path):
    from pe6203.experiment import freeze_files
    from pe6203.strategy_search import check_knowledge

    write_json(tmp_path / "adaptations/a/knowledge.json", {"tools": ["frozen"]})
    lock = {"files": freeze_files(tmp_path, [tmp_path / "adaptations/a/knowledge.json"])}
    write_json(tmp_path / "knowledge-lock.json", lock)
    with pytest.raises(ValueError, match="review"):
        check_knowledge(tmp_path)
    from pe6203.experiment import sha

    write_json(
        tmp_path / "knowledge-review.json",
        {
            "accepted": True,
            "lock_sha256": sha(tmp_path / "knowledge-lock.json"),
            "note": "Checked semantic grounding",
        },
    )
    check_knowledge(tmp_path)
    write_json(tmp_path / "adaptations/a/knowledge.json", {"tools": ["mutated"]})
    with pytest.raises(ValueError, match="changed"):
        check_knowledge(tmp_path)


def test_explicit_pairs_do_not_expand_into_cartesian_cells_and_paths_hide_arms():
    from pe6203.strategy_search import cells_for

    spec = {
        "development": {
            "tasks": [133, 235, 283],
            "stages": ["middle", "late"],
            "task_stage_pairs": [[133, "middle"], [283, "late"], [235, "middle"]],
            "strategies": ["selective_patch", "budget_feedback"],
            "repeats": 1,
            "opaque_cell_ids": True,
        }
    }
    cells = cells_for(spec, "development")
    assert len(cells) == len({c["id"] for c in cells}) == 6
    assert {(c["task_id"], c["version"]) for c in cells} == {
        (133, "middle"),
        (283, "late"),
        (235, "middle"),
    }
    assert all(c["id"].startswith("cell-") and c["strategy"] not in c["id"] for c in cells)
    assert cells == cells_for(spec, "development")
    spec["development"]["task_stage_pairs"].append([133, "middle"])
    with pytest.raises(ValueError, match="distinct"):
        cells_for(spec, "development")


def test_budget_contract_rejects_config_that_conflicts_with_its_advertised_limits(tmp_path):
    from pe6203.strategy_search import prepare_search

    spec = {
        "model_config": "config.json",
        "development": {
            "tasks": [133],
            "stages": ["middle"],
            "strategies": ["budget_contract"],
            "repeats": 1,
        },
    }
    write_json(tmp_path / "spec.json", spec)
    write_json(
        tmp_path / "config.json", {"max_rounds": 20, "agent": {"max_completion_tokens": 4096}}
    )
    with pytest.raises(ValueError, match="budget_contract.*12.*4096"):
        prepare_search(tmp_path, tmp_path / "out", "spec.json", "development")
    assert not (tmp_path / "out").exists()


def test_explicit_execution_cells_reuse_prior_results_without_rerunning_them():
    from pe6203.strategy_search import cells_for

    group = {
        "tasks": [133, 235, 283],
        "stages": ["middle", "late"],
        "strategies": ["selective_patch", "budget_feedback"],
        "repeats": 1,
        "opaque_cell_ids": True,
        "execution_cells": [
            [133, "middle", "selective_patch", 0],
            [283, "late", "budget_feedback", 0],
        ],
    }
    cells = cells_for({"development": group}, "development")
    assert len(cells) == 2
    assert {(c["task_id"], c["version"], c["strategy"], c["seed"]) for c in cells} == {
        tuple(c) for c in group["execution_cells"]
    }
    for invalid in [[], [[999, "middle", "selective_patch", 0]], [group["execution_cells"][0]] * 2]:
        with pytest.raises(ValueError, match="distinct supported execution cells"):
            cells_for({"development": {**group, "execution_cells": invalid}}, "development")

"""Cost reporting must count frozen knowledge once and keep unknown charges visible."""

from pe6203.benchmark import write_json


def test_costs_by_arm_deduplicate_updates_and_preserve_unknown_fees(tmp_path):
    from scripts.report_strategy_search import costs_by_arm

    cells = [
        {"id": f"run{r}", "task_id": 1, "version": "late", "strategy": "candidate"}
        for r in range(3)
    ]
    plan = {
        "cells": cells,
        "shared_adaptations": {"1-late-candidate": "adaptations/shared/adaptation.json"},
    }
    write_json(
        tmp_path / "adaptations/shared/adaptation.json",
        {"cost": {"usd": 0.1, "total_tokens": 100, "seconds": 2}},
    )
    for index, charge in enumerate([0.2, None]):
        write_json(
            tmp_path / "cells" / f"run{index}" / "run/result.json",
            {
                "cost": {
                    "agent": {"usd": charge, "known_usd": 0.2, "total_tokens": 200},
                    "judge": {"usd": 0.05, "total_tokens": 50},
                }
            },
        )
    result = costs_by_arm(tmp_path, plan)[0]
    assert result["update"]["usd"] == 0.1
    assert result["update"]["total_tokens"] == 100
    assert result["update"]["seconds"] == 2
    assert result["unique_updates"] == 1
    assert result["recorded_executions"] == 2 and result["planned"] == 3
    assert result["agent"]["usd"] is None
    assert result["agent"]["known_usd"] == 0.4
    assert result["agent"]["unknown_totals"] == 1
    assert result["judge"]["usd"] == 0.1

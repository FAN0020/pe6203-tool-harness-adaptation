"""Compare the historical 29-variant registry with recorded evaluation metadata.

No benchmark, model, updater, or judge calls. Historical conclusions are read only.
"""

import ast
import csv
import json
import subprocess
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
E = ROOT / "results/evidence/unified-reaudit-20261102"
TASK_STAGES = {(task, stage) for task in (133, 235, 283)
               for stage in ("early", "middle", "late")}


def variants(ref):
    source = subprocess.check_output(
        ["git", "show", f"{ref}:src/pe6203/patch_variants.py"], cwd=ROOT, text=True
    )
    tree = ast.parse(source)
    return next(ast.literal_eval(node.value) for node in tree.body
                if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "VARIANTS"
                        for target in node.targets))


def read(path):
    return json.loads(path.read_text())


def main():
    original, audited, current = (
        variants(ref) for ref in ("7314799473", "d6b60d2", "a5551e1")
    )
    assert (len(original), len(audited), len(current)) == (29, 36, 43)
    assert set(original) < set(audited) < set(current)
    maturity = {row["candidate"]: row for row in read(E / "candidate-maturity.json")}
    cells = read(E / "cells.json")
    table = []
    for name in original:
        info = maturity[name]
        executed = [row for row in cells
                    if row["strategy"] == name and row["status"] != "not_started"]
        original_rows = [row for row in executed
                         if row["condition_class"] == "original_benchmark"]
        cohorts = defaultdict(set)
        for row in original_rows:
            cohorts[row["cohort"]].add((row["task_id"], row["stage"]))
        row = {
            "candidate": name,
            "historical_registry_commit": "7314799473",
            "recorded_actor_cells": len(executed),
            "recorded_product_reviews": info["products_reviewed"],
            "original_task_ids": ",".join(map(str, sorted({r["task_id"] for r in original_rows}))),
            "original_changed_cells": info["changed_original"],
            "original_fixed_fixture_cells": info["original_fixed_fixture"],
            "controlled_synthetic_cells": info["controlled_synthetic"],
            "recorded_task223_actor_cells": sum(r["task_id"] == 223 for r in executed),
            "one_cohort_covers_course_3x3": any(TASK_STAGES <= seen for seen in cohorts.values()),
            "evidence_layer": info["layer"],
        }
        assert row["recorded_actor_cells"] == info["executed"]
        table.append(row)
    assert sum(row["recorded_actor_cells"] > 0 for row in table) == 27
    assert sum(row["one_cohort_covers_course_3x3"] for row in table) == 1
    assert not any(row["recorded_task223_actor_cells"] for row in table)
    with (HERE / "29-candidate-screen.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(table[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(table)
    result = {
        "registry_versions": {"historical_29": "7314799473", "audited_36": "d6b60d2",
                              "current_43_at_review": "a5551e1"},
        "counts": {"historical": len(original), "audited": len(audited),
                   "current": len(current), "historical_with_actor": 27,
                   "historical_without_actor": 2,
                   "historical_with_any_task223_actor": 0,
                   "historical_one_cohort_covers_course_3x3": 1},
        "added_after_29_before_36": sorted(set(audited) - set(original)),
        "added_after_36": sorted(set(current) - set(audited)),
        "limits": [
            "The 29 names are one historical registry snapshot, not 29 proven methods.",
            "Execution counts mix distinct task families, fixtures, protocols and cohorts.",
            "A candidate name's absence on task 223 says it was not tested there, not that it cannot work there.",
            "One-cohort coverage of nine course task-stage conditions is not a successful promotion result.",
            "No benchmark question, answer or scored trace was used to generate this index.",
        ],
    }
    (HERE / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result["counts"], ensure_ascii=False))


if __name__ == "__main__":
    main()

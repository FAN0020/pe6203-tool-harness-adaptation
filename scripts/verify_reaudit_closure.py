"""Recompute closed trial evidence and cross-check the published audit, offline."""

import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "results/evidence"
OUT = E / "unified-reaudit-20261102"
TRIALS = [
    "evidence-dictionary-20261102",
    "evidence-contrastive-20261102",
    "capability-consolidation-20261102",
    "relational-probe-memory-20261102",
    "pruned-episode-memory-20261102",
]


def read(path):
    return json.loads(path.read_text())


def main():
    checks = []
    for name in TRIALS:
        script = "verify_trial_with_deviation.py" if name.startswith("relational-") else "verify_trial.py"
        run = subprocess.run(
            [sys.executable, str(E / name / script)],
            cwd=ROOT, capture_output=True, text=True, check=True,
        )
        computed = json.loads(run.stdout)
        assert computed == read(E / name / "trial-verification.json"), name
        assert not computed["development_pass"] and not computed["validation_started"]
        checks.append({
            "evidence": name,
            "saved_verifier_output_reproduced": True,
            "development_pass": False,
            "judge_slots": computed["judge_slots"],
            "rows": len(computed["rows"]),
            "settled_requests": computed["settled_requests"],
            "known_usd": computed["known_usd"],
            "unknown_requests": computed["unknown_requests"],
        })
    inventory = read(OUT / "candidate-inventory.json")
    assert len(inventory) == 36
    assert sum(x["executed_cells"] > 0 for x in inventory) == 33
    assert all(x["executed_cells"] == x["products_reviewed"] for x in inventory)
    maturity = {r["candidate"]: r for r in read(OUT / "candidate-maturity.json")}
    for name in ["artifact_contract", "document_sequence", "prefix_workflow_memory"]:
        assert maturity[name]["layer"] == "original with fixed fixture development/products; retention separate"
    assert not any(r["goal_validated"] for r in maturity.values())
    costs = read(OUT / "total-cost-audit.json")
    receipts = read(OUT / "new-cost-receipts.json")
    assert len(receipts) == len({r["id"] for r in receipts}) == 603
    total = sum((Decimal(r["known_usd"]) for r in receipts), Decimal(0))
    assert total == Decimal(costs["new_known_usd"]) == Decimal("1.094071176")
    assert costs["union_priced_receipts"] == 6163
    assert Decimal(costs["union_known_lower_bound_usd"]) == Decimal("8.3025109865")
    summary = read(OUT / "new-round-summary.json")
    assert Decimal(summary["closed_new_rounds_usd"]) == total
    assert summary["live_or_unclosed_rounds"] == 0
    output = {
        "offline_integrity_pass": True,
        "trials": checks,
        "registered_candidates": 36,
        "candidates_with_actor_and_product_review": 33,
        "new_original_development_cells": sum(x["rows"] for x in checks),
        "new_judge_slots": sum(x["judge_slots"] for x in checks),
        "new_known_usd": str(total),
        "new_unknown_requests": 0,
        "historical_unknowns_preserved": True,
        "goal_complete": False,
        "scope": "Integrity/recomputation only. Does not turn failed development into validation, establish causality, or certify missing iteration rounds.",
    }
    (OUT / "closure-verification.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({k: v for k, v in output.items() if k != "trials"}))


if __name__ == "__main__":
    main()

"""Compile closed new-mechanism rounds; never read live actor scores."""

import csv
import json
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "results/evidence"
OUT = E / "unified-reaudit-20261102"
ROUNDS = [
    ("evidence-dictionary-20261102", "evidence representation", 1),
    ("evidence-contrastive-20261102", "evidence representation", 2),
    ("capability-consolidation-20261102", "capability selection", 1),
    ("relational-probe-memory-20261102", "state-linked episode memory", 1),
    ("pruned-episode-memory-20261102", "state-linked episode memory", 2),
]


def main():
    rounds = []
    rows = []
    total = Decimal(0)
    for name, direction, version in ROUNDS:
        p = E / name
        # No live raw_trace/result/experiment access: only committed/review-frozen verifier output.
        f = p / "trial-verification.json"
        if not f.exists():
            rounds.append(
                dict(
                    evidence=name,
                    direction=direction,
                    mechanism_round=version,
                    status="frozen_in_progress_or_not_closed",
                    development_pass=None,
                )
            )
            continue
        d = json.loads(f.read_text())
        extra = Decimal("0.004804392") if name == "relational-probe-memory-20261102" else Decimal(0)
        cost = Decimal(d["known_usd"]) + extra
        total += cost
        rounds.append(
            dict(
                evidence=name,
                direction=direction,
                mechanism_round=version,
                status="development_evaluated",
                candidate=d["candidate"],
                development_pass=d["development_pass"],
                validation_started=d["validation_started"],
                metrics=d["metrics"],
                gates=d["gates"],
                actor_judge_preflight_usd=d["known_usd"],
                new_updater_usd=str(extra),
                total_new_known_usd=str(cost),
                new_unknown=d["unknown_requests"],
                api_requests=d["api_requests"] + (3 if extra else 0),
                judge_slots=d["judge_slots"],
                product_review_limit=d.get(
                    "review_blinding",
                    "Same coordinator; frozen before arm/score reveal, not independent human review.",
                ),
                source="trial-verification.json",
            )
        )
        for r in d["rows"]:
            rows.append(
                {
                    "round": name,
                    "direction": direction,
                    "mechanism_round": version,
                    **{
                        k: r[k]
                        for k in [
                            "cell_id",
                            "task_id",
                            "stage",
                            "strategy",
                            "execution_status",
                            "core_pass",
                            "TF",
                            "PE",
                            "tool_calls",
                            "tool_errors",
                            "review_id",
                        ]
                    },
                }
            )
    (OUT / "new-mechanism-rounds.json").write_text(
        json.dumps(rounds, ensure_ascii=False, indent=2) + "\n"
    )
    with (OUT / "new-mechanism-cells.csv").open("w") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    historical = json.loads((OUT / "cost-audit.json").read_text())["deduplicated_union"][
        "known_usd"
    ]
    summary = {
        "historical_known_lower_bound_usd": historical,
        "closed_new_rounds_usd": str(total),
        "combined_known_lower_bound_usd": str(Decimal(historical) + total),
        "live_round_cost_included": False,
        "live_or_unclosed_rounds": sum(r["development_pass"] is None for r in rounds),
        "historical_unknowns_preserved": True,
        "goal_complete": False,
        "direction_status": [
            {
                "direction": direction,
                "closed_rounds": sum(
                    r["direction"] == direction and r["development_pass"] is not None
                    for r in rounds
                ),
                "planned_rounds": sum(r["direction"] == direction for r in rounds),
            }
            for direction in dict.fromkeys(r["direction"] for r in rounds)
        ],
        "remaining_user_requirements": [
            "No independently validated dual-improvement winner yet.",
            "Capability-selection direction has only one completed new version; a second must have a distinct supported mechanism, not merely restore wording or sample again.",
            "Two independent validation blocks required only after strict development pass; no version promoted by development or synthetic success alone.",
            "Additional course E/M/L NU/FR/SP only after a true validated candidate; no slide/script edits.",
        ],
    }
    (OUT / "new-round-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "closed_rounds": len([r for r in rounds if r["development_pass"] is not None]),
                "original_development_rows": len(rows),
                "known_new_cost": str(total),
            }
        )
    )


if __name__ == "__main__":
    main()

"""Executable oracle checks and strict property/gate aggregation.

Semantic and rendered-page judgments require recorded human/model-coordinator
review; this program validates their completeness, not independent correctness.
"""
import argparse
import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from pe6203.experience_projection import PROPERTIES, training_gate

BASE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reviews", type=Path)
    args = parser.parse_args()
    for name, expected in json.loads((BASE / "data-manifest.json").read_text()).items():
        assert hashlib.sha256((BASE / name).read_bytes()).hexdigest() == expected
    for task_id in (900201, 900202):
        oracle = json.loads((BASE / f"evaluation/oracle-{task_id}.json").read_text())
        for row in oracle["rows"]:
            rate = (Decimal(row["successful"]) / row["trials"] * 100).quantize(Decimal(".1"), rounding=ROUND_HALF_UP)
            cost = Decimal(row["usd_per_query"]) * oracle["monthly_volume"]
            assert rate == Decimal(row["success_percent"])
            assert cost == Decimal(row["monthly_usd"])
            assert row["feasible"] == (row["p95_ms"] <= oracle["latency_limit"] and cost <= oracle["budget"])
        assert oracle["recommendation"] == max((r for r in oracle["rows"] if r["feasible"]), key=lambda r: Decimal(r["successful"]) / r["trials"])["method"]
    result = {"data_and_oracles_verified": True}
    if args.reviews:
        rows = json.loads(args.reviews.read_text())
        for row in rows:
            assert set(row["properties"]) == PROPERTIES
            assert set(row["properties"].values()) <= {"pass", "fail", "unknown"}
            assert row["core_pass"] == all(v == "pass" for v in row["properties"].values())
            assert row["artifact_modified"] is False and row["official_scores_revealed"] is False
        result["signal_gate"] = training_gate(rows)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

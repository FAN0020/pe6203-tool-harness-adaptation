"""Generate local synthetic integration records using the real baselines.

Run from the project root: python -m integration.run_baseline_validation
"""

import argparse
import hashlib
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

from fixtures.baseline_cases import all_cases
from integration import baselines
from integration.baseline_wrapper import run_baseline_once, save_run_record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="outputs/baseline_integration_validation.json")
    parser.add_argument("--allow-metadata-api", action="store_true")
    args = parser.parse_args()
    if not args.allow_metadata_api:
        parser.error(
            "Six paid updater calls require --allow-metadata-api; use pytest for free tests"
        )
    if Path(args.output).exists():
        parser.error("Output exists; choose a new --output path to preserve previous evidence")
    records = []
    for case in all_cases():
        old_knowledge = baselines.build_knowledge(case["old_metadata"])
        for strategy in ("no_update", "full_rewrite"):
            record = run_baseline_once(
                adapt_fn=baselines.adapt,
                old_knowledge=deepcopy(old_knowledge),
                raw_new_metadata=deepcopy(case["new_metadata"]),
                strategy=strategy,
                context={
                    "updater": {"allow_metadata_api": True},
                    "audit_path": str(
                        Path(args.output).with_suffix("") / case["name"] / f"{strategy}.json"
                    ),
                },
            )
            records.append(
                {
                    "case": case["name"],
                    "old_metadata": case["old_metadata"],
                    "new_metadata": case["new_metadata"],
                    "old_knowledge": old_knowledge,
                    **record,
                }
            )
    module_path = Path(baselines.__file__)
    save_run_record(
        {
            "validation_type": "synthetic_integration_run",
            "created_at_utc": datetime.now(UTC).isoformat(),
            "baseline_source_sha256": hashlib.sha256(module_path.read_bytes()).hexdigest(),
            "benchmark_integrated": False,
            "official_metrics": {"TF": None, "PE": None, "ECS": None},
            "record_count": len(records),
            "records": records,
        },
        args.output,
    )
    print(f"Saved {len(records)} synthetic update records to {args.output}")
    print("Run pytest for behavioral checks; benchmark metrics are not evaluated.")


if __name__ == "__main__":
    main()

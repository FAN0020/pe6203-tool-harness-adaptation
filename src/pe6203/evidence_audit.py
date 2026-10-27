"""Audit explicitly selected historical evidence without promoting it to formal results.

Run with --manifest experiments/evaluation/pilot-evidence.json --output NEW_DIR.
All inputs are hash-checked. No model calls, network access or score replacement.
"""

import argparse
import copy
import json
import math
import statistics
from pathlib import Path

from .evaluation import SCORES, digest, judge_scores, number, read, write_outputs


def token_count(cost):
    """Support both historical tokens and current total_tokens fields."""
    values = [cost[k] for k in ("tokens", "total_tokens") if cost.get(k) is not None]
    if any(not number(x) for x in values) or len(set(values)) > 1:
        raise ValueError("Invalid or conflicting token fields")
    return values[0] if values else None


def score_run(result, evaluation):
    if result.get("status") != "evaluated" or result.get("judge_status") != "complete":
        return None, "runner_or_judge_incomplete"
    if evaluation.get("idx") != result.get("task_id"):
        raise ValueError("EVAL task ID disagrees with result")
    scores, reason = judge_scores(evaluation)
    if reason:
        return None, reason
    if any(
        not number(result.get(k), 1, 10) or not math.isclose(result[k], scores[k], abs_tol=1e-8)
        for k in ("TF", "PE")
    ):
        return None, "result_and_eval_scores_disagree"
    return scores, None


def bundle_evaluation(bundle):
    """Some published bundles retain judge responses but omit EVAL aggregates."""
    runs = bundle.get("judge_runs", [])
    aggregate = bundle.get("aggregate")
    source = "published_aggregate"
    if aggregate is None:
        source = "recomputed_from_preserved_judge_records"
        valid = [
            x["result"]
            for x in runs
            if isinstance(x, dict)
            and isinstance(x.get("result"), dict)
            and all(type(x["result"].get(k)) is int and 1 <= x["result"][k] <= 10 for k in SCORES)
        ]
        aggregate = {
            "successful_runs": len(valid),
            "total_runs": len(runs),
            "complete": len(valid) == len(runs) == 5,
        }
        aggregate.update(
            {k + "_mean": statistics.mean(x[k] for x in valid) if valid else None for k in SCORES}
        )
    return {
        "idx": bundle["result"]["task_id"],
        "eval_result": {"runs": runs, "aggregate": aggregate},
    }, source


def inspect_entry(entry, base):
    sources = []

    def load(field):
        path = base / entry[field]
        actual = digest(path)
        if actual != entry.get(field + "_sha256"):
            raise ValueError("Evidence hash mismatch: " + entry[field])
        sources.append({"path": entry[field], "sha256": actual})
        return read(path)

    payload = load("path")
    kind = entry["format"]
    evaluation, aggregate_source = None, None
    bundle = {}
    if kind == "bundle":
        bundle = payload
        result = payload["result"]
        evaluation, aggregate_source = bundle_evaluation(bundle)
    elif kind == "result_eval":
        result = payload
        evaluation = load("eval_path")
        aggregate_source = "published_aggregate"
    elif kind == "summary_row":
        matches = [r for r in payload["runs"] if r["strategy"] == entry["strategy"]]
        if len(matches) != 1:
            raise ValueError("Summary strategy does not identify one row")
        result = copy.deepcopy(matches[0])
        result.update(task_id=payload["task_id"], version=payload["environment_version"])
        # Summary rows lack per-call evidence; no synthetic raw record is created.
        result["cost"] = {
            "agent": {"total_tokens": result.get("agent_total_tokens")},
            "judge": {"total_tokens": result.get("judge_total_tokens")},
            "update": {
                "tokens": result.get("update_tokens"),
                "seconds": result.get("update_seconds"),
                "usd": result.get("update_usd"),
            },
        }
    elif kind == "result_summary":
        result = payload
    else:
        raise ValueError("Unknown evidence format")
    scores, reason = score_run(result, evaluation) if evaluation else (None, "summary_only")
    row = {
        "evidence_id": entry["evidence_id"],
        "comparison_group": entry["comparison_group"],
        "task_id": result["task_id"],
        "stage": result["version"],
        "strategy": result["strategy"],
        "repeat_id": result.get("seed"),
        "execution_status": result.get("execution_status"),
        "judge_status": result.get("judge_status"),
        "reported_TF": result.get("TF"),
        "reported_PE": result.get("PE"),
        "verified_TF": scores["TF"] if scores else None,
        "verified_PE": scores["PE"] if scores else None,
        "judge_TF_sd": scores["judge_TF_sd"] if scores else None,
        "judge_PE_sd": scores["judge_PE_sd"] if scores else None,
        "score_check": "verified" if scores else reason,
        "aggregate_source": aggregate_source,
        "ECS": None,
        "formal_eligible": False,
        "formal_exclusion": entry["formal_exclusion"],
        "protocol_sha256": result.get("protocol_sha256"),
        "source_path": entry["path"],
    }
    costs = result.get("cost", {})
    if not costs and "usage_tokens" in result:
        costs = {**result["usage_tokens"], "update": result.get("update_cost_reported", {})}
    cost_rows = []
    for role in ("update", "agent", "judge"):
        cost = costs.get(role) or {}
        cost_rows.append(
            {
                "evidence_id": entry["evidence_id"],
                "role": role,
                "tokens": token_count(cost),
                "seconds": cost.get("seconds"),
                "usd": cost.get("usd"),
                "source_path": entry["path"],
                "scope": "recorded_run_cost; not independently reaggregated per-call usage",
            }
        )
    judges = []
    if evaluation:
        for i, run in enumerate(evaluation["eval_result"]["runs"], 1):
            record = run.get("result") or {}
            judges.append(
                {
                    "evidence_id": entry["evidence_id"],
                    "judge_attempt": i,
                    "TF": record.get(SCORES[0]),
                    "PE": record.get(SCORES[1]),
                    "grounding": record.get(SCORES[2]),
                    "error": run.get("error", record.get("error")),
                    "raw_response_available": "response" in run,
                }
            )
    failures = []
    for i, event in enumerate(bundle.get("tool_results", bundle.get("tool_errors", []))):
        if event.get("result", {}).get("isError") or event.get("error"):
            function = event.get("call", {}).get("function", event)
            failures.append(
                {
                    "evidence_id": entry["evidence_id"],
                    "round": event.get("round"),
                    "tool": function.get("name"),
                    "arguments": function.get("arguments"),
                    "source_path": entry["path"],
                    "event_index": i,
                    "classification": "unattributed_tool_error",
                    "under_or_over_update_confirmed": False,
                }
            )
    return row, cost_rows, judges, failures, sources


def audit(manifest, base):
    if manifest.get("evidence_kind") != "historical_development_audit":
        raise ValueError("This command is only for historical development evidence")
    rows, costs, judges, failures, sources = [], [], [], [], []
    seen = set()
    for entry in manifest["entries"]:
        if entry["evidence_id"] in seen:
            raise ValueError("Duplicate evidence ID")
        seen.add(entry["evidence_id"])
        row, c, j, f, s = inspect_entry(entry, base)
        rows.append(row)
        costs.extend(c)
        judges.extend(j)
        failures.extend(f)
        sources.extend(s)
    return {
        "evidence_kind": manifest["evidence_kind"],
        "source_commit": manifest["source_commit"],
        "new_model_calls": 0,
        "formal_three_strategy_results_available": False,
        "runs": rows,
        "recorded_costs": costs,
        "judge_attempts": judges,
        "unattributed_tool_errors": failures,
        "sources": sources,
        "limitations": [
            "Development evidence only; no strategy ranking or ECS.",
            "Different comparison groups must not be pooled.",
            "Five judge attempts are not five agent repetitions.",
            "Human judge validation and causal failure attribution remain pending.",
            "No project-wide cost total: shared update identities are not established.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    path = Path(args.manifest).resolve()
    manifest = read(path)
    output = audit(manifest, path.parent / manifest["source_root"])
    output["manifest_sha256"] = digest(path)
    write_outputs(args.output, output)
    print(
        json.dumps(
            {
                "runs": len(output["runs"]),
                "new_model_calls": 0,
                "verified_score_records": sum(
                    x["score_check"] == "verified" for x in output["runs"]
                ),
            }
        )
    )


if __name__ == "__main__":
    main()

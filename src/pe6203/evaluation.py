"""Offline PE6203 evaluation. Python 3.10+, standard library only.

Consumes a D-side analysis manifest and explicit run ledger. It does not launch
models, alter benchmark labels, infer experiment identities, or fabricate scores.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import re
import statistics as stats
from pathlib import Path

STAGES = ("early", "middle", "late")
STRATEGIES = ("no_update", "full_rewrite", "selective_patch")
SCORES = ("task_fulfillment", "planning_and_efficiency", "grounding")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def number(x, low=0, high=float("inf")):
    return type(x) in (int, float) and math.isfinite(x) and low <= x <= high


def mean(xs):
    return stats.mean(xs) if xs else None


def ecs(values, sample=False):
    if len(values) != 3 or not all(number(v, 1, 10) for v in values):
        raise ValueError("ECS requires three valid, unrounded TF scores")
    return stats.mean(values) - (stats.stdev(values) if sample else stats.pstdev(values))


def judge_scores(payload):
    """Recompute from all five raw judge records; never trust rounded means."""
    if not isinstance(payload, dict):
        return None, "invalid_eval_object"
    packed = payload.get("eval_result", {})
    if not isinstance(packed, dict):
        return None, "invalid_eval_result"
    runs = packed.get("runs", [])
    if not isinstance(runs, list) or len(runs) != 5:
        return None, "judge_attempt_count_not_five"
    if any(not isinstance(x, dict) or not isinstance(x.get("result"), dict) for x in runs):
        return None, "invalid_judge_record"
    rows = [x.get("result", {}) for x in runs]
    if any(run.get("error") is not None for run in runs):
        return None, "judge_record_contains_error"
    if packed.get("protocol") == "durable-slots-v1":
        attempts = packed.get("attempts")
        if not isinstance(attempts, list) or not 5 <= len(attempts) <= 10:
            return None, "invalid_judge_attempt_audit"
        if any(
            not isinstance(a, dict) or type(a.get("slot")) is not int or not 1 <= a["slot"] <= 5
            for a in attempts
        ):
            return None, "invalid_judge_slot"
        for slot, selected in enumerate(runs, 1):
            history = [a for a in attempts if a["slot"] == slot]
            if (
                not history
                or len(history) > 2
                or [a.get("attempt") for a in history] != list(range(1, len(history) + 1))
            ):
                return None, "invalid_judge_attempt_sequence"
            first = next(
                (a for a in history if a.get("result") is not None and not a.get("error")), None
            )
            if first != selected:
                return None, "judge_did_not_select_first_valid_attempt"
    if any(
        "error" in x or any(type(x.get(k)) is not int or not 1 <= x[k] <= 10 for k in SCORES)
        for x in rows
    ):
        return None, "invalid_judge_score_or_error"
    for run in runs:
        if "response" not in run:
            continue
        try:
            raw = run["response"]["choices"][0]["message"]["content"]
            parsed = json.loads(re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip()))
            if any(type(parsed[k]) is not int or parsed[k] != run["result"][k] for k in SCORES):
                return None, "raw_judge_response_mismatch"
        except (KeyError, IndexError, TypeError, AttributeError, ValueError):
            return None, "invalid_raw_judge_response"
    agg = packed.get("aggregate", {})
    if not isinstance(agg, dict):
        return None, "invalid_judge_aggregate"
    if agg.get("successful_runs") != 5 or agg.get("total_runs") != 5:
        return None, "judge_count_mismatch"
    if agg.get("complete", True) is not True:
        return None, "judge_marked_incomplete"
    values = {k: stats.mean(x[k] for x in rows) for k in SCORES}
    for k, v in values.items():
        a = agg.get(k + "_mean")
        if not number(a, 1, 10) or not math.isclose(a, v, abs_tol=1e-8):
            return None, "judge_aggregate_mismatch:" + k
    return {
        "TF": values[SCORES[0]],
        "PE": values[SCORES[1]],
        "grounding": values[SCORES[2]],
        "judge_TF_sd": stats.stdev(x[SCORES[0]] for x in rows),
        "judge_PE_sd": stats.stdev(x[SCORES[1]] for x in rows),
    }, None


def weighted(rows, key):
    """Equal tasks, averaging available matched repeats within each task."""
    groups = {}
    for row in rows:
        groups.setdefault(row["task_id"], []).append(row[key])
    return mean([stats.mean(v) for v in groups.values()])


def validate_manifest(m, demo=False):
    if demo:
        if m.get("evidence_kind") != "synthetic_software_test":
            raise ValueError("--demo accepts synthetic_software_test only")
    elif m.get("frozen") is not True or m.get("evidence_kind") != "real_model_evaluation":
        raise ValueError("Formal analysis requires a frozen real_model_evaluation manifest")
    if not m.get("experiment_id") or not m.get("comparison_config_file_sha256"):
        raise ValueError("Missing experiment identity or frozen comparison configuration hash")
    tasks = m.get("tasks", [])
    ids = [t["task_id"] for t in tasks]
    reserved = {139, 223} | set(m.get("development_reserved_ids", []))
    if not ids or len(ids) != len(set(ids)) or reserved.intersection(ids):
        raise ValueError("Need distinct evaluation tasks; development tasks are excluded")
    if any(type(i) is not int for i in ids):
        raise ValueError("Task IDs must be integers")
    repeats = m.get("repeat_ids", [])
    if not repeats or len(repeats) != len(set(repeats)) or any(type(r) is not int for r in repeats):
        raise ValueError("Need distinct integer repeat IDs")
    for t in tasks:
        if not demo and not t.get("review_evidence"):
            raise ValueError("Each task needs review evidence")
        for v in STAGES[1:]:
            x = t.get("transitions", {}).get(v, {})
            if x.get("label") not in ("changed", "unaffected", "uncertain"):
                raise ValueError("Missing transition label")
            if not set(x.get("change_types", [])).issubset({"TOOL", "PARAM", "DESC"}):
                raise ValueError("Unknown change type")
    return ids, repeats


def checked_file(base, entry, field):
    p = (base / entry[field]).resolve()
    expected = entry.get(field + "_sha256")
    if not expected or digest(p) != expected:
        raise ValueError("Missing or mismatched byte hash for " + field)
    return p


def load_runs(manifest, ledger, base):
    ids, repeats = [t["task_id"] for t in manifest["tasks"]], manifest["repeat_ids"]
    expected = set(itertools.product(ids, STAGES, STRATEGIES, repeats))
    selected, attempts, seen = {}, [], set()
    for entry in ledger.get("runs", []):
        key = (entry["task_id"], entry["stage"], entry["strategy"], entry["repeat_id"])
        attempt_key = key + (entry["attempt_id"],)
        if key not in expected or attempt_key in seen:
            raise ValueError("Unexpected or duplicate run identity: " + repr(attempt_key))
        seen.add(attempt_key)
        if entry.get("experiment_id") != manifest["experiment_id"]:
            raise ValueError("Mixed experiment IDs")
        if entry.get("comparison_config_file_sha256") != manifest["comparison_config_file_sha256"]:
            raise ValueError("Mixed comparison configuration")
        if type(entry.get("selected_for_analysis")) is not bool:
            raise ValueError("Every attempt needs explicit selected_for_analysis")
        if entry.get("attempt_id") != 0 and not entry.get("retry_evidence"):
            raise ValueError("Additional attempts need an audited retry reason")
        p = checked_file(base, entry, "result_path")
        result = read(p)
        identity = (
            result.get("task_id"),
            result.get("version"),
            result.get("strategy"),
            result.get("seed"),
        )
        if identity != key:
            raise ValueError("Result identity disagrees with ledger")
        if (
            not entry.get("expected_config_sha256")
            or result.get("config_sha256") != entry["expected_config_sha256"]
        ):
            raise ValueError("Runner config mismatch")
        if (
            manifest.get("evidence_kind") == "real_model_evaluation"
            and result.get("status") == "evaluated"
            and result.get("judge_status") == "complete"
        ):
            validate_formal_result(result, manifest)
        # Per-cell config hashes are audited against the common comparison config;
        # output locations / knowledge references may legitimately differ.
        row = dict(
            task_id=key[0],
            stage=key[1],
            strategy=key[2],
            repeat_id=key[3],
            attempt_id=entry["attempt_id"],
            result_path=entry["result_path"],
            runner_status=result.get("status"),
            execution_status=result.get("execution_status"),
            TF=None,
            PE=None,
            eligible=False,
            reason=None,
            cost=result.get("cost", {}),
            protocol_sha256=result.get("protocol_sha256"),
        )
        if result.get("status") != "evaluated" or result.get("judge_status") != "complete":
            row["reason"] = "runner_or_judge_incomplete"
        else:
            ep = checked_file(base, entry, "eval_path")
            evaluation = read(ep)
            if evaluation.get("idx") != key[0]:
                raise ValueError("EVAL task ID disagrees with ledger")
            score, reason = judge_scores(evaluation)
            if reason:
                row["reason"] = reason
            elif any(
                not number(result.get(k), 1, 10)
                or not math.isclose(result[k], score[k], abs_tol=1e-8)
                for k in ("TF", "PE")
            ):
                row["reason"] = "result_and_eval_scores_disagree"
            else:
                row.update(score, eligible=True)
        if row["runner_status"] not in ("evaluated", "judge_incomplete", "blocked", "timeout"):
            raise ValueError("Unrecognised runner status")
        row["selected_for_analysis"] = entry["selected_for_analysis"]
        row["adaptation_artifact_id"] = entry.get("adaptation_artifact_id")
        attempts.append(row)
        if entry["selected_for_analysis"]:
            if key in selected:
                raise ValueError("Multiple selected attempts; best-score selection is forbidden")
            selected[key] = row
    for t, v, r in itertools.product(ids, STAGES, repeats):
        hashes = {
            selected[t, v, s, r]["protocol_sha256"]
            for s in STRATEGIES
            if (t, v, s, r) in selected and selected[t, v, s, r]["eligible"]
        }
        if len(hashes) > 1:
            raise ValueError("Mixed runner protocols in one comparison cell")
    return expected, selected, attempts


def validate_formal_result(result, manifest):
    """Reject smoke runs and require provenance before allowing formal tables."""
    config = result.get("config", {})
    if config.get("pilot_only") or result.get("strategy") not in STRATEGIES:
        raise ValueError("Pilot/smoke records cannot enter formal analysis")
    for key in ("benchmark_commit", "dataset_revision"):
        if not manifest.get(key) or result.get(key) != manifest[key]:
            raise ValueError("Missing or mismatched " + key)
    if not result.get("protocol_sha256"):
        raise ValueError("Formal results require recorded runner protocol hashes")
    if not config:
        raise ValueError("Formal results require the actual execution config")
    actual = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    if actual != result.get("config_sha256"):
        raise ValueError("Config bytes cannot reproduce runner digest; use original formal logs")


def check_comparison_config(manifest, base):
    """Hash the reviewed configuration, rather than accepting an arbitrary label."""
    path = manifest.get("comparison_config_path")
    if not path or digest(base / path) != manifest["comparison_config_file_sha256"]:
        raise ValueError("Missing or mismatched comparison config file")


def summarize(m, selected, attempts):
    ids = [t["task_id"] for t in m["tasks"]]
    repeats = m["repeat_ids"]
    tasks = {t["task_id"]: t for t in m["tasks"]}

    def complete(t, v, r):
        return all(selected.get((t, v, s, r), {}).get("eligible") for s in STRATEGIES)

    cells, exclusions, main, triplets, transitions, failures = [], [], [], [], [], []
    for t, v, s, r in itertools.product(ids, STAGES, STRATEGIES, repeats):
        row = selected.get((t, v, s, r))
        cells.append(
            {
                "task_id": t,
                "stage": v,
                "strategy": s,
                "repeat_id": r,
                "TF": row["TF"] if row else None,
                "PE": row["PE"] if row else None,
                "eligible": bool(row and row["eligible"]),
                "matched": complete(t, v, r),
                "reason": row["reason"] if row else "no_selected_result",
            }
        )
        if not complete(t, v, r):
            exclusions.append(
                {
                    "task_id": t,
                    "stage": v,
                    "strategy": s,
                    "repeat_id": r,
                    "reason": (row["reason"] or "another_strategy_incomplete")
                    if row
                    else "no_selected_result",
                }
            )
    for v, s in itertools.product(STAGES, STRATEGIES):
        rows = [x for x in cells if x["stage"] == v and x["strategy"] == s and x["matched"]]
        main.append(
            {
                "stage": v,
                "strategy": s,
                "TF": weighted(rows, "TF"),
                "PE": weighted(rows, "PE"),
                "matched_tasks": len({x["task_id"] for x in rows}),
                "matched_cells": len(rows),
                "planned_cells": len(ids) * len(repeats),
            }
        )
    for t, r in itertools.product(ids, repeats):
        if not all(complete(t, v, r) for v in STAGES):
            continue
        for s in STRATEGIES:
            values = [selected[t, v, s, r]["TF"] for v in STAGES]
            triplets.append(
                {
                    "task_id": t,
                    "repeat_id": r,
                    "strategy": s,
                    "early_TF": values[0],
                    "middle_TF": values[1],
                    "late_TF": values[2],
                    "upstream_population": ecs(values),
                    "paper_sample": ecs(values, True),
                }
            )
    ecs_table = [
        {
            "strategy": s,
            "upstream_population": weighted(
                [x for x in triplets if x["strategy"] == s], "upstream_population"
            ),
            "paper_sample": weighted([x for x in triplets if x["strategy"] == s], "paper_sample"),
            "matched_triplets": len([x for x in triplets if x["strategy"] == s]),
            "planned_triplets": len(ids) * len(repeats),
        }
        for s in STRATEGIES
    ]
    for v, s, label in itertools.product(STAGES[1:], STRATEGIES, ("changed", "unaffected")):
        rows, early_rows = [], []
        for t, r in itertools.product(ids, repeats):
            if tasks[t]["transitions"][v]["label"] != label or not complete(t, v, r):
                continue
            value = selected[t, v, s, r]["TF"]
            rows.append({"task_id": t, "delta": value - selected[t, v, "no_update", r]["TF"]})
            if complete(t, "early", r):
                early_rows.append(
                    {"task_id": t, "delta": value - selected[t, "early", "no_update", r]["TF"]}
                )
        transitions.append(
            {
                "stage": v,
                "strategy": s,
                "subgroup": label,
                "delta_vs_no_update_same_stage": weighted(rows, "delta"),
                "matched_cells": len(rows),
                "matched_tasks": len({x["task_id"] for x in rows}),
                "delta_vs_no_update_early": weighted(early_rows, "delta")
                if label == "unaffected"
                else None,
                "early_matched_cells": len(early_rows) if label == "unaffected" else 0,
            }
        )
    for s in STRATEGIES:
        rows = [x for x in cells if x["strategy"] == s]
        observed = [x for x in attempts if x["strategy"] == s]
        failures.append(
            {
                "strategy": s,
                "planned_cells": len(rows),
                "attempts": len(observed),
                "eligible_selected_cells": sum(x["eligible"] for x in rows),
                "missing_selected_cells": sum(x["reason"] == "no_selected_result" for x in rows),
                "noneligible_cell_fraction": sum(not x["eligible"] for x in rows) / len(rows),
                "attempt_execution_failures": sum(
                    x["execution_status"]
                    in (
                        "failed",
                        "max_rounds",
                        "empty_answer",
                        "output_truncated",
                        "content_filtered",
                    )
                    for x in observed
                ),
                "attempt_not_started": sum(
                    x["execution_status"] == "not_started" for x in observed
                ),
            }
        )
    breakdown = []
    for v, s, change in itertools.product(STAGES[1:], STRATEGIES, ("TOOL", "PARAM", "DESC")):
        rows = [
            x
            for x in cells
            if x["stage"] == v
            and x["strategy"] == s
            and x["matched"]
            and tasks[x["task_id"]]["transitions"][v]["label"] == "changed"
            and change in tasks[x["task_id"]]["transitions"][v]["change_types"]
        ]
        breakdown.append(
            {
                "stage": v,
                "strategy": s,
                "change_type": change,
                "TF": weighted(rows, "TF"),
                "PE": weighted(rows, "PE"),
                "matched_tasks": len({x["task_id"] for x in rows}),
                "matched_cells": len(rows),
            }
        )
    task_results = []
    for t, v, s in itertools.product(ids, STAGES, STRATEGIES):
        rows = [
            x
            for x in cells
            if x["task_id"] == t and x["stage"] == v and x["strategy"] == s and x["matched"]
        ]
        task_results.append(
            {
                "task_id": t,
                "stage": v,
                "strategy": s,
                "matched_repeats": len(rows),
                "TF": mean([x["TF"] for x in rows]),
                "PE": mean([x["PE"] for x in rows]),
                "TF_repeat_sd": stats.stdev(x["TF"] for x in rows) if len(rows) > 1 else None,
                "PE_repeat_sd": stats.stdev(x["PE"] for x in rows) if len(rows) > 1 else None,
            }
        )
    return dict(
        main_results=main,
        ecs=ecs_table,
        ecs_triplets=triplets,
        recovery_retention=transitions,
        change_type_results=breakdown,
        task_results=task_results,
        cells=cells,
        exclusions=exclusions,
        completeness=failures,
    )


def update_costs(ledger, attempts):
    """Sum unique artifacts, including failed updates; do not impute unknowns."""
    unique = {}
    for item in ledger.get("updates", []):
        aid = item.get("artifact_id")
        if not aid or item.get("strategy") not in STRATEGIES:
            raise ValueError("Update artifact needs identity and strategy")
        if aid in unique and unique[aid] != item:
            raise ValueError("Conflicting cost records for one update artifact")
        for unit in ("tokens", "seconds", "usd"):
            if item.get(unit) is not None and not number(item[unit]):
                raise ValueError("Invalid update cost")
        if item.get("usd") is not None and item.get("usd") != 0 and not item.get("price_source"):
            raise ValueError("USD cost needs pricing or invoice evidence")
        if item["strategy"] == "no_update" and any(
            item.get(k) != 0 for k in ("tokens", "seconds", "usd")
        ):
            raise ValueError("No Update must explicitly record zero adaptation cost")
        unique[aid] = item
    for row in attempts:
        aid = row["adaptation_artifact_id"]
        if row["stage"] != "early" and (
            aid not in unique or unique[aid]["strategy"] != row["strategy"]
        ):
            raise ValueError("Missing or mismatched update artifact")
    table = []
    for s in STRATEGIES:
        rows = [x for x in unique.values() if x["strategy"] == s]
        out = {"strategy": s, "unique_artifacts": len(rows)}
        for unit in ("tokens", "seconds", "usd"):
            known = [x[unit] for x in rows if x.get(unit) is not None]
            out[unit + "_known_sum"] = sum(known) if known else None
            out[unit + "_missing_artifacts"] = len(rows) - len(known)
            out[unit + "_total"] = sum(known) if rows and len(known) == len(rows) else None
        table.append(out)
    return table


def execution_costs(attempts):
    """All agent/judge attempts count, including failed and unselected attempts."""
    table = []
    for strategy, role in itertools.product(STRATEGIES, ("agent", "judge")):
        rows = [x.get("cost", {}).get(role) or {} for x in attempts if x["strategy"] == strategy]
        out = {"strategy": strategy, "role": role, "attempts": len(rows)}
        for unit in ("total_tokens", "seconds", "usd"):
            values = [x.get(unit) for x in rows]
            if any(v is not None and not number(v) for v in values):
                raise ValueError("Invalid execution cost: " + unit)
            known = [v for v in values if v is not None]
            out[unit + "_known_sum"] = sum(known) if known else None
            out[unit + "_missing_attempts"] = len(values) - len(known)
            out[unit + "_total"] = sum(known) if rows and len(known) == len(rows) else None
        table.append(out)
    return table


def write_outputs(out, result):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    (out / "summary.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    )
    for name, rows in result.items():
        if isinstance(rows, list) and rows and isinstance(rows[0], dict):
            with (out / (name + ".csv")).open("w", newline="", encoding="utf-8-sig") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", required=True)
    p.add_argument("--ledger", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--demo", action="store_true", help="Synthetic software checks only")
    args = p.parse_args()
    m, ledger = read(args.manifest), read(args.ledger)
    validate_manifest(m, args.demo)
    if not args.demo:
        check_comparison_config(m, Path(args.manifest).resolve().parent)
    expected, selected, attempts = load_runs(m, ledger, Path(args.ledger).resolve().parent)
    result = summarize(m, selected, attempts)
    result["update_cost"] = update_costs(ledger, attempts)
    result["execution_cost"] = execution_costs(attempts)
    result["evidence_kind"] = m["evidence_kind"]
    result["experiment_id"] = m["experiment_id"]
    result["planned_cells"] = len(expected)
    result["manifest_sha256"] = digest(args.manifest)
    result["ledger_sha256"] = digest(args.ledger)
    result["all_attempt_cost_records"] = [
        {
            "task_id": x["task_id"],
            "stage": x["stage"],
            "strategy": x["strategy"],
            "repeat_id": x["repeat_id"],
            "attempt_id": x["attempt_id"],
            "cost": x["cost"],
        }
        for x in attempts
    ]
    write_outputs(args.output, result)
    print(
        json.dumps(
            {
                "evidence_kind": result["evidence_kind"],
                "planned_cells": len(expected),
                "eligible_selected": sum(r["eligible"] for r in selected.values()),
                "output": args.output,
            }
        )
    )


if __name__ == "__main__":
    main()

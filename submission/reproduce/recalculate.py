"""Recalculate archived PE6203 evidence with Python's standard library only.

No repository imports, extraction, networking, model calls or historical writes.
Usage: python3 recalculate.py [--archive main-raw.tar.gz] [--output derived-dir]
"""

import argparse
import csv
import hashlib
import io
import itertools
import json
import math
import statistics
import tarfile
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

ARCHIVE_SHA = "e95e15694abe9a12e37c813f81e6e0fb0b5ccd00c2003f2a25a36a092c8001c9"
PREFIX = "course-v1.3-final-20261031/"
STAGES = ["early", "middle", "late"]
METHODS = ["no_update", "full_rewrite", "selective_patch"]
TASKS = [133, 235, 283]


def close(actual, expected):
    assert math.isclose(actual, expected, abs_tol=1e-10), (actual, expected)


def aggregate_usage(usages):
    totals = {
        k: sum((u or {}).get(k) or 0 for u in usages)
        for k in ["prompt_tokens", "completion_tokens", "total_tokens"]
    }
    totals.update(
        known_usd=sum((u or {}).get("cost") or 0 for u in usages),
        unknown_requests=sum(u is None or u.get("cost") is None for u in usages),
        requests=len(usages),
    )
    return totals


def audit(archive):
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    assert digest == ARCHIVE_SHA, "Archive differs from frozen main evidence"
    with tarfile.open(fileobj=io.BytesIO(archive.read_bytes())) as tar:
        names = set(tar.getnames())

        def raw(name):
            return tar.extractfile(PREFIX + name).read()

        def read(name):
            return json.loads(raw(name))

        plan = read("plan.json")
        assert hashlib.sha256(raw("plan.json")).hexdigest() == raw("plan.sha256").decode().strip()
        expected = set(itertools.product(TASKS, STAGES, METHODS, [0]))
        assert {
            (c["task_id"], c["version"], c["strategy"], c["seed"]) for c in plan["cells"]
        } == expected
        # Original frozen terminal-file manifest, independent of current source.
        terminal_files = 0
        for cell in read("experiment.json")["cells"].values():
            for name, expected_sha in cell.get("files", {}).items():
                assert hashlib.sha256(raw(name)).hexdigest() == expected_sha, name
                terminal_files += 1
        runtime_only = {"root", "output_dir", "adaptation_path", "knowledge_path", "update_cost"}
        expected_config = {k: v for k, v in plan["config"].items() if k not in runtime_only}
        rows, costs, unknowns, protocols, question_hashes = [], [], [], set(), defaultdict(set)
        original_prompts = defaultdict(set)
        for cell in sorted(
            plan["cells"],
            key=lambda c: (c["task_id"], STAGES.index(c["version"]), METHODS.index(c["strategy"])),
        ):
            cid = cell["id"]
            base = f"cells/{cid}/"
            run = base + "run/"
            result = read(run + "result.json")
            trace = read(run + "raw_trace.json")
            evaluation = read(run + f"EVAL/{cell['task_id']}.json")
            adaptation = read(base + "adaptation/adaptation.json")
            knowledge = read(base + "adaptation/knowledge.json")
            target = read(f"catalogs/{cell['task_id']}/{cell['version']}.json")
            assert read(run + "environment-metadata.json") == target
            assert read(run + "knowledge.json") == knowledge
            assert (
                hashlib.sha256(json.dumps(knowledge, sort_keys=True).encode()).hexdigest()
                == result["knowledge_sha256"]
            )
            assert {
                k: v for k, v in result["config"].items() if k not in runtime_only
            } == expected_config
            assert (
                result["agent_model"] == result["judge_model"] == plan["config"]["agent"]["model"]
            )
            assert result["benchmark_commit"] == plan["benchmark_commit"]
            assert result["dataset_revision"] == plan["dataset_revision"]
            protocols.add(result["protocol_sha256"])
            question_hashes[cell["task_id"]].add(
                hashlib.sha256(trace["question"].encode()).hexdigest()
            )
            rating_rows = []
            judge_usages = []
            for i, selected in enumerate(evaluation["eval_result"]["runs"], 1):
                response = selected["response"]
                rating = json.loads(response["choices"][0]["message"]["content"])
                rating_rows.append(rating)
                attempts = sorted(
                    n.removeprefix(PREFIX)
                    for n in names
                    if n.startswith(PREFIX + run + f"judge-attempts/slot-{i}-")
                    and n.endswith("/outcome.json")
                )
                valid = []
                for attempt in attempts:
                    outcome = read(attempt)
                    if outcome.get("response"):
                        judge_usages.append(outcome["response"].get("usage"))
                    # Main cohort has one valid, immutable attempt per slot.
                    if outcome.get("result"):
                        valid.append(outcome)
                assert len(attempts) == len(valid) == 1
                assert valid[0]["response"] == response
                original = raw(run + f"judge-original-prompt-{i}.txt").decode()
                static_rubric = (
                    original.split("# Input Data", 1)[0]
                    + original.rsplit("# SCORING RUBRICS", 1)[1]
                )
                original_prompts[(cell["task_id"], i)].add(
                    hashlib.sha256(static_rubric.encode()).hexdigest()
                )
                assert raw(run + f"judge-prompt-{i}.txt").decode().startswith(original)
            assert len(rating_rows) == 5
            tf = sum(Fraction(str(x["task_fulfillment"])) for x in rating_rows) / 5
            pe = sum(Fraction(str(x["planning_and_efficiency"])) for x in rating_rows) / 5
            close(float(tf), result["TF"])
            close(float(pe), result["PE"])
            events = trace["events"]
            finish_reasons = [
                e["response"]["choices"][0]["finish_reason"]
                for e in events
                if e["type"] == "agent_response"
            ]
            status = result["execution_status"]
            if status == "output_truncated":
                assert finish_reasons[-1] == "length"
            elif status == "max_rounds":
                assert (
                    max(e["round"] for e in events if e["type"] == "agent_response")
                    == expected_config["max_rounds"]
                )
                assert not trace["stop"]
            elif status == "completed":
                assert trace["stop"] and trace["answer"].strip()
            else:
                raise AssertionError(status)
            agent_usages = []
            for e in events:
                if e["type"] == "agent_response":
                    agent_usages.append(e["response"].get("usage"))
                elif e["type"] in ["request_retry", "agent_error"]:
                    agent_usages.append(e.get("usage"))
                    if e.get("usage") is None:
                        unknowns.append(
                            {
                                "cell": cid,
                                "role": "agent",
                                "type": e["type"],
                                "round": e.get("round"),
                                "error_type": e.get("error_type"),
                            }
                        )
            agent_cost, judge_cost = aggregate_usage(agent_usages), aggregate_usage(judge_usages)
            for role, cost in [("agent", agent_cost), ("judge", judge_cost)]:
                close(cost["known_usd"], result["cost"][role]["known_usd"])
                if cost["unknown_requests"]:
                    assert result["cost"][role]["total_tokens"] is None
                    assert result["cost"][role]["usd"] is None
                else:
                    assert cost["total_tokens"] == result["cost"][role]["total_tokens"]
            update = adaptation["cost"]
            if update.get("calls"):
                updater = read(base + "adaptation/updater-audit.json")
                response = updater["response"]
                usage = response["usage"]
                assert usage["total_tokens"] == update["total_tokens"]
                close(usage["cost"], update["usd"])
                assert updater["settings"]["model"] == plan["updater"]["model"]
            else:
                assert update["total_tokens"] == update["usd"] == 0
            costs.append(
                {
                    "cell": cid,
                    "method": cell["strategy"],
                    "agent": agent_cost,
                    "judge": judge_cost,
                    "update": {
                        k: update.get(k) for k in ["calls", "total_tokens", "seconds", "usd"]
                    },
                }
            )
            rows.append(
                {
                    "id": cid,
                    "task": cell["task_id"],
                    "stage": cell["version"],
                    "method": cell["strategy"],
                    "TF": float(tf),
                    "PE": float(pe),
                    "TF_exact": str(tf),
                    "PE_exact": str(pe),
                    "TF_ratings": [x["task_fulfillment"] for x in rating_rows],
                    "PE_ratings": [x["planning_and_efficiency"] for x in rating_rows],
                    "execution_status": status,
                    "tool_calls": sum(e["type"] == "tool_result" for e in events),
                    "tool_errors": sum(
                        e["type"] == "tool_result" and e["result"].get("isError", False)
                        for e in events
                    ),
                }
            )
        assert len(protocols) == 1
        assert all(len(x) == 1 for x in question_hashes.values())
        assert all(len(x) == 1 for x in original_prompts.values())
        for task in plan["suite"]["tasks"]:
            assert question_hashes[task["task_id"]] == {task["question_sha256"]}
        strategy, stage_means, recovery, retention, ecs_tasks = [], [], [], [], []
        by_cell = {(r["task"], r["stage"], r["method"]): r for r in rows}
        for method in METHODS:
            group = [r for r in rows if r["method"] == method]
            ecs = []
            for task in TASKS:
                tf = [by_cell[task, stage, method]["TF"] for stage in STAGES]
                item = {
                    "task": task,
                    "method": method,
                    "TF_versions": tf,
                    "population": statistics.mean(tf) - statistics.pstdev(tf),
                    "sample": statistics.mean(tf) - statistics.stdev(tf),
                }
                ecs.append(item)
                ecs_tasks.append(item)
            updates = [c["update"] for c in costs if c["method"] == method]
            strategy.append(
                {
                    "method": method,
                    "TF": float(sum(Fraction(r["TF_exact"]) for r in group) / 9),
                    "PE": float(sum(Fraction(r["PE_exact"]) for r in group) / 9),
                    "ECS_population": statistics.mean(e["population"] for e in ecs),
                    "ECS_sample": statistics.mean(e["sample"] for e in ecs),
                    "completion": dict(Counter(r["execution_status"] for r in group)),
                    "update_tokens": sum(u["total_tokens"] for u in updates),
                    "update_seconds": sum(u["seconds"] for u in updates),
                    "update_usd": sum(u["usd"] for u in updates),
                }
            )
            for stage in STAGES:
                g = [by_cell[task, stage, method] for task in TASKS]
                stage_means.append(
                    {
                        "method": method,
                        "stage": stage,
                        "TF": statistics.mean(x["TF"] for x in g),
                        "PE": statistics.mean(x["PE"] for x in g),
                    }
                )
                if stage != "early":
                    recovery.append(
                        {
                            "method": method,
                            "stage": stage,
                            "changed_tasks": [133, 283],
                            "TF": statistics.mean(
                                by_cell[t, stage, method]["TF"] for t in [133, 283]
                            ),
                            "delta_TF_vs_no_update": statistics.mean(
                                by_cell[t, stage, method]["TF"]
                                - by_cell[t, stage, "no_update"]["TF"]
                                for t in [133, 283]
                            ),
                            "delta_TF_vs_own_early": statistics.mean(
                                by_cell[t, stage, method]["TF"] - by_cell[t, "early", method]["TF"]
                                for t in [133, 283]
                            ),
                        }
                    )
                    retention.append(
                        {
                            "method": method,
                            "stage": stage,
                            "task": 235,
                            "TF": by_cell[235, stage, method]["TF"],
                            "PE": by_cell[235, stage, method]["PE"],
                            "delta_TF_vs_own_early": by_cell[235, stage, method]["TF"]
                            - by_cell[235, "early", method]["TF"],
                            "delta_PE_vs_own_early": by_cell[235, stage, method]["PE"]
                            - by_cell[235, "early", method]["PE"],
                        }
                    )
        pe_values = [r["PE"] for r in rows if r["method"] == "selective_patch"]
        pe_sum = sum(Fraction(str(x)) for x in pe_values)
        assert pe_sum == 82 and pe_sum / 9 == Fraction(82, 9)
        preflight = [
            u
            for n in names
            if n.startswith(PREFIX + "preflight/") and n.endswith(".json")
            for u in read(n.removeprefix(PREFIX))
        ]
        preflight_cost = aggregate_usage([x["usage"] for x in preflight])
        known_total = (
            sum(c[role]["known_usd"] for c in costs for role in ["agent", "judge"])
            + sum(c["update"]["usd"] for c in costs)
            + preflight_cost["known_usd"]
        )
        return {
            "archive_sha256": digest,
            "terminal_files_verified": terminal_files,
            "cells": rows,
            "strategy_means": strategy,
            "stage_means": stage_means,
            "ecs_by_task": ecs_tasks,
            "recovery": recovery,
            "retention": retention,
            "costs": costs,
            "preflight": preflight_cost,
            "known_total_usd": known_total,
            "unknown_billing": unknowns,
            "selective_PE": {
                "values_task_then_stage": pe_values,
                "sum": str(pe_sum),
                "mean_exact": str(pe_sum / 9),
                "mean": float(pe_sum / 9),
            },
            "fairness": {
                "task_question_hashes_verified": True,
                "config_identical": True,
                "judge_static_rubric_identical_by_task_slot": True,
                "protocol_sha256": list(protocols),
                "model": plan["config"]["agent"]["model"],
                "config": expected_config,
                "benchmark_commit": plan["benchmark_commit"],
                "dataset_revision": plan["dataset_revision"],
            },
            "method": "Independent standard-library recalculation from immutable archive; no source pipeline imports, no network or changed scores.",
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--archive",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "evidence/main-raw.tar.gz",
    )
    parser.add_argument(
        "--output", type=Path, default=Path(__file__).resolve().parents[1] / "evidence/recomputed"
    )
    args = parser.parse_args()
    result = audit(args.archive)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "metrics.json").write_text(json.dumps(result, indent=2) + "\n")
    with (args.output / "cells.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=result["cells"][0].keys())
        writer.writeheader()
        writer.writerows(result["cells"])
    print(
        json.dumps(
            {
                "verified_cells": len(result["cells"]),
                "valid_ratings": 5 * len(result["cells"]),
                "selective_PE": result["selective_PE"],
                "strategy_means": result["strategy_means"],
                "known_total_usd": result["known_total_usd"],
                "unknown_billing": result["unknown_billing"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

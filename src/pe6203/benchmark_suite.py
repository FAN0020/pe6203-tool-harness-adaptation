"""Reviewed course subset and an audited bridge to the existing evaluation engine."""

import csv
from pathlib import Path

from . import evaluation as ev
from .benchmark import read_json, write_json


def validate_suite(suite, output, lock):
    for key, expected in [
        ("benchmark_commit", lock["commit"]),
        ("dataset_revision", lock["dataset_revision"]),
    ]:
        if suite.get(key) != expected:
            raise ValueError(f"Suite {key} does not match the release")
    ev.validate_manifest(
        {
            **suite,
            "experiment_id": suite["suite_id"],
            "comparison_config_file_sha256": "pending-freeze",
            "frozen": True,
            "evidence_kind": "real_model_evaluation",
            "repeat_ids": [0],
        }
    )
    for task in suite["tasks"]:
        for transition in task["transitions"].values():
            if transition["label"] == "uncertain":
                raise ValueError("Benchmark suite needs reviewed transition labels")
    for path, expected in suite["catalog_sha256"].items():
        if ev.digest(Path(output) / path) != expected:
            raise ValueError(f"Reviewed catalog changed: {path}")


def analyze(output, plan):
    """Export traceable manifest/ledger and calculate only complete matched comparisons."""
    output = Path(output).resolve()
    dest = output / "analysis"
    dest.mkdir(exist_ok=True)
    comparison = dest / "comparison-config.json"
    write_json(
        comparison,
        {
            "config": plan["config"],
            "updater": plan.get("updater"),
            "endpoints": plan.get("endpoints"),
            "plan_sha256": ev.digest(output / "plan.json"),
        },
    )
    manifest = {
        "experiment_id": ev.digest(output / "plan.json"),
        "suite_id": plan["suite"]["suite_id"],
        "evidence_kind": "real_model_evaluation",
        "frozen": True,
        "comparison_config_path": comparison.name,
        "comparison_config_file_sha256": ev.digest(comparison),
        "benchmark_commit": plan["benchmark_commit"],
        "dataset_revision": plan["dataset_revision"],
        "tasks": plan["suite"]["tasks"],
        "repeat_ids": sorted({c["seed"] for c in plan["cells"]}),
        "development_reserved_ids": [139, 223],
    }
    ev.validate_manifest(manifest)
    ev.check_comparison_config(manifest, dest)
    ledger = {"runs": [], "updates": []}
    for cell in plan["cells"]:
        directory = output / "cells" / cell["id"]
        ap = directory / "adaptation/adaptation.json"
        if ap.exists():
            cost = read_json(ap).get("cost", {})
            ledger["updates"].append(
                {
                    "artifact_id": cell["id"],
                    "strategy": cell["strategy"],
                    "tokens": cost.get("total_tokens"),
                    "seconds": cost.get("seconds"),
                    "usd": cost.get("usd"),
                    "price_source": str(ap.relative_to(output))
                    + " (provider-reported usage.cost, no price estimate)",
                }
            )
        rp = directory / "run/result.json"
        if not rp.exists():
            continue
        result = read_json(rp)
        operational = {"root", "output_dir", "adaptation_path", "knowledge_path", "update_cost"}
        actual = {k: v for k, v in result.get("config", {}).items() if k not in operational}
        expected = {k: v for k, v in plan["config"].items() if k not in operational}
        if actual != expected:
            raise ValueError(f"Run differs from the frozen common configuration: {cell['id']}")
        entry = {
            "task_id": cell["task_id"],
            "stage": cell["version"],
            "strategy": cell["strategy"],
            "repeat_id": cell["seed"],
            "attempt_id": 0,
            "selected_for_analysis": True,
            "experiment_id": manifest["experiment_id"],
            "comparison_config_file_sha256": manifest["comparison_config_file_sha256"],
            "expected_config_sha256": result["config_sha256"],
            "adaptation_artifact_id": cell["id"],
            "result_path": "../" + str(rp.relative_to(output)),
            "result_path_sha256": ev.digest(rp),
        }
        ep = directory / "run/EVAL" / f"{cell['task_id']}.json"
        if ep.exists():
            entry.update(
                eval_path="../" + str(ep.relative_to(output)), eval_path_sha256=ev.digest(ep)
            )
        ledger["runs"].append(entry)
    write_json(dest / "analysis-manifest.json", manifest)
    write_json(dest / "run-ledger.json", ledger)
    expected, selected, attempts = ev.load_runs(manifest, ledger, dest)
    report = ev.summarize(manifest, selected, attempts)
    report.update(
        update_cost=ev.update_costs(ledger, attempts),
        execution_cost=ev.execution_costs(attempts),
        experiment_id=manifest["experiment_id"],
        planned_cells=len(expected),
        suite_id=plan["suite"]["suite_id"],
        evidence_kind="real_model_evaluation",
        manifest_sha256=ev.digest(dest / "analysis-manifest.json"),
        ledger_sha256=ev.digest(dest / "run-ledger.json"),
        limitations=plan.get("limitations", []),
    )
    write_json(dest / "summary.json", report)
    for name, rows in report.items():
        if isinstance(rows, list) and rows and isinstance(rows[0], dict):
            with (dest / f"{name}.csv").open("w", newline="", encoding="utf-8-sig") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
    return report

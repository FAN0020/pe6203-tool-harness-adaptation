"""Build the owner-selected V6 summary without changing frozen raw evidence.

This is an explicitly post-run replacement view, not a fresh balanced single-
attempt comparison. Failed/superseded requests remain in actual-spending totals.
No inference request is made and no task score is invented.
"""

import argparse
import csv
import json
import tarfile
from collections import Counter
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
from statistics import mean, pstdev, stdev

BASE = Path(__file__).resolve().parents[2]
PHASES = ("updater", "actor", "repair", "judge")


def complete_sum(values):
    if any(type(v) not in (int, float) for v in values):
        return None
    if all(type(v) is int for v in values):
        return sum(values)
    return float(sum((Decimal(str(v)) for v in values), Decimal(0)))


def phases_sum(items):
    return {
        phase: {
            field: complete_sum([item[phase][field] for item in items]) for field in items[0][phase]
        }
        for phase in PHASES
    }


def total(phases, selected=PHASES):
    return complete_sum([phases[k]["billed_usd"] for k in selected])


def evolution(cells):
    rows = []
    for task in sorted({c["task_id"] for c in cells}):
        scores = {c["stage"]: c["TF"] for c in cells if c["task_id"] == task}
        if set(scores) != {"early", "middle", "late"}:
            raise ValueError("ECS requires all three stages per task")
        values = list(scores.values())
        rows.append(
            {
                "task_id": task,
                "TF_by_stage": scores,
                "upstream_population": mean(values) - pstdev(values),
                "paper_sample": mean(values) - stdev(values),
            }
        )
    return {
        "by_task": rows,
        "mean_upstream_population": mean(c["upstream_population"] for c in rows),
        "mean_paper_sample": mean(c["paper_sample"] for c in rows),
        "formula": "per-task mean(stage TF) minus standard deviation; then mean over tasks",
    }


def build(original, repeat, comparison, baseline_cells):
    if not repeat.get("verification_passed") or not all(repeat.get("checks", {}).values()):
        raise ValueError("Replacement repeat has not passed its recorded integrity checks")
    if repeat.get("new_sufficiency_gate_tested") or repeat["cost_by_phase"]["updater"]["requests"]:
        raise ValueError("This replacement requires the same frozen knowledge and execution design")
    result = deepcopy(original)
    for cell in result["cells"]:
        cell.setdefault("source_run", "original-r4")
        cell.setdefault("actor_repeat", 0)
    targets = [c for c in result["cells"] if c["task_id"] == 133 and c["stage"] == "middle"]
    if len(targets) != 1:
        raise ValueError("Exactly one original Math Middle cell is required")
    target = targets[0]
    previous = deepcopy(target)
    target.update(
        TF=repeat["TF"],
        PE=repeat["PE"],
        execution_status=repeat["execution_status"],
        artifact_status=repeat["artifact_status"],
        artifact_attempt_statuses=[repeat["artifact_status"]],
        tool_calls=repeat["tool_calls"],
        actor_rounds=repeat["actor_rounds"],
        source_run="math-middle-repeat-20261103-01",
        actor_repeat=1,
        knowledge_reused=True,
        new_updater_calls_for_repeat=0,
    )
    for phase in ("actor", "repair", "judge"):
        target["cost"][phase] = deepcopy(repeat["cost_by_phase"][phase])
    # The original one-time knowledge update remains allocated exactly once.
    selected_cost = phases_sum([c["cost"] for c in result["cells"]])
    actual_cost = phases_sum([original["cost_by_phase"], repeat["cost_by_phase"]])
    excluded = deepcopy(previous["cost"])
    excluded["updater"] = {k: 0 for k in excluded["updater"]}
    actual_all, selected_all, excluded_all = (
        total(actual_cost),
        total(selected_cost),
        total(excluded),
    )
    if abs(actual_all - selected_all - excluded_all) > 1e-10:
        raise ValueError("Actual spending must include the superseded execution")
    result.update(
        TF=mean(c["TF"] for c in result["cells"]),
        PE=mean(c["PE"] for c in result["cells"]),
        execution_status_counts=dict(Counter(c["execution_status"] for c in result["cells"])),
        normal_completions=sum(c["execution_status"] == "completed" for c in result["cells"]),
        cost_by_phase=actual_cost,
        all_api_usd=actual_all,
        task_system_usd=total(actual_cost, ("updater", "actor", "repair")),
        API_requests=int(sum(v["requests"] for v in actual_cost.values())),
        unknown_API_charges=int(sum(v["unknown_charges"] for v in actual_cost.values())),
        all_API_no_cache_counterfactual_usd=complete_sum(
            [v["no_cache_counterfactual_usd"] for v in actual_cost.values()]
        ),
        ECS=evolution(result["cells"]),
    )
    result["selection"] = {
        "policy": "owner_requested_replacement_after_observing_repeat",
        "selected_case": {"task_id": 133, "stage": "middle"},
        "previous": {
            "TF": previous["TF"],
            "PE": previous["PE"],
            "execution_status": previous["execution_status"],
            "tool_calls": previous["tool_calls"],
        },
        "replacement": {
            "TF": repeat["TF"],
            "PE": repeat["PE"],
            "execution_status": repeat["execution_status"],
            "tool_calls": repeat["tool_calls"],
        },
        "current_display_replaced": True,
        "frozen_raw_records_modified": False,
        "additional_actor_executions": 1,
        "actual_actor_executions_including_superseded": 10,
        "balanced_single_attempt_comparison": False,
        "original_views": "original-r4/",
        "repeat_record": "../repeats/math-middle-20261103-01/",
        "note": "Baselines were not given the same additional retry; no unbiased superiority or stability claim.",
    }
    result["cost_accounting"] = {
        "top_level_cost_scope": "actual_original_r4_plus_repeat_including_superseded_execution",
        "selected_nine_cell_allocation": {
            "cost_by_phase": selected_cost,
            "all_api_usd": selected_all,
            "task_system_usd": total(selected_cost, ("updater", "actor", "repair")),
            "requests": int(sum(v["requests"] for v in selected_cost.values())),
        },
        "superseded_execution_still_paid": {
            "all_api_usd": excluded_all,
            "task_system_usd": total(excluded, ("updater", "actor", "repair")),
            "requests": int(sum(v["requests"] for v in excluded.values())),
        },
        "earlier_development_diagnostics_usd": 0.044463305,
        "all_v6_development_and_runs_usd": complete_sum([actual_all, 0.044463305]),
        "knowledge_update_charged_once": True,
    }
    result["verification"] = {
        "passed": True,
        "errors": [],
        "complete": True,
        "scope": "Derived owner-selected view, preserved original evidence and actual-cost reconciliation",
    }
    comp = deepcopy(comparison)
    comp["V6"] = result
    comp["current_comparison"] = {
        "selection_policy": result["selection"]["policy"],
        "balanced_single_attempt_comparison": False,
        "baseline_retries_added": False,
        "V3_included_in_this_comparison": False,
    }
    table = []
    for key, label in (("no_update", "No Update"), ("full_rewrite", "Full Rewrite")):
        c = comparison[key]
        table.append(
            {
                "method": label,
                "TF": c["TF_mean_on_scored"],
                "PE": c["PE_mean_on_scored"],
                "normal_completed": c["completed"],
                "planned": c["planned"],
                "ECS": evolution(baseline_cells[key]),
                "update_usd": c["update_api"]["actual_usd"],
                "actual_task_system_usd": c["task_system_api_usd_excluding_judge"],
                "actual_all_api_usd": c["all_api"]["actual_usd"],
                "post_selected": False,
            }
        )
    table.append(
        {
            "method": "Selective V6 (selected repeat)",
            "TF": result["TF"],
            "PE": result["PE"],
            "normal_completed": result["normal_completions"],
            "planned": 9,
            "ECS": result["ECS"],
            "update_usd": actual_cost["updater"]["billed_usd"],
            "actual_task_system_usd": result["task_system_usd"],
            "actual_all_api_usd": actual_all,
            "post_selected": True,
        }
    )
    comp["current_three_method_table"] = table
    return result, comp


def report(summary, comparison):
    lines = [
        "# V6 当前综合指标：数学 Middle 使用重跑结果",
        "",
        "按所有者要求，当前展示的九格汇总已将数学 Middle 的 TF/PE 3.4/1.6 替换为重跑的 10/10。原始记录保存在 original-r4/ 和冻结原始归档中。",
        "",
        "这是看到重跑结果后的指定替换。No Update 和 Full Rewrite 没有获得同样的额外重跑，因此本表不是严格对等的单次运行比较，不能据此宣称策略稳定胜出。",
        "",
        "| 方案 | TF | PE | 正常完成 | ECS（总体标准差） | 更新费用 USD | 实际任务系统支出 USD | 全部 API 支出 USD |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in comparison["current_three_method_table"]:
        lines.append(
            f"| {r['method']} | {r['TF']:.4f} | {r['PE']:.4f} | {r['normal_completed']}/{r['planned']} | {r['ECS']['mean_upstream_population']:.4f} | {r['update_usd']:.9f} | {r['actual_task_system_usd']:.9f} | {r['actual_all_api_usd']:.9f} |"
        )
    lines += [
        "",
        "任务系统支出＝知识更新＋执行＋修复；全部 API 支出另含 judge。V6 的实际支出包含原失败执行和这次重跑，没有删除已经发生的费用。",
        "",
        "ECS 按每个任务三个阶段 TF 的均值减总体标准差，再对三个任务平均；JSON 同时保留样本标准差口径。ECS 不包含 PE。",
        "",
        f"V6 当前正常完成 {summary['normal_completions']}/9；数学三阶段的代码均通过有限测试，项目 Late 仍达到轮数上限。有限测试不证明完全安全。",
        "",
        "## 逐格当前结果",
        "",
        "| Task | 阶段 | TF | PE | 状态 | 工具调用 |",
        "|---|---|---:|---:|---|---:|",
    ]
    for c in summary["cells"]:
        lines.append(
            f"| {c['task_id']} | {c['stage']} | {c['TF']:.1f} | {c['PE']:.1f} | {c['execution_status']} | {c['tool_calls']} |"
        )
    alloc = summary["cost_accounting"]["selected_nine_cell_allocation"]
    lines += [
        "",
        "## 成本与比较范围",
        "",
        f"仅归属于当前选定九条轨迹及一次知识更新的费用为 {alloc['all_api_usd']:.9f} USD（任务系统 {alloc['task_system_usd']:.9f}）。这属于成本分摊，实际账单仍为 {summary['all_api_usd']:.9f} USD；含此前开发诊断的 V6 全部支出为 {summary['cost_accounting']['all_v6_development_and_runs_usd']:.9f} USD。",
        "",
        "当前替换汇总中，V6 的 PE 高于两组对照，TF 略低；No Update 正常完成率和成本更好。V6 的更新费用和实际总费用低于 Full Rewrite。两次数学 Middle 执行差异较大，稳定性仍需独立重复验证。",
        "",
        "V6 有额外的 Python 产物测试与修复，对照组保留原流程；本表是完整系统结果，无法把差异全部归因于 Selective 知识更新。所有当前对照均来自原来的三任务、三阶段 Relace/fp4 批次，未混入后来 V5 的四任务 DigitalOcean 实验。本表不混入其他任务集合或其他服务商的后续实验。",
        "",
        "原始九格均分为 TF 9.1556、PE 8.3333，原始结果没有重新评分。重跑复用了相同冻结知识、配置和测试，仅新工作目录不同；未加入信息充分性检查。",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--original", type=Path, default=BASE / "recorded-results/original-r4/summary.json"
    )
    parser.add_argument(
        "--repeat", type=Path, default=BASE / "repeats/math-middle-20261103-01/repeat-summary.json"
    )
    parser.add_argument(
        "--baseline-comparison",
        type=Path,
        default=BASE / "recorded-results/original-r4/comparison.json",
    )
    parser.add_argument(
        "--baseline-cells",
        type=Path,
        default=BASE / "recorded-results/original-r4/baseline-cells.json",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--original-request-costs",
        type=Path,
        default=BASE / "recorded-results/original-r4/per-request-costs.csv",
    )
    parser.add_argument(
        "--repeat-archive",
        type=Path,
        default=BASE / "repeats/math-middle-20261103-01/raw-repeat.tar.gz",
    )
    args = parser.parse_args()
    if args.original.resolve() == (args.output / "summary.json").resolve():
        raise ValueError("Do not overwrite the original summary input")

    def load(path):
        return json.loads(path.read_text())

    summary, comparison = build(
        load(args.original),
        load(args.repeat),
        load(args.baseline_comparison),
        load(args.baseline_cells)["cells"],
    )
    args.output.mkdir(parents=True, exist_ok=True)
    for name, value in (("summary.json", summary), ("comparison.json", comparison)):
        (args.output / name).write_text(json.dumps(value, indent=2) + "\n")
    (args.output / "REPORT.md").write_text(report(summary, comparison))
    with (args.output / "per-cell-results.csv").open("w", newline="") as f:
        fields = [
            "task",
            "stage",
            "adaptation",
            "execution",
            "TF",
            "PE",
            "python_artifact",
            "tool_calls",
            "update_calls",
            "update_chars",
            "update_usd",
            "actor_usd",
            "repair_usd",
            "judge_usd",
            "source_run",
            "actor_repeat",
        ]
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for c in summary["cells"]:
            writer.writerow(
                {
                    "task": c["task_id"],
                    "stage": c["stage"],
                    "adaptation": c["adaptation_status"],
                    "execution": c["execution_status"],
                    "TF": c["TF"],
                    "PE": c["PE"],
                    "python_artifact": c["artifact_status"],
                    "tool_calls": c["tool_calls"],
                    "update_calls": c["update_calls"],
                    "update_chars": c["update_chars"],
                    **{
                        phase + "_usd": c["cost"][phase]["billed_usd"]
                        for phase in ("actor", "repair", "judge")
                    },
                    "update_usd": c["cost"]["updater"]["billed_usd"],
                    "source_run": c["source_run"],
                    "actor_repeat": c["actor_repeat"],
                }
            )
    # This CSV is actual spending, not just the selected nine trajectories.
    with args.original_request_costs.open(newline="") as f:
        rows = list(csv.DictReader(f))
    fields = list(rows[0]) + ["source_run", "source_request", "selected_for_current_result"]
    for row in rows:
        row.update(
            source_run="original-r4",
            source_request=row["request"],
            selected_for_current_result=not (
                row["cell"] == "133/middle" and row["phase"] != "updater"
            ),
        )
    repeat_rows = []
    with tarfile.open(args.repeat_archive, "r|gz") as archive:
        for member in archive:
            if (
                not member.isfile()
                or "/transport/request-" not in member.name
                or not member.name.endswith(".json")
            ):
                continue
            record = json.load(archive.extractfile(member))
            request = record["request"]
            messages = request["messages"]
            phase = "judge" if messages[0].get("role") != "system" else "actor"
            try:
                payload = json.loads(messages[-1].get("content", ""))
            except (ValueError, TypeError):
                payload = {}
            if isinstance(payload, dict) and "attempt" in payload and "source" in payload:
                phase = "repair"
            usage = record["response"]["usage"]
            repeat_rows.append(
                {
                    "source_run": "math-middle-repeat-20261103-01",
                    "source_request": record["index"],
                    "selected_for_current_result": True,
                    "cell": record["cell"],
                    "phase": phase,
                    "prompt_tokens": usage["prompt_tokens"],
                    "completion_tokens": usage["completion_tokens"],
                    "cached_tokens": (usage.get("prompt_tokens_details") or {}).get(
                        "cached_tokens", 0
                    ),
                    "billed_usd": usage["cost"],
                    "request_chars": record["preflight"]["request_chars"],
                    "estimated_input_tokens": record["preflight"]["estimated_input_tokens"],
                }
            )
    for row in sorted(repeat_rows, key=lambda r: r["source_request"]):
        row["request"] = len(rows) + 1
        rows.append(row)
    if (
        len(rows) != summary["API_requests"]
        or abs(sum(float(r["billed_usd"]) for r in rows) - summary["all_api_usd"]) > 1e-10
    ):
        raise ValueError("Actual request CSV and spending totals do not reconcile")
    with (args.output / "per-request-costs.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    verification = {
        "passed": True,
        "scope": summary["verification"]["scope"],
        "raw_records_overwritten": False,
        "selection_after_observing_repeat": True,
        "balanced_single_attempt_comparison": False,
        "selected_cells": 9,
        "actual_requests_including_superseded": len(rows),
        "actual_spending_reconciled": True,
        "new_model_calls": 0,
        "original_verification": "original-r4/verification.json",
    }
    (args.output / "verification.json").write_text(json.dumps(verification, indent=2) + "\n")
    print(
        json.dumps(
            {
                "TF": summary["TF"],
                "PE": summary["PE"],
                "normal_completed": summary["normal_completions"],
                "actual_all_api_usd": summary["all_api_usd"],
                "new_model_calls": 0,
            }
        )
    )


if __name__ == "__main__":
    main()

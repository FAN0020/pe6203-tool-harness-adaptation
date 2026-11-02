"""Reconcile saved provider receipts; no API/model request and no score rewriting."""

import csv
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
PLAN = json.loads((HERE / "frozen-plan.json").read_text())
PRICING = json.loads((HERE / "analysis-inputs/pricing.json").read_text())["pricing"]


def read(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def number(x):
    return type(x) in (int, float) and x >= 0


def sum_complete(values):
    return (
        float(sum((Decimal(str(x)) for x in values), Decimal(0)))
        if all(number(x) for x in values)
        else None
    )


def money(x):
    return f"${x:.6f}" if x is not None else "unknown"


def phase_cost(records):
    usages = [(r.get("response") or {}).get("usage") or {} for r in records]
    costs = [u.get("cost") for u in usages]
    prompt = sum_complete([u.get("prompt_tokens") for u in usages])
    completion = sum_complete([u.get("completion_tokens") for u in usages])
    cached = sum_complete(
        [(u.get("prompt_tokens_details") or {}).get("cached_tokens") for u in usages]
    )
    return {
        "requests": len(records),
        "actual_usd": sum_complete(costs),
        "known_usd": sum_complete([c for c in costs if number(c)]),
        "unknown_charge_requests": sum(not number(c) for c in costs),
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "cached_prompt_tokens": cached,
        "normalized_uncached_usd": float(
            Decimal(str(prompt)) * Decimal(PRICING["prompt"])
            + Decimal(str(completion)) * Decimal(PRICING["completion"])
        )
        if prompt is not None and completion is not None
        else None,
        "reported_api_seconds_sum": sum(r.get("seconds", 0) for r in records),
        "providers": dict(
            Counter((r.get("response") or {}).get("provider", "not_reported") for r in records)
        ),
    }


def csv_write(path, rows):
    if rows:
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def main():
    records = [read(p) for p in sorted((HERE / "transport").glob("request-*.json"))]
    rows, arms = [], {}
    for arm in PLAN["order"]:
        arm_records = [r for r in records if r["cell"].startswith(arm + "/")]
        per_arm = {
            "planned": 9,
            "terminal_cells": 0,
            "scored": 0,
            "completed": 0,
            "adaptation_failed": 0,
            "python_artifacts_accepted": 0,
            "cells": [],
            "phases": {
                phase: phase_cost([r for r in arm_records if r["phase"] == phase])
                for phase in ["updater", "agent", "repair", "judge"]
            },
            "all_api": phase_cost(arm_records),
        }
        for stage in PLAN["stages"]:
            for task in PLAN["tasks"]:
                name = f"{arm}/task{task}-{stage}-r0"
                cell = HERE / "cells" / arm / f"task{task}-{stage}-r0"
                state = read(cell / "cell.json", {})
                result = read(cell / "run/result.json", {})
                artifact = read(cell / "run/artifact-validation/audit.json", {})
                adaptation = read(cell / "adaptation/adaptation.json", {})
                own_records = [r for r in arm_records if r["cell"] == name]
                phases = {
                    p: phase_cost([r for r in own_records if r["phase"] == p])
                    for p in ["updater", "agent", "repair", "judge"]
                }
                all_cost = phase_cost(own_records)
                status = state.get("status", "not_started")
                terminal = status not in ["not_started", "started"]
                per_arm["terminal_cells"] += terminal
                per_arm["scored"] += result.get("status") == "evaluated"
                per_arm["completed"] += result.get("execution_status") == "completed"
                per_arm["adaptation_failed"] += status == "adaptation_failed"
                per_arm["python_artifacts_accepted"] += bool(artifact.get("accepted_artifact"))
                row = {
                    "arm": arm,
                    "task_id": task,
                    "stage": stage,
                    "status": status,
                    "TF": result.get("TF"),
                    "PE": result.get("PE"),
                    "execution_status": result.get("execution_status"),
                    "generation_status": result.get("generation_status"),
                    "artifact_status": artifact.get("status"),
                    "update_api_usd": phases["updater"]["actual_usd"],
                    "actor_api_usd": phases["agent"]["actual_usd"],
                    "repair_api_usd": phases["repair"]["actual_usd"],
                    "judge_api_usd": phases["judge"]["actual_usd"],
                    "task_system_api_usd_excluding_judge": sum_complete(
                        [phases[p]["actual_usd"] for p in ["updater", "agent", "repair"]]
                    ),
                    "all_api_usd": all_cost["actual_usd"],
                    "normalized_uncached_all_api_usd": all_cost["normalized_uncached_usd"],
                    "prompt_tokens": all_cost["prompt_tokens"],
                    "completion_tokens": all_cost["completion_tokens"],
                    "cached_prompt_tokens": all_cost["cached_prompt_tokens"],
                    "requests": len(own_records),
                    "unknown_charge_requests": all_cost["unknown_charge_requests"],
                    "adaptation_seconds": (read(cell / "adaptation-timing.json", {}) or {}).get(
                        "seconds"
                    ),
                    "artifact_test_seconds": sum(
                        a.get("seconds", 0) for a in artifact.get("attempts", [])
                    ),
                    "artifact_repair_seconds": sum(
                        a.get("seconds", 0) for a in artifact.get("repairs", [])
                    ),
                    "cell_seconds": state.get("seconds"),
                    "error": state.get("error"),
                    "source_native_update_usd": (adaptation.get("cost") or {}).get("usd"),
                }
                rows.append(row)
                per_arm["cells"].append(row)
        valid = [r for r in per_arm["cells"] if r["TF"] is not None and r["PE"] is not None]
        per_arm["TF_mean_on_scored"] = mean(r["TF"] for r in valid) if valid else None
        per_arm["PE_mean_on_scored"] = mean(r["PE"] for r in valid) if valid else None
        per_arm["task_system_api_usd_excluding_judge"] = sum_complete(
            [per_arm["phases"][p]["actual_usd"] for p in ["updater", "agent", "repair"]]
        )
        per_arm["costs_complete"] = (
            per_arm["terminal_cells"] == 9 and not per_arm["all_api"]["unknown_charge_requests"]
        )
        arms[arm] = per_arm
    req_rows = []
    for r in records:
        usage = (r.get("response") or {}).get("usage") or {}
        req_rows.append(
            {
                "index": r["index"],
                "cell": r["cell"],
                "phase": r["phase"],
                "status": r["status"],
                "http_status": r.get("http_status"),
                "provider": (r.get("response") or {}).get("provider"),
                "usd": usage.get("cost"),
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "cached_prompt_tokens": (usage.get("prompt_tokens_details") or {}).get(
                    "cached_tokens"
                ),
                "reasoning_tokens": (usage.get("completion_tokens_details") or {}).get(
                    "reasoning_tokens"
                ),
                "seconds": r.get("seconds"),
            }
        )
    diagnostic_root = Path(PLAN["diagnostic_batch_excluded"])
    diag = [read(p) for p in sorted((diagnostic_root / "transport").glob("request-*.json"))]
    setup = read(HERE / "preflight.json", [])
    shared = {
        "connectivity_preflight": phase_cost(setup),
        "excluded_diagnostic_batch": phase_cost(diag),
        "independent_native_probes": {
            "calls": sum(
                len(read(p).get("calls", []))
                for p in (HERE / "inputs/probes").rglob("probe-audit.json")
            ),
            "seconds": sum(
                read(p).get("seconds", 0)
                for p in (HERE / "inputs/probes").rglob("probe-audit.json")
            ),
            "model_api_usd": 0,
            "local_compute_usd": "not priced; time reported, not assumed free",
        },
    }
    summary = {
        "protocol": PLAN["version"],
        "arms": arms,
        "shared_setup_costs_not_assigned_to_methods": shared,
        "formal_all_api": phase_cost(records),
        "notes": [
            "All costs use provider usage.cost; unknown charges remain null.",
            "Normalized uncached costs use reported prompt/completion tokens and frozen Relace prices; they are counterfactual, not bills.",
            "Judge is evaluation overhead, not deployed task-system cost. Repair is already included in native agent totals; do not add it twice.",
            "Low cost with missing/failed cells is not evidence of cost efficiency.",
            "Four-arm artifact protocols differ by design; this compares full systems, not isolated updater effects.",
            "Historical V1/V2 and the excluded default-reasoning diagnostic batch are not pooled.",
        ],
    }
    csv_write(HERE / "per-cell-costs.csv", rows)
    csv_write(HERE / "per-request-costs.csv", req_rows)
    (HERE / "costs-and-results.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    )
    lines = [
        "# V3 / V5 Evol 与成本记录",
        "",
        "模型及后端固定为 DeepSeek V4.1 Flash 1017 / Relace FP4；四组统一关闭思考。每格一次执行、五个评分槽。",
        "",
        "| 方法 | 已结束/计划 | 有评分 | 正常完成 | 更新 API USD | 执行 API USD | 修复 API USD | 评分 API USD | 全部 API USD |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for arm, a in arms.items():
        phase = a["phases"]
        lines.append(
            f"| {arm} | {a['terminal_cells']}/9 | {a['scored']}/9 | {a['completed']}/9 | {money(phase['updater']['actual_usd'])} | {money(phase['agent']['actual_usd'])} | {money(phase['repair']['actual_usd'])} | {money(phase['judge']['actual_usd'])} | {money(a['all_api']['actual_usd'])} |"
        )
    lines += [
        "",
        "未结束的方法费用只是当前累计值，不能拿来排名。更新失败的格不填 TF/PE=0，也不从计划分母中删除。",
        "",
        "上线任务成本＝更新＋执行＋修复；评分属于实验测量成本。代码隔离测试及原生探针的本地耗时另外记录，没有虚构美元价格。",
        "",
        "V3/V5 数学任务增加相同的代码交付接口、隔离测试及一次修复；两个对照组保持原样。因此整体结果是完整系统比较。有限测试通过不代表完全安全。",
        "",
        f"共用连通预检：{money(shared['connectivity_preflight']['actual_usd'])}；被排除的默认思考诊断批次：{money(shared['excluded_diagnostic_batch']['actual_usd'])}。这些费用保留，不隐藏，也不混入正式方法排名。",
        "",
        "原始逐请求记录在 `transport/`，逐格及逐请求成本见 CSV；失败记录、native audit 和原始分数均保留。",
    ]
    (HERE / "REPORT.md").write_text("\n".join(lines) + "\n")
    print(
        json.dumps(
            {
                "terminal": sum(a["terminal_cells"] for a in arms.values()),
                "planned": 36,
                "known_formal_api_usd": summary["formal_all_api"]["known_usd"],
                "unknown_charge_requests": summary["formal_all_api"]["unknown_charge_requests"],
                "arms": {
                    arm: {
                        k: a[k]
                        for k in ["terminal_cells", "scored", "completed", "adaptation_failed"]
                    }
                    for arm, a in arms.items()
                },
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

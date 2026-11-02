"""Separate first-attempt and retry-aware readouts; never overwrite original metrics."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

from pe6203.benchmark import read_json, write_json

TASKS = (133, 235, 283, 430, 90)
STAGES = ("early", "middle", "late")
ARMS = ("v1", "v2", "v3", "v5", "v6", "no_update", "full_rewrite")


def observations(root, item):
    if item["TF"] is None or item["PE"] is None:
        return []
    source = item["source"]
    if source in ("v35-original-three-20261103", "five-task-supplement-20261103"):
        data = read_json(root / f"evaluation/supplements/five-task-20261103/{source}/verification.json")
        return [{"repeat": r["repeat"], "TF": r["TF"], "PE": r["PE"]} for r in data["rows"]
                if r["arm"] == item["arm"] and r["task_id"] == item["task_id"] and r["stage"] == item["stage"] and r["outcome"] == "scored"]
    if source.startswith(("evaluation/v3/", "evaluation/v5/")):
        data = read_json(root / source)
        r = next(r for r in data["cell_summaries"] if r["strategy"] == "selective_patch" and r["task_id"] == item["task_id"] and r["stage"] == item["stage"])
        return [{"repeat": i + 1, "TF": tf, "PE": pe} for i, (tf, pe) in enumerate(zip(r["TF_runs"], r["PE_runs"], strict=True))]
    return [{"repeat": 0, "TF": item["TF"], "PE": item["PE"]}]


def stats(records, arm):
    cells = [r for r in records if r["arm"] == arm]
    valid = [r for r in cells if r["observations"]]
    task_ecs = []
    for task in TASKS:
        lookup = {r["stage"]: {o["repeat"]: o["TF"] for o in r["observations"]} for r in cells if r["task_id"] == task}
        common = set.intersection(*(set(lookup[s]) for s in STAGES))
        if common:
            values = []
            for repeat in sorted(common):
                scores = [lookup[s][repeat] for s in STAGES]
                values.append(statistics.mean(scores) - statistics.pstdev(scores))
            task_ecs.append({"task_id": task, "ECS": statistics.mean(values), "matched_repeats": len(values)})
    return {"scored_conditions": len(valid), "planned_conditions": 15,
            "TF_scored_conditions": statistics.mean(statistics.mean(o["TF"] for o in r["observations"]) for r in valid),
            "PE_scored_conditions": statistics.mean(statistics.mean(o["PE"] for o in r["observations"]) for r in valid),
            "ECS_complete_five_tasks": statistics.mean(r["ECS"] for r in task_ecs) if len(task_ecs) == 5 else None,
            "ECS_task_details": task_ecs}


def report(root, retry, out):
    if out.exists():
        raise ValueError("Do not overwrite an existing retry report")
    verified = read_json(retry / "verification.json")
    if not verified["passed"]:
        raise ValueError("Offline retry audit must pass before reporting")
    coverage = read_json(root / "evaluation/supplements/five-task-20261103/five-task-coverage.json")["rows"]
    before = [{**r, "observations": observations(root, r)} for r in coverage]
    after = [{**r, "observations": [dict(o) for o in r["observations"]]} for r in before]
    retry_rows = defaultdict(list)
    for c in read_json(retry / "plan.json")["cell_order"]:
        path = retry / "runs" / c["id"] / "result.json"
        if path.is_file():
            r = read_json(path)
            if r["TF"] is not None and r["PE"] is not None:
                retry_rows[c["arm"], c["task_id"], c["stage"]].append({"repeat": c["repeat"], "TF": r["TF"], "PE": r["PE"]})
    applied = []
    for r in after:
        key = r["arm"], r["task_id"], r["stage"]
        if key not in retry_rows:
            continue
        if r["observations"]:
            raise ValueError("Retry tried to replace a previously scored condition")
        r["observations"] = retry_rows[key]
        applied.append({"arm": key[0], "task_id": key[1], "stage": key[2], "all_valid_runs_included": len(retry_rows[key])})
    data = {"scope": "Posthoc retry-aware exploratory results; original first-attempt scores preserved",
            "inclusion": "ALL valid first-retry scores replace only missing conditions in this separate view, regardless of score direction",
            "aggregation": "Equal weight task-stage conditions; actor repeats averaged within each condition",
            "ECS": "Population std within matched three-stage repeat; mean repeats within task, then equal-weight all five tasks. Missing or unmatched task -> no full ECS",
            "before": {a: stats(before, a) for a in ARMS}, "after": {a: stats(after, a) for a in ARMS},
            "included_retry_conditions": applied, "after_condition_observations": after,
            "additional_costs": read_json(retry / "summary.json")["by_arm"],
            "actual_additional_API_usd": read_json(retry / "summary.json")["known_actual_usd"],
            "V6_math_middle_selection": "Uses original first pass (3.4/1.6), not previously selected favorable10/10 repeat",
            "controls": "No new control execution; no claim of controlled superiority",
            "original_overwrite": False}
    out.mkdir(parents=True)
    write_json(out / "comparison.json", data)
    lines = ["# 所有失败条件统一重试一次：补充结果", "",
             "这是看到首轮失败后开展的探索性恢复实验。原始首轮结果、此前五任务汇总和全部失败不变。不能把本表称为未重试的主实验。", "",
             "固定V2/V3/V5/V6的7个更新失败条件，各重新更新一次；成功后进行3次独立actor执行。所有有效新评分都进入本补充视图，即使均分降低；不进行成功挑选或反复重跑。", "",
             "| 方法 | 首轮有效条件 | 首轮TF | 首轮PE | 一次重试后有效条件 | 重试后TF | 重试后PE | 五任务ECS |",
             "| --- | --- | ---: | ---: | --- | ---: | ---: | ---: |"]
    for a in ARMS:
        b, f = data["before"][a], data["after"][a]
        e = f"{f['ECS_complete_five_tasks']:.3f}" if f["ECS_complete_five_tasks"] is not None else "缺失/重复不匹配"
        lines.append(f"| {a} | {b['scored_conditions']}/15 | {b['TF_scored_conditions']:.3f} | {b['PE_scored_conditions']:.3f} | {f['scored_conditions']}/15 | {f['TF_scored_conditions']:.3f} | {f['PE_scored_conditions']:.3f} | {e} |")
    lines += ["", "TF/PE仅是已有评分条件的均分，必须连同分母解释；五任务仍含不同历史批次、服务商和重复数，不是严格同期排行榜。V6数学Middle使用原始首轮；此前有利重跑未混入此表。", "",
              "## 本轮逐条件结果", ""]
    for c in read_json(retry / "summary.json")["retry_conditions"]:
        lines.append(f"- {c['arm']} / {c['task_id']} / {c['stage']}：{c['retry_update_status']}；{'; '.join(c['failure']) if c['failure'] else '更新通过，执行和评分另见原始结果。'}")
    lines += ["", "## 新增费用", "",
              "下列费用全部是额外发生的费用，不替代、扣除或抹去首轮支出。", "",
              "| 方法 | 重试更新 USD | 新执行 USD | 更新＋执行 USD，不含judge |",
              "| --- | ---: | ---: | ---: |"]
    for a in ("v2", "v3", "v5", "v6"):
        c = data["additional_costs"][a]
        lines.append(f"| {a} | {float(c['update_usd_once']):.6f} | {float(c['actor_usd']):.6f} | {float(c['deployment_usd']):.6f} |")
    lines += ["", f"包含judge的本轮全部真实API支出：USD {data['actual_additional_API_usd']}。", "",
              "V2历史283Late未锁服务商；本轮固定DigitalOcean，已记录协议差异。若要证明一次重试策略优于其他方法，应在新协议下统一比较，不能把补充结果冒充原始对照实验。"]
    (out / "README.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({a: v for a, v in data["after"].items()}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--retry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report(args.root.resolve(), args.retry.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()

"""Publish supplemental evidence and coverage; no inference calls or score edits."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import statistics
import tarfile
from collections import defaultdict
from pathlib import Path

from pe6203.benchmark import read_json, write_json

BATCHES = ("v35-original-three-20261103", "five-task-supplement-20261103")
TASKS = (133, 235, 283, 430, 90)
ARMS = ("no_update", "full_rewrite", "v1", "v2", "v3", "v5", "v6")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def coverage(root, runs):
    groups = defaultdict(list)

    def add(arm, task, stage, tf, pe, batch, repeats=1):
        groups[arm, task, stage].append({"TF": tf, "PE": pe, "source": batch, "actor_repeats": repeats})

    for path, version in [("results/evidence/course-v1.3-20261031/summary.json", "v1"),
                          ("evaluation/v2/recorded-results/summary.json", "v2")]:
        for row in read_json(root / path)["rows"]:
            if row["strategy"] == "selective_patch":
                add(version, row["task_id"], row["version"], row["TF"], row["PE"], path)
    for row in read_json(root / "evaluation/v6/recorded-results/original-r4/summary.json")["cells"]:
        add("v6", row["task_id"], row["stage"], row["TF"], row["PE"], "evaluation/v6/recorded-results/original-r4/summary.json")
    for arm, rows in read_json(root / "evaluation/v6/recorded-results/original-r4/baseline-cells.json")["cells"].items():
        for row in rows:
            add(arm, row["task_id"], row["stage"], row["TF"], row["PE"], "evaluation/v6/recorded-results/original-r4/baseline-cells.json")
    for version, folder in [("v3", "recorded-108"), ("v5", "recorded-72")]:
        path = f"evaluation/{version}/{folder}/summary.json"
        for row in read_json(root / path)["cell_summaries"]:
            if row["strategy"] == "selective_patch" and row["task_id"] in (430, 90):
                add(version, row["task_id"], row["stage"], row["TF_mean"], row["PE_mean"], path, row["scored"])
    for batch in BATCHES:
        verification = read_json(runs / batch / "verification.json")
        buckets = defaultdict(list)
        for row in verification["rows"]:
            buckets[row["arm"], row["task_id"], row["stage"]].append(row)
        for (arm, task, stage), rows in buckets.items():
            scored = [r for r in rows if r["outcome"] == "scored"]
            add(arm, task, stage, statistics.mean(r["TF"] for r in scored) if scored else None,
                statistics.mean(r["PE"] for r in scored) if scored else None, batch, len(scored))
    records = []
    for arm in ARMS:
        for task in TASKS:
            for stage in ("early", "middle", "late"):
                rows = groups[arm, task, stage]
                if len(rows) != 1:
                    raise ValueError(f"Expected one predeclared source per condition: {arm, task, stage}")
                records.append({"arm": arm, "task_id": task, "stage": stage, **rows[0]})
    return records


def package(root, runs, out):
    if out.exists():
        raise ValueError("Refusing to overwrite a published evidence package")
    verifications = {batch: read_json(runs / batch / "verification.json") for batch in BATCHES}
    if not all(v["passed"] for v in verifications.values()):
        raise ValueError("Complete offline checks are required")
    records = coverage(root, runs)
    out.mkdir(parents=True)
    write_json(out / "five-task-coverage.json", {"rows": records,
               "scope": "Cross-batch inventory; V6 first-pass original three tasks; no post-hoc favorable replacement; no pooled version leaderboard"})
    manifest = {"schema": "supplement-evidence-1", "archives": {}, "files": {},
                "primary_method": "V6", "historical_reference": "V1", "v4": "excluded",
                "methodology": "Blocked updates retained without fabricated official scores; all original records preserved"}
    sources = set()
    for batch in BATCHES:
        home = runs / batch
        target = out / batch
        target.mkdir()
        for name in ("plan.json", "knowledge-freeze.json", "summary.json", "verification.json", "trajectories.csv"):
            shutil.copy2(home / name, target / name)
        archive = target / "raw-measurements.tar.gz"
        members = {}
        with tarfile.open(archive, "w:gz", compresslevel=6) as tar:
            for p in sorted(home.rglob("*")):
                if p.is_symlink():
                    raise ValueError("Unexpected link in raw evidence")
                if p.is_file():
                    name = batch + "/" + str(p.relative_to(home))
                    members[name] = sha(p)
                    tar.add(p, arcname=name, recursive=False)
        write_json(target / "raw-manifest.json", {"sha256": sha(archive), "members": members})
        manifest["archives"][str(archive.relative_to(out))] = {"sha256": sha(archive), "members": len(members)}
        sources.update(read_json(home / "plan.json")["source_files_sha256"])
    sources.update(("scripts/verify_task_supplement.py", "scripts/package_five_task_supplement.py"))
    archive = out / "runtime.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for name in sorted(sources):
            tar.add(root / name, arcname=name, recursive=False)
    manifest["archives"][archive.name] = {"sha256": sha(archive), "members": len(sources)}
    lines = ["# 五任务补测：V6 为主方法，V1 为历史基线", "",
             "五任务为133（数学安全）、235（销售图表）、283（项目规划）、430（SwiftUI）、90（卡牌及每日题）；V4不纳入。",
             "这是补齐历史缺项的证据包，不是所有版本同期、相同重复数的五任务排行榜。", "",
             "## 本次 V3/V5 原三个任务", "",
             "每版计划27条轨迹，知识先更新一次并冻结，再独立执行三次；不增加Python产物测试或修正。", "",
             "| 版本 | 更新通过条件 | 有评分轨迹 / 计划 | 正常最终答复 / 计划 | 已评分TF | 已评分PE | 更新＋执行 USD |",
             "| --- | --- | --- | --- | ---: | ---: | ---: |"]
    for arm in ("v3", "v5"):
        row = verifications[BATCHES[0]]["by_arm"][arm]
        cost = read_json(runs / BATCHES[0] / "summary.json")["by_arm"][arm]["deployment_usd"]
        lines.append(f"| {arm} | {row['update_conditions_validated']}/9 | {row['scored']}/27 | {row['normal_final_answers']}/27 | {row['scored_only_TF']:.3f} | {row['scored_only_PE']:.3f} | {float(cost):.6f} |")
    lines += ["", "V3的283 Late、V5的133 Middle更新失败，各阻止三条执行。两版有效条件不同，均分只描述成功进入评分的子集，不能直接据此判优。未赋零分，也未删掉失败条件。", "",
              "只看两版都进入评分的共同条件，可作补充比较；它排除了更新失败，不能代表完整方法成功率：", "",
              "| 版本 | 共同有效条件 | 轨迹 | TF | PE |", "| --- | --- | --- | ---: | ---: |"]
    paired_rows = verifications[BATCHES[0]]["rows"]
    successful = {arm: {(r["task_id"], r["stage"]) for r in paired_rows if r["arm"] == arm and r["outcome"] == "scored"} for arm in ("v3", "v5")}
    matched = successful["v3"] & successful["v5"]
    for arm in ("v3", "v5"):
        rows = [r for r in paired_rows if r["arm"] == arm and (r["task_id"], r["stage"]) in matched]
        lines.append(f"| {arm} | {len(matched)}/9 | {len(rows)} | {statistics.mean(r['TF'] for r in rows):.3f} | {statistics.mean(r['PE'] for r in rows):.3f} |")
    lines += ["",
              "## 新增430、90的同期补测", "",
              "各组计划18条轨迹，两个任务×三个阶段×三次执行。No Update、Full Rewrite策略和执行流程不改。两个任务不适用Python产物验证；V6仅做冻结后的事后诊断。", "",
              "| 方案 | 更新通过条件 | 有评分 / 计划 | 正常最终答复 / 计划 | 已评分TF | 已评分PE | 更新＋执行 USD |",
              "| --- | --- | --- | --- | ---: | ---: | ---: |"]
    for arm in ("no_update", "full_rewrite", "v1", "v2", "v6"):
        row = verifications[BATCHES[1]]["by_arm"][arm]
        cost = read_json(runs / BATCHES[1] / "summary.json")["by_arm"][arm]["deployment_usd"]
        lines.append(f"| {arm} | {row['update_conditions_validated']}/6 | {row['scored']}/18 | {row['normal_final_answers']}/18 | {row['scored_only_TF']:.3f} | {row['scored_only_PE']:.3f} | {float(cost):.6f} |")
    lines += ["", "已评分均分必须与更新成功率一起解释。更新失败的版本无法提供完整六条件总体均分。失败请求费用均计入。", "",
              "## 五任务覆盖与来源", "",
              "每任务有Early/Middle/Late三格；下表是取得评分的条件数，不是执行次数。", "",
              "| 方案 | 133 | 235 | 283 | 430 | 90 | 有评分条件 / 15 |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for arm in ARMS:
        counts = [sum(r["TF"] is not None and r["PE"] is not None for r in records if r["arm"] == arm and r["task_id"] == task) for task in TASKS]
        lines.append("| " + arm + " | " + " | ".join(f"{n}/3" for n in counts) + f" | {sum(counts)}/15 |")
    lines += ["", "来源逐格记录在five-task-coverage.json。V1、V2、V6及旧对照的原三个任务保留历史单次批次；新任务为三次，模型路由和运行日期也并非所有批次一致。V3/V5原三个任务使用本次新批次，430/90使用各自历史三次正式评测。", "",
              "V6五任务覆盖采用原始首轮数学Middle，不把较好的重跑替换成预注册主结果。已有selected-repeat展示不修改，仍单独保留。V6的Python测试与修复仍仅在原数学任务启用；本补测不改变对照组。", "",
              "## Early与高分的解释", "",
              "Early匹配只排除知识过时，不保证规划、工具运行、最终交付和模型评审满分。相同知识仍可产生不同轨迹；V3还附加能力边界文字，完整输入未必相同。不要把Early强制改成10分或按期望调整No Update分数。", "",
              "235是不变工具的保持能力对照；430与90补充变化场景。扩大任务数可以改善覆盖，但不能消除批次、重复数、执行能力和评分的混杂。五次judge不是五次独立agent执行。", "",
              "## 费用与复核", ""]
    for batch in BATCHES:
        v = verifications[batch]
        lines.append(f"- {batch}：{v['requests']}次真实API请求，实际已知费用USD {v['actual_known_usd']}；离线核验通过。")
    lines += ["", "更新＋执行费用不含judge；实际批次费用包括judge、失败的更新和所有已经发生的请求。原始request/response、MCP轨迹、工作目录产物、五次评分和逐笔费用全部封存。", "",
              "runtime.tar.gz包含本次使用的源代码、配置与评测脚本。核验脚本为scripts/verify_task_supplement.py，仅离线检查；重新执行实验必须使用新目录和独立凭据。"]
    (out / "README.md").write_text("\n".join(lines) + "\n")
    for p in out.rglob("*"):
        if p.is_file() and p.suffix != ".gz":
            manifest["files"][str(p.relative_to(out))] = sha(p)
    write_json(out / "manifest.json", manifest)
    print(json.dumps({"package": str(out), "archive_bytes": sum((out / p).stat().st_size for p in manifest["archives"])}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--runs", type=Path, default=Path("results/raw"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    package(args.root.resolve(), args.runs.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()

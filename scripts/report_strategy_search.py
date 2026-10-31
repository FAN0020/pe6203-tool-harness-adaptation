"""Readable, evidence-linked research history; never edits executions or ratings."""

import argparse
import html
import json
import os
import statistics
from collections import Counter
from pathlib import Path

from pe6203.benchmark import read_json, write_json
from pe6203.experiment import adaptation_path, summarize

ROOT = Path(__file__).resolve().parents[1]
NAMES = {133: "数学表达式与安全建议", 235: "销售图表／保持能力", 283: "项目拆解"}


def esc(value):
    return html.escape(str(value))


def average(values):
    values = list(values)
    return statistics.mean(values) if values and all(v is not None for v in values) else None


def fmt(value):
    return "—" if value is None else f"{value:.3f}" if isinstance(value, float) else esc(value)


def table(headers, rows):
    return (
        '<div class="scroll"><table><thead><tr>'
        + "".join(f"<th>{esc(h)}</th>" for h in headers)
        + "</tr></thead><tbody>"
        + "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
        + "</tbody></table></div>"
    )


def link(path, label, destination):
    relative = os.path.relpath(Path(path).resolve(), destination.parent)
    return f'<a href="{esc(relative)}">{esc(label)}</a>'


def costs_by_arm(directory, plan):
    def totals(costs):
        result = {}
        for field in ("usd", "total_tokens", "seconds"):
            values = [cost.get(field) for cost in costs]
            result[field] = (
                sum(values) if values and all(v is not None for v in values) else None
            )
        result["known_usd"] = sum(
            (c.get("known_usd") if c.get("known_usd") is not None else c.get("usd")) or 0
            for c in costs
        )
        result["unknown_totals"] = sum(c.get("usd") is None for c in costs)
        return result

    result = []
    for arm in sorted({c["strategy"] for c in plan["cells"]}):
        cells = [c for c in plan["cells"] if c["strategy"] == arm]
        paths = {adaptation_path(directory, plan, c) for c in cells}
        updates = [read_json(p)["cost"] if p.exists() else {} for p in paths]
        runs = [Path(directory) / "cells" / c["id"] / "run/result.json" for c in cells]
        recorded = [read_json(p).get("cost", {}) for p in runs if p.exists()]
        result.append(
            {
                "strategy": arm,
                "planned": len(cells),
                "recorded_executions": len(recorded),
                "unique_updates": len(paths),
                "generated_updates": sum(p.exists() for p in paths),
                "update": totals(updates),
                "agent": totals([r.get("agent", {}) for r in recorded]),
                "judge": totals([r.get("judge", {}) for r in recorded]),
            }
        )
    return result


def analyze(directory):
    summary = summarize(directory)
    rows = summary["rows"]
    arms = sorted({r["strategy"] for r in rows})
    metrics = []
    for arm in arms:
        for stage in sorted({r["version"] for r in rows}, key=["early", "middle", "late"].index):
            group = [r for r in rows if r["strategy"] == arm and r["version"] == stage]
            metrics.append(
                {
                    "strategy": arm,
                    "stage": stage,
                    "scored": sum(r["TF"] is not None for r in group),
                    "planned": len(group),
                    "TF": average(r["TF"] for r in group),
                    "PE": average(r["PE"] for r in group),
                }
            )
    comparisons = []
    index = {(r["task_id"], r["version"], r["strategy"], r["seed"]): r for r in rows}
    for arm in arms:
        for stage in ["middle", "late"]:
            for kind, tasks in [("recovery", [133, 283]), ("retention", [235])]:
                pairs = [
                    r
                    for r in rows
                    if r["strategy"] == arm and r["version"] == stage and r["task_id"] in tasks
                ]
                item = {"strategy": arm, "stage": stage, "group": kind, "pairs_planned": len(pairs)}
                for field in ["TF", "PE"]:
                    for comparator in ["no_update", "selective_patch", "own_early"]:
                        differences = []
                        for r in pairs:
                            other = index.get(
                                (
                                    r["task_id"],
                                    "early" if comparator == "own_early" else stage,
                                    arm if comparator == "own_early" else comparator,
                                    r["seed"],
                                ),
                                {},
                            )
                            a, b = r.get(field), other.get(field)
                            differences.append(a - b if a is not None and b is not None else None)
                        item[f"delta_{field}_vs_{comparator}"] = average(differences)
                comparisons.append(item)
    cases = []
    for row in rows:
        directory_run = directory / "cells" / row["id"] / "run"
        trace_path = directory_run / "raw_trace.json"
        trace = read_json(trace_path) if trace_path.exists() else {}
        calls = [e for e in trace.get("events", []) if e.get("type") == "tool_result"]
        errors = [e for e in calls if e.get("result", {}).get("isError")]
        cases.append(
            {
                **row,
                "tool_calls": len(calls),
                "tool_error_events": errors,
                "chosen_tools": dict(Counter(e["call"]["function"]["name"] for e in calls)),
                "answer": trace.get("answer", ""),
                "trace_path": str(trace_path),
            }
        )
    result = {
        "summary": summary,
        "metrics": metrics,
        "recovery_retention": comparisons,
        "cases": cases,
        "costs_by_arm": costs_by_arm(directory, read_json(directory / "plan.json")),
    }
    write_json(directory / "readable-analysis.json", result)
    return result


def render(directories, destination):
    destination = Path(destination).resolve()
    sections = [
        "<h1>Selective Patch 策略研究</h1>",
        "<p>研究目标：在不明显损伤 TF、ECS、完成率及逐任务表现的前提下，提高环境变化后的 PE。报告同时保留 recovery、retention 和更新成本；效率改善不自动等于恢复能力改善。</p>",
        "<p>依据课程 brief 与 <a href=\"https://arxiv.org/html/2607.14642v1\">MCPEvol 论文</a>，分别报告指标，不合成任意加权总分。课程核心是变化任务能否恢复、原本可用的任务是否受损；本小子集 TF 接近上限，故候选搜索以受约束的 PE 改善为目标。</p>",
        table(
            ["评价层次", "指标与比较", "判断范围"],
            [
                ["主要结果", "变化任务 TF：Middle/Late 与同阶段 No Update 对照，并展示自身 Early", "衡量恢复；高绝对 TF 不自动证明有恢复增益"],
                ["主要结果", "未变化任务 TF：与原 Selective Patch 及自身 Early 对照", "衡量保持；逐任务展示，避免均值掩盖退化"],
                ["跨版本稳定性", "ECS＝三个版本 TF 均值减标准差", "同时列发布代码与论文附录的标准差口径"],
                ["效率与代价", "PE、更新 tokens／秒／费用；执行费用另列", "满足质量约束后比较效率；PE 不等同于 token 成本"],
                ["补充运行证据", "完成率、截断、轮数耗尽、工具错误及完整轨迹", "补充解释 TF/PE；不改原 benchmark 的评分"],
            ],
        ),
        "<p>本项目预设筛选门槛：PE 至少提高 0.5，整体 TF/ECS 下降均不超过 0.2，任一任务×阶段的平均 TF 下降不超过 0.5，完成数不降低；另检查三次重复的一致性与配对检验。这些是我们的实验选择，不是课程或论文规定；均值容差也不是统计意义上的无退化证明。开发集结果只用于选候选，不能作为独立确认结果。</p>",
        "<p>所有 agent 自行选择工具及参数。固定模型、任务、judge 与执行预算；新规则只来自工具元数据和独立小型探针。三阶段 Early 共用 K0。开发结果用于筛选，确认结果才用于晋级；既有任务上的新重复不代表未见任务泛化。</p>",
        "<p>原有结果："
        + link(ROOT / "reports/course-v1.3-experiment.html", "v1.3 与六条诊断", destination)
        + " · "
        + link(ROOT / "reports/experiment-readiness.html", "旧 A/B 的成功与失败案例", destination)
        + "</p>",
        "<h2>方法依据</h2>",
    ]
    papers = read_json(ROOT / "experiments/.context/selective-literature.json")["papers"]
    sections.append(
        table(
            ["论文", "我们的改造", "与原方法的区别"],
            [
                [
                    f'<a href="{esc(p["url"])}">{esc(p["id"])}</a>',
                    esc(p["adaptation_zh"]),
                    esc(p["difference_zh"]),
                ]
                for p in papers
            ],
        )
    )
    failure = ROOT / "results/evidence/selective-search-20261031/generation-v1-failure.json"
    if failure.exists():
        f = read_json(failure)
        sections += [
            "<h2>保留的生成失败</h2>",
            "<p>v1 在任务执行前被拦截：关联补丁引用了不属于变化集合的工具 ID。执行轨迹数为 0；失败响应、已生成补丁与费用均已归档。v1.1 增加明确 ID 列表及最多一次结构修复，不按分数重试。"
            + link(failure, "完整记录", destination)
            + f"；已知更新费用 ${f['known_update_usd']:.6f}。</p>",
        ]
    rejected = ROOT / "results/evidence/selective-search-20261031/generation-v2-rejection.json"
    if rejected.exists():
        rejected_data = read_json(rejected)
        sections.append(
            "<p>v2 的 workflow 候选在执行前被语义审查拒绝：建议使用已知失败的工具作为替代路径，并把使用条件写得过窄。0 条任务执行，原响应和费用保留。"
            + link(rejected, "拒绝记录", destination)
            + f"；已知更新费用 ${rejected_data['known_update_usd']:.6f}。</p>"
        )
    sections.append(
        "<p>第二轮：<strong>sufficiency_notes</strong> 在变化工具上添加结果复用、完成条件和保留必要检查的规则；<strong>sufficiency_feedback</strong> 再加入冻结探针的局部结果记忆，直接记录观察而不生成替代方案。两者更新都不调用 LLM。</p>"
    )
    for directory in directories:
        directory = Path(directory).resolve()
        a = analyze(directory)
        s = a["summary"]
        plan = read_json(directory / "plan.json")
        sections += [
            f"<h2>{esc(directory.name)}</h2>",
            f"<p>{esc(plan['research']['phase'])}：完整评分 {s['scored']}/{s['planned']}；执行完成 {s['completed_execution']}。截断或轮数耗尽即使 TF 高，也不算执行完成。</p>",
            "<p>"
            + link(directory / "plan.json", "冻结计划", destination)
            + " · "
            + link(directory / "runs.csv", "全部单元 CSV", destination)
            + " · "
            + link(directory / "readable-analysis.json", "结构化分析与完整错误", destination)
            + "</p>",
        ]
        overall = []
        for arm in sorted({row["strategy"] for row in s["rows"]}):
            group = [row for row in s["rows"] if row["strategy"] == arm]
            overall.append(
                [
                    esc(arm),
                    f"{sum(row['TF'] is not None for row in group)}/{len(group)}",
                    fmt(average(row["TF"] for row in group)),
                    fmt(average(row["PE"] for row in group)),
                    str(sum(row["execution_status"] == "completed" for row in group)),
                ]
            )
        sections.append(table(["策略", "完整评分", "整体 TF", "整体 PE", "正常完成"], overall))
        selection_path = directory / "candidate-selection.json"
        if selection_path.exists():
            sections.append(
                "<details><summary>开发筛选决定及限制（尚未晋级）</summary><pre>"
                + esc(json.dumps(read_json(selection_path), ensure_ascii=False, indent=2))
                + "</pre></details>"
            )
        sections.append(
            table(
                ["策略", "阶段", "完整评分", "TF", "PE"],
                [
                    [
                        esc(r["strategy"]),
                        esc(r["stage"]),
                        f"{r['scored']}/{r['planned']}",
                        fmt(r["TF"]),
                        fmt(r["PE"]),
                    ]
                    for r in a["metrics"]
                ],
            )
        )
        sections.append(
            "<h3>恢复与保持</h3><p>recovery＝133/283，retention＝235。Δ 是同阶段配对差值；own Early 衡量各方法自身的跨阶段变化。— 表示对照缺失或评分不完整，不能解读为 0。</p>"
        )
        sections.append(
            table(
                [
                    "策略",
                    "阶段",
                    "子集",
                    "ΔTF / No Update",
                    "ΔTF / 原 Patch",
                    "ΔTF / own Early",
                    "ΔPE / 原 Patch",
                ],
                [
                    [
                        esc(r["strategy"]),
                        esc(r["stage"]),
                        esc(r["group"]),
                        fmt(r["delta_TF_vs_no_update"]),
                        fmt(r["delta_TF_vs_selective_patch"]),
                        fmt(r["delta_TF_vs_own_early"]),
                        fmt(r["delta_PE_vs_selective_patch"]),
                    ]
                    for r in a["recovery_retention"]
                ],
            )
        )
        sections.append("<h3>ECS 与成本</h3>")
        sections.append(
            table(
                ["任务", "策略", "重复", "ECS：发布代码", "ECS：论文附录"],
                [
                    [
                        str(r["task_id"]),
                        esc(r["strategy"]),
                        str(r["repeat"] + 1),
                        fmt(r["upstream_population"]),
                        fmt(r["paper_sample"]),
                    ]
                    for r in s["ecs"]
                ],
            )
        )
        sections.append(
            "<p>每份冻结知识的更新成本只计一次，三次执行复用。API 预检费用另存 preflight/。执行费用仅累计已保存的运行；存在未知收费时，下界不等于总额。</p>"
        )
        sections.append(
            table(
                ["策略", "已保存运行", "更新 tokens", "更新秒数", "更新 $", "执行 $ 下界", "评分 $ 下界", "未知费用记录数"],
                [
                    [
                        esc(r["strategy"]),
                        f"{r['recorded_executions']}/{r['planned']}",
                        fmt(r["update"]["total_tokens"]),
                        fmt(r["update"]["seconds"]),
                        "—" if r["update"]["usd"] is None else f"{r['update']['usd']:.6f}",
                        f"{r['agent']['known_usd']:.6f}",
                        f"{r['judge']['known_usd']:.6f}",
                        str(sum(r[k]["unknown_totals"] for k in ["update", "agent", "judge"])),
                    ]
                    for r in a["costs_by_arm"]
                ],
            )
        )
        sections.append(
            "<details><summary>所有策略合计的原始成本统计</summary><pre>"
            + esc(json.dumps(s["cost"], ensure_ascii=False, indent=2))
            + "</pre></details>"
        )
        if any("feedback" in row["strategy"] for row in s["rows"]):
            sections.append(
                "<p>探针准备成本另计：反馈方法复用研究开始前采集的 12 次独立本地 MCP 探测，没有模型调用；采集耗时未记录，记为未知，不能算作 0。上表更新耗时仅包含冻结反馈已存在时的补丁生成；不代表从零建立反馈记忆的全部成本。12 次探测是一次性共享成本，不应乘以任务重复数，也不能完全忽略。</p>"
            )
        billing = directory / "billing-audit.json"
        if billing.exists():
            sections.append(
                "<p>已知费用下界及未知总额记录：</p><pre>"
                + esc(json.dumps(read_json(billing), ensure_ascii=False, indent=2))
                + "</pre>"
            )
        search_summary = directory / "search-summary.json"
        if search_summary.exists() and read_json(search_summary).get("decision"):
            sections.append(
                "<h3>预设晋级判定</h3><pre>"
                + esc(
                    json.dumps(read_json(search_summary)["decision"], ensure_ascii=False, indent=2)
                )
                + "</pre>"
            )
        sections.append(
            "<h3>逐条成功与失败证据</h3><p>保留全部单元，不只展示高分。工具报错可能被恢复；低分、工具错误或截断本身不能证明 under-update / over-update，需要定位具体知识改动并做对照归因。</p>"
        )
        review_path = directory / "manual-development-review.json"
        reviews = (
            {r["id"]: r for r in read_json(review_path)["cases"]} if review_path.exists() else {}
        )
        for case in a["cases"]:
            title = f"{case['id']} · TF {fmt(case['TF'])} / PE {fmt(case['PE'])} · {case['execution_status']} · {case['tool_calls']} 次工具调用 / {len(case['tool_error_events'])} 次错误"
            content = (
                "<p>"
                + esc(NAMES.get(case["task_id"], case["task_id"]))
                + " · "
                + esc(case["status"])
                + "</p>"
            )
            if case["id"] in reviews:
                content += (
                    "<h4>人工分析（不改评分）</h4><p>"
                    + esc(reviews[case["id"]]["interpretation"])
                    + "</p>"
                )
            content += (
                "<pre>"
                + esc(json.dumps(case["chosen_tools"], ensure_ascii=False, indent=2))
                + "</pre>"
            )
            if case["tool_error_events"]:
                content += (
                    "<h4>错误</h4><pre>"
                    + esc(json.dumps(case["tool_error_events"], ensure_ascii=False, indent=2))
                    + "</pre>"
                )
            if case["answer"]:
                content += "<h4>回答</h4><pre>" + esc(case["answer"]) + "</pre>"
            if Path(case["trace_path"]).exists():
                content += link(case["trace_path"], "完整执行轨迹", destination)
            sections.append("<details><summary>" + title + "</summary>" + content + "</details>")
    page = (
        '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Selective Patch 策略研究</title><style>body{font:16px/1.65 system-ui,sans-serif;max-width:1180px;margin:32px auto;padding:0 20px;color:#20272e;background:#fafbfc}h1,h2,h3{line-height:1.3}h2{margin-top:42px;border-bottom:2px solid #d9e2ec;padding-bottom:10px}a{color:#0969a6}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border:1px solid #d9e2ec;padding:8px;text-align:left;vertical-align:top}th{background:#eaf1f7}th:first-child,td:first-child{min-width:85px}.scroll{overflow:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#eef2f6;padding:14px;border-radius:6px;font-size:13px}details{background:white;border:1px solid #d9e2ec;border-radius:7px;margin:10px 0;padding:12px}summary{cursor:pointer;font-weight:600;overflow-wrap:anywhere}td{overflow-wrap:anywhere}p{max-width:100ch}</style><main>'
        + "\n".join(sections)
        + "</main></html>"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Normalize display-only whitespace; linked raw answers and traces remain byte-exact.
    destination.write_text("\n".join(line.rstrip() for line in page.splitlines()) + "\n")
    print(destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=Path, nargs="+", required=True)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "reports/selective-strategy-search.html"
    )
    args = parser.parse_args()
    render(args.runs, args.output)

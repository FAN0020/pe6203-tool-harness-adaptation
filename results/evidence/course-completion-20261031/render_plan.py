"""Render the current completion plan from JSON; no experimental execution."""

import html
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEST = ROOT / "reports/course-completion-plan.html"


def read(path):
    return json.loads((ROOT / path).read_text())


def esc(value):
    return html.escape(str(value))


def table(headers, rows):
    return (
        '<div class="scroll"><table><thead><tr>'
        + "".join(f"<th>{esc(x)}</th>" for x in headers)
        + "</tr></thead><tbody>"
        + "".join("<tr>" + "".join(f"<td>{esc(x)}</td>" for x in row) + "</tr>" for row in rows)
        + "</tbody></table></div>"
    )


def link(path, label):
    return f'<a href="{esc(os.path.relpath(ROOT / path, DEST.parent))}">{esc(label)}</a>'


def render():
    plan = read("experiments/course-completion-plan.json")
    audit = read("results/evidence/course-completion-20261031/reuse-audit.json")
    pause = read(plan["sources"]["pause_audit"])
    parts = [
        "<h1>PE6203：先完成课程项目</h1>",
        '<p class="lead">最小可行实验 → 离线验证与交付 → 有必要且获批才扩展</p>',
        '<p class="notice"><strong>新实验未获批准，策略搜索已暂停。</strong>主矩阵27条已完整评分：20正常完成、5轮数耗尽、2截断。新增主矩阵为0；两类失败的严格例证和最终展示仍有缺口，不宣称课程已经全部完成。</p>',
        "<p>"
        + link("README.md", "项目入口")
        + " · "
        + link("experiments/course-completion-plan.json", "当前计划 JSON")
        + " · "
        + link("results/evidence/course-completion-20261031/reuse-audit.json", "离线审计")
        + " · "
        + link("results/evidence/course-completion-20261031/pause-audit.json", "停止与归档记录")
        + "</p>",
        "<p>依据："
        + link(plan["sources"]["brief"], "原始 Project 4 brief")
        + " §3.2允许固定子集和预算受限时每cell一次；§4.2要求指标、恢复/保持、更新成本、两类失败分析。"
        + '<a href="https://arxiv.org/html/2607.14642v1#S6.SS1">MCPEvol-Bench §6.1 / D.1</a>提供TF/PE/ECS与评估口径；论文中的模块扩展不是课程必须逐一复现的清单。PE +0.5不是课程要求。</p>',
        "<h2>已安全停止</h2>",
        table(
            ["工作", "保存的状态", "决定"],
            [
                ["确认 R2", "6已评分 / 2连接失败 / 100未开始", "保留，不补跑"],
                [
                    "确认 R3",
                    "5已评分 / 2连接失败 / 101未开始；201终态文件hash核验",
                    "新增完整归档，不补跑",
                ],
                [
                    "连接诊断",
                    f"7/12轮，9次模型请求；已知费用 ${pause['connectivity_diagnostic']['known_usd']:.8f}",
                    "在sleep中SIGINT，无在途请求；保留全部观测，不继续",
                ],
                ["VPN", "用户确认此前启用、现已关闭", "可能影响连接，根因未证实；不作废有效结果"],
            ],
        ),
        "<h2>逐项要求与缺口</h2>",
        table(
            ["Brief", "要求", "状态", "现有证据", "剩余工作"],
            [
                [x[k] for k in ["ref", "requirement", "status", "evidence", "remaining"]]
                for x in plan["requirements"]
            ],
        ),
        "<h2>最小矩阵：直接复用27条</h2>",
        table(
            ["任务", "角色", "覆盖", "三阶段×三方法×一次"],
            [
                [x["id"], x["purpose"], x["coverage"], "9条，全部已评分"]
                for x in plan["minimum_matrix"]["tasks"]
            ],
        ),
        "<p>" + esc(plan["minimum_matrix"]["coverage_limit"]) + "</p>",
        "<p>固定OpenRouter DeepSeek v4.1 Flash；temperature 0；agent 4096输出tokens、12轮、900秒；同一judge及原rubric、5个首次有效评分槽。每槽最多2次逻辑尝试，每HTTP请求最多1次重试。三方法的任务、解码、工具服务器和执行预算相同。5次评分不是5次agent执行。</p>",
        "<h2>可以直接使用的主结果</h2>",
        table(
            [
                "方法",
                "TF（9条均值）",
                "PE（9条均值）",
                "ECS population",
                "正常完成",
                "轮数耗尽 / 截断",
            ],
            [
                [
                    x["method"],
                    f"{x['TF']:.4f}",
                    f"{x['PE']:.4f}",
                    f"{x['ECS_population']:.4f}",
                    f"{x['execution_status'].get('completed', 0)}/9",
                    f"{x['execution_status'].get('max_rounds', 0)} / {x['execution_status'].get('output_truncated', 0)}",
                ]
                for x in audit["course_metrics"]
            ],
        ),
        "<p>恢复：Selective Patch在133/283上相对同阶段No Update，Middle ΔTF=0，Late +0.1。保持：235各阶段TF=10，ΔTF=0，PE仍有波动。主表同时附逐阶段数值和ECS sample口径。TF接近上限不证明所有产物正确；原始评分不修改。</p>",
        "<p>更新成本：Full Rewrite 177974 tokens / 203.508秒 / $0.049176；Selective Patch 0模型tokens / 1.145秒 / $0；No Update为0。主实验执行、评分、更新、preflight合计已知$"
        + f"{audit['course_cost']['known_total_usd']:.6f}"
        + "，另1次失败请求费用未知；不是完整账单。27条执行跨度约32.75分钟，独立诊断另计。</p>",
        "<h2>复用旧结果，保留成功和失败</h2>",
        table(
            ["Cohort", "已有数据", "用途与边界"],
            [[x["cohort"], x["evidence"], x["use"]] for x in plan["reuse"]],
        ),
        "<p>"
        + link("reports/course-v1.3-experiment.html", "主实验逐条结果和六条负诊断")
        + " · "
        + link("reports/selective-strategy-search.html", "历史研究全部轨迹、费用、成功/失败案例")
        + " · "
        + link("reports/experiment-readiness.html", "旧A/B报告")
        + "</p>",
        "<h2>失败案例：什么已经知道，什么还不知道</h2>",
        table(
            ["案例", "已观察", "允许的结论"],
            [
                [
                    "133 Late No Update",
                    "缺必填allow_variables，工具拒绝；随后补参恢复。Selective已更新并成功调用。",
                    "陈旧知识的直接机制例证；不能称为Selective Patch漏改。",
                ],
                [
                    "235 Late Full Rewrite（旧B）",
                    "TF8.8/PE4.2；五次地图调用、单位缺失。",
                    "无关重写与退化同时出现，仍是候选而非已证因果。",
                ],
                [
                    "235回退诊断",
                    "重写/回退各3次，全部TF/PE10。",
                    "未证实历史over-update假设；不得为了出现伤害反复追跑。",
                ],
                [
                    "Early公共K0 / 发布包错误 / 网络中断",
                    "相同知识也会截断或耗尽轮数；Late存在原包缺失内部方法。",
                    "作为预算、评判和工程局限；不能自动贴under/over-update标签。",
                ],
            ],
        ),
        "<h2>剩余实验与增量预算</h2>",
    ]
    for item in plan["remaining_experiment_options"]:
        parts += [f"<h3>{esc(item['option'])}</h3>"]
        labels = {
            "new_trajectories": "新增轨迹",
            "new_api_usd": "新增API费用（美元）",
            "runtime": "预计时间",
            "gain": "获得的证据",
            "approval": "授权边界",
            "new_trajectories_upper_bound": "轨迹上限",
            "new_judge_slots_upper_bound": "评分槽上限",
            "matrix": "诊断矩阵",
            "precondition": "启动前提",
            "injection_boundary": "故障注入边界",
            "estimated_usd": "预计费用范围（美元）",
            "proposed_review_ceiling_usd": "建议费用复核阈值（美元）",
            "runtime_minutes_expected": "预计运行分钟",
            "runtime_review_threshold_minutes": "时间复核阈值（分钟）",
            "cost_basis": "估算依据",
            "stop": "停止条件",
        }
        for k, v in item.items():
            if k != "option":
                parts.append(f"<p><strong>{esc(labels[k])}</strong>：{esc(v)}</p>")
    parts += [
        "<p><strong>推荐先批准离线交付阶段。</strong>现在没有可直接执行且有充分依据的新增自然失败矩阵。若确需模型诊断，先把具体diff和两臂协议交给用户审批；至多4条只是规模与预算上限，不是自动执行承诺。人工故障注入只能明确作为诊断，不能包装成自然benchmark失败，也不能预先保证符合教师对案例的要求。</p>",
        "<h2>优先级与停止条件</h2>",
        table(
            ["优先级", "工作", "状态", "停止条件"],
            [[x["priority"], x["action"], x["status"], x["stop"]] for x in plan["priority_plan"]],
        ),
        "<h2>仅在另行批准后考虑</h2>",
        "<ul>" + "".join("<li>" + esc(x) + "</li>" for x in plan["optional_only"]) + "</ul>",
        "<p>旧PE增益、非退化与显著性门槛原样保留在历史研究协议中。课程停止条件是交付完整、证据可追踪、限制诚实，不是某一方法获胜。严格失败案例缺口未关闭时保持“未全部满足”。</p>",
    ]
    style = "body{font:16px/1.65 system-ui,sans-serif;background:#f5f7fb;color:#172333;margin:0}main{max-width:1240px;margin:32px auto;padding:32px;background:white;border-radius:14px}h1{font-size:30px}h2{margin-top:36px;border-bottom:1px solid #d8dfeb;padding-bottom:8px}.lead{color:#36516d}.notice{padding:18px;background:#fff4d8;border-left:4px solid #b77710}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:10px;border:1px solid #dce3ec;text-align:left;vertical-align:top}th{background:#edf2f8}a{color:#155bba}p{overflow-wrap:anywhere}@media(max-width:650px){main{margin:0;padding:16px;border-radius:0}h1{font-size:24px}td{min-width:120px}}"
    DEST.write_text(
        '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PE6203 课程完成计划</title><style>'
        + style
        + "</style></head><body><main>"
        + "".join(parts)
        + "</main></body></html>"
    )
    print(DEST)


if __name__ == "__main__":
    render()

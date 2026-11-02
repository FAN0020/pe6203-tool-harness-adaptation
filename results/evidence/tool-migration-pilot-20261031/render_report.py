"""Local research appendix; preserve main-course results and original scores."""

import html
import json
from pathlib import Path

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[2]


def main():
    v = json.loads((FOLDER / "trial-verification.json").read_text())
    q = json.loads((FOLDER / "quality-review.json").read_text())
    css = (
        (ROOT / "reports/budget-contract-results.html")
        .read_text()
        .split("<style>", 1)[1]
        .split("</style>", 1)[0]
    )
    parts = [
        f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PE6203 · 工具迁移对照</title><style>{css}</style><main>',
        "<h1>工具删除与迁移：task430 补充对照</h1>",
        '<p class="note">' + html.escape(q["headline_zh"]) + "</p>",
        "<p>2026-10-31 · 官方task430：解释声明式编程并展示SwiftUI代码。Early/Middle/Late × No Update/Full Rewrite/原Selective Patch/budget_feedback ×1次，共12条新轨迹、60个原judge评分槽。没有新增策略，也没有替换原133/235/283或覆盖27条主实验。</p>",
        "<h2>为何增加这个案例</h2><p>选择依据是发布版变化覆盖，不是模型得分。对四份官方mutation记录的离线检查找到三类工具删除：filesystem.read_file（现有任务已用替代工具）、LeetCode每日题入口（时变数据和其他服务）、Swiftipedia.search_symbols。task430明确列出search_symbols且仅需两个公开只读服务，因此首先检查它。task72同样涉及删除，但需PDF本地材料。实际目录确认Late移除search_symbols，文本查询迁入browse_module的query参数；Wikipedia两工具的契约三阶段均不变。</p>",
        "<p>完整选择依据、三阶段目录和12次公开只读工具探测见coverage-audit-20261031。没有读取官方答案或评分来选择新案例。该案例在已有开发结果之后选入，不能称预先保护的测试集。所需工具列表表示官方意图；是否实际调用，仍由agent决定。</p>",
        '<h2>独立复算</h2><div class="scroll"><table><tr><th>方法</th><th>正常完成</th><th>变化后完成</th><th>TF</th><th>PE</th><th>ECS总体SD</th><th>ECS样本SD</th></tr>',
    ]
    for name, s in v["summary"].items():
        parts.append(
            f"<tr><td>{name}</td><td>{s['completed']}/3</td><td>{s['post_change_completed']}/2</td><td>{s['TF']:.4f}</td><td>{s['PE']:.4f}</td><td>{s['ECS_population']:.4f}</td><td>{s['ECS_sample']:.4f}</td></tr>"
        )
    parts += [
        "</table></div><p>ECS = 三阶段TF均值 − 标准差。总体SD分母n=3，对应发布代码；样本SD分母n−1=2，对应论文附录口径。5个judge槽不是5次agent执行；高TF不证明正常结束。</p>",
        "<table><tr><th>Cell /阶段</th><th>方法</th><th>实际终态</th><th>TF</th><th>PE</th><th>Late旧工具调用</th><th>browse+query</th></tr>",
    ]
    for r in v["cells"]:
        stale = (
            "—" if r["removed_search_symbols_calls"] is None else r["removed_search_symbols_calls"]
        )
        parts.append(
            f"<tr><td>{r['cell_id']} / {r['stage']}</td><td>{r['strategy']}</td><td>{r['execution_status']}</td><td>{r['TF']}</td><td>{r['PE']}</td><td>{stale}</td><td>{r['browse_query_calls']}</td></tr>"
        )
    parts += ["</table><h2>恢复、保持与质量</h2>"]
    for line in q["findings_zh"]:
        parts.append("<p>" + html.escape(line) + "</p>")
    parts += [
        "<table><tr><th>方法</th><th>Middle−Early TF</th><th>Late−Early TF</th><th>更新tokens</th><th>更新秒</th><th>更新USD</th><th>Agent+judge USD</th></tr>"
    ]
    for name, s in v["summary"].items():
        parts.append(
            f"<tr><td>{name}</td><td>{s['TF_recovery_vs_own_Early']['middle']:+.3f}</td><td>{s['TF_recovery_vs_own_Early']['late']:+.3f}</td><td>{s['update_tokens']}</td><td>{s['update_seconds']:.3f}</td><td>{s['update_usd']:.8f}</td><td>{s['agent_judge_usd']}</td></tr>"
        )
    parts += [
        "</table><p>所有Early知识精确K0；Early输出差异属于随机波动，不能解释为适应收益。变化后相对Early的差值也受这个波动影响。这里的Wikipedia保持是同一任务中的未变化能力；原task235保持任务仍在原独立cohort中，不拼成新的匹配样本。</p>",
        "<h2>方法、公平性和限制</h2><p>base模型和快照不变，DigitalOcean唯一后端，无fallback；agent温度0、4096输出tokens、12轮、900秒，judge同一原协议、5个首次有效槽。预算反馈方法仍是原实现：精确差异更新受影响记录，保留不变记录，再加入当前必需参数、必要工作/结果复用、预算规则和适用冻结探针观察。本案例没有适用的旧探针观察，因此没有把新探测或任务答案注入知识。</p>",
        "<p>Full Rewrite重新构建完整目标目录，模型改写全部15条Middle/Late描述；schemas、routing、output schema和usage rules取目标元数据。并非每个字段由LLM自由生成。本次补上可选updater供应商固定和统一记账；不使用这些新设置的历史默认行为仍受回归测试保护，旧结果不改。</p>",
        "<p>本轮每格单次、一个补充任务；不能宣称显著性、稳定胜出或泛化。原公开MCP服务访问实时Wikipedia/Swiftipedia，内容和响应时间可能变化；完整观察与时间均归档。Swift检查包含全部围栏片段语法解析及12个核心CounterView、两项疑点的本机类型检查；不执行生成代码，不证明全部片段、iOS SDK兼容或运行正确。省略类型/回调的教学片段、API签名不自动当成完整app的编译错误。</p>",
        f"<p>全部请求已知费用US${v['known_usd']}（updater${v['updater_usd']}，预检${v['preflight_usd']}），未知费用{v['unknown_cost_items']}项；{v['api_requests']}个API请求，含更新的账本跨度{v['elapsed_seconds_including_updates']:.1f}秒。总费用和轨迹额度未设置上限，记录仍完整。</p>",
        '<h2>课程失败分析缺口</h2><p>No Update调用旧工具是stale-knowledge局部失败，不能改称Selective Patch under-update。既有受控缺参案例保留；先前相关evaluate规则对照仍不足以确认over-update。后续独立的<a href="routing-fault-results.html">两条路由诊断</a>已确认：无关Wikipedia路由误改导致局部读取失败，但agent补偿后仍完成任务。该受控guard消融不是自然方法失败；正常验证器会拒绝它。课程接受范围仍待TA确认，草稿未发送。后续诊断没有改动本轮12条结果。</p>',
        "<h2>逐格原评分与审阅</h2>",
    ]
    for row in q["cells"]:
        r = next(r for r in v["cells"] if r["cell_id"] == row["cell_id"])
        parts.append(
            f"<details><summary>{r['cell_id']} · {r['stage']} · {r['strategy']}</summary><p>TF {[x['TF'] for x in r['judge_values']]}；PE {[x['PE'] for x in r['judge_values']]}</p><p>{html.escape(row['review_zh'])}</p></details>"
        )
    parts += ["<h2>证据与复现</h2><p>"]
    for name in [
        "trial-verification.json",
        "quality-review.json",
        "artifact-checks.json",
        "typecheck-examples.json",
        "judge-audit.json",
        "coverage-touch.json",
        "runtime-environment.json",
        "raw-trial.tar.gz",
        "reproduction.json",
    ]:
        parts.append(
            f'<a href="../results/evidence/tool-migration-pilot-20261031/{name}">{name}</a> · '
        )
    parts += [
        '<a href="../results/evidence/coverage-audit-20261031/selection-audit.json">覆盖选择依据</a> · <a href="../results/evidence/routing-fault-proposal-20261031/plan.json">诊断执行前提案快照</a> · <a href="../HANDOVER.md">HANDOVER</a></p>',
        "<pre>python3 results/evidence/tool-migration-pilot-20261031/verify_trial.py</pre>",
        f"<p>归档SHA-256：{v['archive_sha256']}。冻结源码eae035e；课程主报告/PDF/Slides保持原有快照，新结果作为独立附录。</p></main></html>",
    ]
    (ROOT / "reports/tool-migration-results.html").write_text(
        "\n".join(part.rstrip() for part in parts) + "\n"
    )


if __name__ == "__main__":
    main()

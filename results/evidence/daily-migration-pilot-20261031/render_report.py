"""Render a separate research appendix from independently verified records."""

import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main():
    v = json.loads((HERE / "trial-verification.json").read_text())
    q = json.loads((HERE / "quality-review.json").read_text())
    css = (ROOT / "reports/budget-contract-results.html").read_text().split("<style>", 1)[1].split(
        "</style>", 1
    )[0]
    parts = [
        '<!doctype html><html lang="zh-CN"><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        f"<title>PE6203 · 每日题工具迁移</title><style>{css}</style><main>",
        "<h1>实时信息获取：task90 补充对照</h1>",
        '<p class="note">' + html.escape(q["headline_zh"]) + "</p>",
        "<p>2026-10-31 · 原任务要求查询青眼白龙的详情、取回图片，再告知当天LeetCode每日题。Early/Middle/Late × 四个已有方法 × 1次，共12条轨迹和60个原协议评分。没有开发新变体；原27条课程主实验及其他开发结果保持不变。</p>",
        "<h2>问题与设计</h2><p>这个案例要求取得实时每日题，减少凭模型已有知识完成回答的可能。Late删除get_daily_challenge，把入口迁入get_problem(daily=true)。选择来自官方变化记录与服务可用性核查，未根据本轮分数更换任务。该任务的公开历史答案曾在过宽读取中暴露，当前每日题也在服务探测中被读取；本轮明确为已暴露开发扩展，不能称保护测试。上述答案均未送入updater或agent。</p>",
        "<p>卡牌搜索在Middle/Late存在参数变化，不能把整个卡牌任务当作不变任务。get_card_by_id和get_card_image的契约三阶段不变，提供同任务内的保持证据；task235的不变任务实验仍单独报告。</p>",
        '<h2>原始评分独立复算</h2><div class="scroll"><table><tr><th>方法</th><th>正常结束</th><th>TF</th><th>PE</th><th>ECS 总体SD</th><th>ECS 样本SD</th></tr>',
    ]
    for method, s in v["summary"].items():
        parts.append(
            f"<tr><td>{method}</td><td>{s['completed']}/3</td><td>{s['TF']:.4f}</td><td>{s['PE']:.4f}</td><td>{s['ECS_population']:.4f}</td><td>{s['ECS_sample']:.4f}</td></tr>"
        )
    parts += [
        "</table></div><p>ECS＝三阶段TF均值−标准差。总体SD使用n＝3，样本SD使用n−1＝2，分别展示发布代码与论文附录口径。正常结束不等于所有用户要求都已满足；5份judge评分也不等于5次agent执行。</p>",
        "<table><tr><th>Cell / 阶段</th><th>方法</th><th>终态</th><th>TF</th><th>PE</th><th>Late旧入口调用</th><th>daily=true调用</th></tr>",
    ]
    for r in v["cells"]:
        stale = "—" if r["stale_daily_tool_calls"] is None else r["stale_daily_tool_calls"]
        parts.append(
            f"<tr><td>{r['cell_id']} / {r['stage']}</td><td>{r['strategy']}</td><td>{r['execution_status']}</td><td>{r['TF']}</td><td>{r['PE']}</td><td>{stale}</td><td>{r['daily_selector_calls']}</td></tr>"
        )
    parts += ["</table><h2>任务事实、恢复与保持</h2>"]
    for line in q["findings_zh"]:
        parts.append("<p>" + html.escape(line) + "</p>")
    parts.append(
        "<table><tr><th>方法</th><th>Middle−Early TF</th><th>Late−Early TF</th><th>更新tokens</th><th>更新秒</th><th>更新USD</th><th>Agent＋judge USD</th></tr>"
    )
    for method, s in v["summary"].items():
        parts.append(
            f"<tr><td>{method}</td><td>{s['TF_recovery_vs_own_Early']['middle']:+.3f}</td><td>{s['TF_recovery_vs_own_Early']['late']:+.3f}</td><td>{s['update_tokens']}</td><td>{s['update_seconds']:.3f}</td><td>{s['update_usd']:.8f}</td><td>{s['agent_judge_usd']}</td></tr>"
        )
    parts += [
        "</table><p>所有Early条件均精确K0；其输出差异不能归因于适应方法。恢复差值还受单次Early随机波动影响。此处指标不与其他cohort混算。</p>",
        "<h2>公平性与限制</h2><p>模型固定为deepseek/deepseek-v4.1-flash-1017，实际供应商固定DigitalOcean，无fallback；agent温度0、4096输出tokens、12轮、900秒。所有方法同任务、执行器和原judge协议。没有总费用/轨迹额度，但单次执行条件保持一致。调用中断、未知费用或评分错误不会被替换成成功结果。</p>",
        "<p>Selective Patch保留不变记录，只更新差异与依赖影响范围；budget_feedback继续使用已有的必要工作、证据复用和预算规则，没有加入本任务答案。Full Rewrite重建全部目标记录并用模型改写26条描述，schema、routing、output schema和usage rules取目标目录。Middle描述被改写为中文，Late保留混合语言；这是已披露的生成差异，不能把比较解释为纯更新范围消融。</p>",
        "<p>执行器原样保存MCP图片块，但把base64序列化为JSON文本传入模型；没有视觉理解或自动浏览器渲染。独立检查图片字节、卡牌ID、原始题目日期与最终事实，不能宣称已验证所有客户端里的展示。公网数据及每日题会变，未来重跑不保证返回完全相同内容。</p>",
        f"<p>本轮请求{v['api_requests']}次，已知费用US${v['known_usd']}，未知{v['unknown_cost_items']}项；其中更新${v['updater_usd']}、预检${v['preflight_usd']}。账本首尾跨度{v['elapsed_seconds_including_updates']:.1f}秒，包含更新与人工审查间隔，不等于纯API计算时间。费用来自响应，未另核账户账单。</p>",
        "<h2>失败分析与研究结论</h2>",
    ]
    for line in q["conclusions_zh"]:
        parts.append("<p>" + html.escape(line) + "</p>")
    parts += [
        '<p>课程失败案例仍需区分：<a href="routing-fault-results.html">无关路由受控诊断</a>确认局部损害，原受控缺参案例确认参数拒绝；均不是正常updater自然失误。课程是否接受guard消融和局部损害仍待TA确认。旧提示性案例与负结果完整保留。</p>',
        "<h2>逐格审阅与原始评分</h2>",
    ]
    for cell in q["cells"]:
        r = next(r for r in v["cells"] if r["cell_id"] == cell["cell_id"])
        parts.append(
            f"<details><summary>{r['cell_id']} · {r['stage']} · {r['strategy']}</summary><p>TF {[s['TF'] for s in r['judge_values']]}；PE {[s['PE'] for s in r['judge_values']]}</p><p>{html.escape(cell['review_zh'])}</p></details>"
        )
    parts += ["<h2>证据与复现</h2><p>"]
    for name in [
        "trial-verification.json", "quality-review.json", "artifact-checks.json",
        "judge-audit.json", "judge-context-audit.json", "coverage-touch.json", "postrun-freeze.json",
        "raw-trial.tar.gz", "raw-manifest.json", "source-manifest.json", "reproduction.json",
    ]:
        parts.append(f'<a href="../results/evidence/daily-migration-pilot-20261031/{name}">{name}</a> · ')
    parts += [
        '<a href="../results/evidence/daily-migration-readiness-20261031/readiness.json">服务核查</a> · <a href="../HANDOVER.md">HANDOVER</a></p>',
        "<pre>python3 results/evidence/daily-migration-pilot-20261031/verify_trial.py</pre>",
        f"<p>原始归档SHA-256：{v['archive_sha256']}。源码52abbcf；本附录未替换课程PDF和共享Slides。</p></main></html>",
    ]
    (ROOT / "reports/daily-migration-results.html").write_text(
        "\n".join(part.rstrip() for part in parts) + "\n"
    )


if __name__ == "__main__":
    main()

"""Render the completed negative pilot from offline evidence."""

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
        f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PE6203 · 证据边界规则试验</title><style>{css}</style><main>',
        "<h1>证据边界规则：未改善完成率与任务质量</h1>",
        '<p class="note"><strong>不晋级。</strong>新规则 evidence_scope 正常完成1/3，对照 budget_feedback 完成2/3；TF和PE均下降。候选更清楚地解释了部分验证结果，但数学答复仍截断，项目规划仍耗尽轮数。该负结果及原评分完整保留。</p>',
        "<p>2026-10-31 · 3 tasks × Late × 2 methods ×1次，6条新轨迹、30个评分。用户已取消总费用/轨迹额度；每轨迹相同12轮、4096输出tokens，固定模型、DigitalOcean供应商、解码、任务和原judge协议。不是三阶段课程主矩阵，不计算ECS。</p>",
        '<h2>独立复算</h2><div class="scroll"><table><tr><th>方法</th><th>正常完成</th><th>变化任务</th><th>保持任务</th><th>TF</th><th>PE</th><th>Agent+judge USD</th></tr>',
    ]
    for name, s in v["summary"].items():
        parts.append(
            f"<tr><td>{name}</td><td>{s['completed']}/3</td><td>{s['changed_completed']}/2</td><td>{s['retention_completed']}/1</td><td>{s['TF']:.4f}</td><td>{s['PE']:.4f}</td><td>{s['agent_judge_usd']}</td></tr>"
        )
    parts += [
        "</table></div><table><tr><th>Cell / task</th><th>方法</th><th>终态</th><th>TF</th><th>PE</th></tr>"
    ]
    for c in v["cells"]:
        parts.append(
            f"<tr><td>{c['cell_id']} / {c['task_id']}</td><td>{c['strategy']}</td><td>{c['execution_status']}</td><td>{c['TF']}</td><td>{c['PE']}</td></tr>"
        )
    parts += [
        "</table>",
        "<h2>变化、产物与失败证据</h2><p>候选只在已受影响记录末尾加入一条固定规则：区分观察、建议与未验证示例，避免无需求的大型实现及未经核实的汇总。133添加10条、283添加11条；235保持精确K0。移除这条新增规则后，知识与对照完全相同。更新0模型tokens、0调用、$0，全部57个冻结输入和知识锁复核通过。</p>",
        "<ul><li><strong>133候选：</strong>正确指出allow_variables=false仍接受x+1，且词法拒绝不等于完整安全验证。但扩写大量Python代码，末尾测试表被截断；代码的字面量和异常处理与说明也不完全一致。TF9.8、PE10不能代表正常完成或安全代码。</li>",
        "<li><strong>133对照：</strong>完整返回，两个代码块可解析；未重现上一轮的字典语法错误。安全性未验证，thread-pool timeout本身不能保证终止计算，Decimal转换也不能挽回已经发生的浮点舍入。不能把语法通过当作安全证明。</li>",
        "<li><strong>283两组：</strong>均保存了覆盖CSV、logs、visualization的任务并进行了实际拆分，但都没有最终答复。候选33条记录、26叶任务、340小时；对照42条、35叶任务、402小时。引用有效、依赖无环。候选10次创建遗漏必需workingDirectory，另有上游review_project_status实现错误；对照零工具错误也耗尽12轮。参数原本就在知识中，不自动归类为under-update；没有无关知识修改的证据，也不称over-update。</li>",
        "<li><strong>235保持：</strong>两组3个图表调用均保留数字、月份顺序和金额单位。对照把两次下降说成一次，并将年内变化叫同比；候选主要合计正确，季节性解释仍只是推测。未归档图像，渲染效果未知；相同K0下差异不能证明知识适应的作用。</li></ul>",
        "<h2>解释边界</h2><p>这是已暴露开发任务、每格单次的配对试验，不支持统计显著性、一般化或单一子句因果结论。两组固定相同供应商但仍有随机输出波动。没有把旧成功轨迹拼入本轮，也没有重跑低分。先前6/6候选完成的观察仍保留，本轮2/3说明不能据此承诺稳定完成。</p>",
        "<p>部分judge理由描述了不存在的最终答复，或错误称全部衍生数字一致；详见judge-audit.json。原TF/PE不修改、不重评。下一步先查明预算、规则重复和契约落实问题；不继续累加同类泛化提示，不启动81/108条自动扩展。</p>",
        f"<p>64个API请求（32 agent、30 judge、2预检），已知费用<strong>US${v['known_usd']}</strong>，预检${v['preflight_usd']}，未知费用0。账本跨度{v['elapsed_seconds']:.2f}秒。更新耗时合计{sum(s['update_seconds'] for s in v['summary'].values()):.3f}秒。以上是实测记录，不是费用上限。</p>",
        "<h2>逐格质量审阅与原分值</h2>",
    ]
    for row in q["cells"]:
        c = next(c for c in v["cells"] if c["cell_id"] == row["cell_id"])
        parts.append(
            f"<details><summary>{row['cell_id']} · {row['task_id']} · {row['strategy']}</summary><p>TF: {[x['TF'] for x in c['judge_values']]}；PE: {[x['PE'] for x in c['judge_values']]}</p><ul>"
        )
        for prop in row["properties"]:
            parts.append(
                "<li><b>"
                + prop["status"].upper()
                + "</b> · "
                + html.escape(prop["reason"])
                + "</li>"
            )
        parts.append("</ul></details>")
    parts += [
        "<h2>证据与复现</h2><p>课程27条主实验、PDF与Slides保持冻结。TA接受范围、已确认over-update及Full Rewrite解释缺口仍见HANDOVER，不能用本轮关闭。</p><p>"
    ]
    for name in [
        "trial-verification.json",
        "quality-review.json",
        "artifact-checks.json",
        "judge-audit.json",
        "reproduction.json",
        "raw-trial.tar.gz",
        "source-4221782.tar.gz",
    ]:
        parts.append(
            f'<a href="../results/evidence/evidence-scope-pilot-20261031/{name}">{name}</a> · '
        )
    parts += [
        f'</p><pre>python3 results/evidence/evidence-scope-pilot-20261031/verify_trial.py</pre><p>归档含265文件，包括完整console.log；SHA-256 {v["archive_sha256"]}。<a href="../HANDOVER.md">HANDOVER</a></p></main></html>'
    ]
    (ROOT / "reports/evidence-scope-results.html").write_text("\n".join(parts) + "\n")


if __name__ == "__main__":
    main()

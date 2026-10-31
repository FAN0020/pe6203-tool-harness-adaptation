"""Render the controlled failure mechanism, without rewriting historical evidence."""

import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main():
    data = json.loads((HERE / "trial-verification.json").read_text())
    review = json.loads((HERE / "evidence-review.json").read_text())
    css = (
        (ROOT / "reports/tool-migration-results.html")
        .read_text()
        .split("<style>")[1]
        .split("</style>")[0]
    )
    body = [
        f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PE6203 · 无关路由故障诊断</title><style>{css}</style><main>',
        "<h1>无关路由误改：受控 over-update 机制</h1>",
        '<p class="note">已确认：无关知识的一处路由误改损害原本正常的文章读取。两组 agent 均完成任务；原方法验证器能拒绝该误改。不能称为自然 updater 失败，也不能把局部损害写成整个任务失败。</p>',
        "<p>2026-10-31 · task430 / Late · 两个新条件各执行一次，10个原judge评分槽，另有2次同参数公开只读工具重放。基于已完成的工具迁移试验；没有新增策略、改任务、改标签或部署。</p>",
        "<h2>单字段干预与因果链</h2>",
        "<pre>真实环境变化：Swiftipedia.search_symbols 被删除 → browse_module.query\n未变化知识：Wikipedia.readArticle 的名称、schema、description、usage rules、routing\n\n唯一注入：wikipedia-mcp::readArticle.routing.tool_name\n控制条件：readArticle\n故障条件：read_article\n\n模型看到的工具名称、描述、schema完全相同；只有派发路由不同。</pre>",
        "<p>该拼写没有对 Swift 查询迁移的依赖。相同别名与 pageId=210648，正确路由返回41,962字符文章；错误路由返回 <code>Tool read_article not found</code>。在完整 agent 轨迹中，故障条件第2、3轮以相同title/pageId调用读工具，两次均报此错；控制条件第2轮成功。正常scope/identity验证器会报告三项违规，本实验仅从研究重放入口载入故障快照，没有修改正式验证器。</p>",
        "<h2>原评分、实际完成与费用</h2><table><tr><th>条件</th><th>终态</th><th>TF</th><th>PE</th><th>工具调用/错误</th><th>agent轮数</th><th>API USD</th></tr>",
    ]
    for row in data["cells"]:
        charge = sum(float(v) for v in row["cost_usd"].values())
        body.append(
            f"<tr><td>{'故障' if row['condition'] == 'fault' else '控制'} ({row['id']})</td><td>{row['execution_status']}</td><td>{row['TF']:.1f}</td><td>{row['PE']:.1f}</td><td>{row['tool_calls']}/{row['structured_tool_errors']}</td><td>{row['agent_rounds']}</td><td>{charge:.9f}</td></tr>"
        )
    body += [
        f"</table><p>19请求＝9 agent＋10 judge，全部实际DigitalOcean，同一模型、温度0、4096输出tokens、12轮和原5槽评分协议；更新/预检模型调用0。费用US${data['known_usd']}，未知0，执行和评分窗口{data['elapsed_seconds']:.2f}秒；无总费用额度。Late单阶段诊断不计算ECS。</p>",
        "<p>故障组TF原值：[10,9,9,10,10]，平均9.6；PE：[8,5,5,7,5]，平均6.0。控制组TF五个10；PE：[7,8,5,7,7]，平均6.8。数值从原始judge响应独立复算；不改分或补评分。</p>",
        "<h2>结论强度</h2><table><tr><th>命题</th><th>分类</th><th>理由</th></tr>",
        "<tr><td>无关知识改动损害读操作</td><td>confirmed（受控局部机制）</td><td>唯一字段差异、同输入重放、两条轨迹均实际触达该路由。</td></tr>",
        "<tr><td>整个任务失败</td><td>contradicted</td><td>故障组如实披露读失败，改用搜索摘要并提供说明与SwiftUI例子；两组均正常结束。</td></tr>",
        "<tr><td>误改造成TF−0.4/PE−0.8</td><td>suggestive</td><td>只是一对随机执行；第一轮查询在触达错误前已不同；judge存在明显理由错误。两组总调用均7次。</td></tr>",
        "<tr><td>正常budget_feedback自然产生此错误</td><td>contradicted / 未观察到</td><td>正常验证器能拒绝故障快照；这是显式guard消融。</td></tr>",
        "</table><p>两组核心CounterView代码与上一轮已通过类型检查的片段逐字一致；复用该检查仅证明此片段，不证明所有示例或app运行。故障组答案的“无需管理任何状态”等绝对表述仍有限制。</p>",
        "<h2>评分问题原样保留</h2><p>故障组slot1/4把已由batch返回的Form、Picker、Slider、NavigationStack等资料说成缺失；slot2/3把两次总调用计成两次重试，并在“0/2缺陷”的TF理由下给9分；slot5引用答案中没有的Date示例。完整证据见evidence-review.json。没有据此伪造修正分数。</p>",
        '<p class="note">后续审计更正解释：原始batch确实返回上述资料，但官方评分格式化器只保留每条工具消息前1000字符；重建已确认这些关键字未进入judge实际观察。因此，资料缺失批评应归为协议证据可见性问题，不能说judge漏读了已展示文本。重试计数等独立问题仍成立。见<a href="../results/evidence/daily-migration-pilot-20261031/judge-context-audit.json">逐观察重建证据</a>；原评分和旧审计快照均保留。</p>',
        "<h2>与课程既有失败案例的关系</h2><table><tr><th>案例</th><th>现有证据</th><th>限制</th></tr>",
        "<tr><td>旧under-update：删allow_variables</td><td>受控缺参，8次拒绝对0次，局部机制confirmed。</td><td>未证明原updater遗漏；控制PE反而低0.2，原分保留。</td></tr>",
        "<tr><td>旧over候选：evaluate usage rule</td><td>22对4次调用、截断对完成，仅suggestive。</td><td>规则与变化validator相关，不能叫无关知识损害。</td></tr>",
        "<tr><td>6条旧chart回退对照</td><td>负结果继续保留。</td><td>不能被本次阳性的局部机制覆盖或改写。</td></tr>",
        "<tr><td>本次Wikipedia路由误改</td><td>新增一条有直接证据的无关知识损害轨迹。</td><td>人工注入、验证器消融、agent补偿成功；课程是否接受仍待确认。</td></tr>",
        "</table><p>Brief §4.2要求“the patch changes unrelated knowledge and damages previously working behavior”。它没有要求必须自然发生，也没有明确规定必须让整个任务无法完成。本例符合受控局部损害的技术机制，但不能默认满足教师对方法失败分析的预期。原27条主表、旧诊断和历史负结果均未改变；本附录尚未合入冻结PDF及共享Slides。</p>",
        "<h2>TA问题草稿（未发送）</h2><p>"
        + html.escape(review["ta_question_draft_not_sent"])
        + "</p>",
        "<h2>复现与审阅</h2><p>",
    ]
    for name in (
        "protocol.json",
        "trial-verification.json",
        "evidence-review.json",
        "raw-trial.tar.gz",
        "raw-manifest.json",
        "reproduction.json",
    ):
        body.append(
            f'<a href="../results/evidence/routing-fault-check-20261031/{name}">{name}</a> ·'
        )
    body += [
        '<a href="../results/evidence/routing-fault-proposal-20261031/scope-guard-check.json">验证器拒绝证据</a> · <a href="../submission/diagnostics-20261031/index.html">旧诊断快照</a> · <a href="tool-migration-results.html">12条工具迁移对照</a> · <a href="../HANDOVER.md">HANDOVER</a></p>',
        "<pre>python3 results/evidence/routing-fault-check-20261031/verify_trial.py</pre>",
        f"<p>87文件原始包SHA-256：{data['archive_sha256']}。执行器冻结37dd2d0，底层runtime与eae035e完全相同。离线核查不调用模型。当前研究目标仍未完成：本实验解释失败机制，并没有开发或证明一个全面改善完成率与任务质量的新策略。</p></main></html>",
    ]
    (ROOT / "reports/routing-fault-results.html").write_text(
        "\n".join(b.rstrip() for b in body) + "\n"
    )


if __name__ == "__main__":
    main()

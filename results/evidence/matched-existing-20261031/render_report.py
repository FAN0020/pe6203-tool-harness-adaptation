"""Render the evidence appendix locally; no external services or model calls."""

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
        f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PE6203 · 固定供应商补充对照</title><style>{css}</style><main>'
    ]
    parts += [
        "<h1>补充对照：完成率与 TF 上升，质量检查仍未通过</h1>",
        '<p class="note"><strong>观察到了收益，尚不晋级。</strong>9 条新增轨迹与3条明确溯源的既有轨迹组成12格描述性分析。budget_feedback 完成6/6，原 Selective Patch 完成2/6；TF、PE均较高。但候选数学代码无效、部分汇总失实，不能宣称全面质量改善、稳定胜出或课程验证已完成。</p>',
        "<p>2026-10-31 · 用户最新授权取消总费用与总轨迹额度。每条执行仍固定同一模型、解码、12轮与4096输出tokens，以保持比较条件。此轮使用已有方法，没有开发新候选，没有修改旧评分、课程27条主结果、PDF或Slides，也没有外部部署。</p>",
        '<h2>独立复算</h2><div class="scroll"><table><tr><th>12格合并分析</th><th>原 Selective Patch</th><th>budget_feedback</th></tr>',
    ]
    a, b = v["summary"]["selective_patch"], v["summary"]["budget_feedback"]
    for name, x, y in [
        ("正常完成", f"{a['completed']}/6", f"{b['completed']}/6"),
        ("变化任务完成", f"{a['changed_completed']}/4", f"{b['changed_completed']}/4"),
        ("不变任务完成", f"{a['retention_completed']}/2", f"{b['retention_completed']}/2"),
        ("平均TF", f"{a['TF']:.4f}", f"{b['TF']:.4f}"),
        ("平均PE", f"{a['PE']:.4f}", f"{b['PE']:.4f}"),
        ("Agent+judge已知费用", a["agent_and_judge_usd"], b["agent_and_judge_usd"]),
        ("知识更新秒数", f"{a['update_seconds']:.3f}", f"{b['update_seconds']:.3f}"),
        ("更新模型tokens / 费用", "0 / $0", "0 / $0"),
    ]:
        parts.append(f"<tr><td>{name}</td><td>{x}</td><td>{y}</td></tr>")
    parts += [
        "</table></div><p>只有 Middle/Late，<strong>不计算新ECS</strong>。变化任务恢复在这里表示变更后任务的实际完成表现，并非已测得相对Early的恢复差值；不变任务完成2/2也不等于答案无错误。费用比较不含共享预检，跨批次缓存/请求差异限制成本归因。</p>",
        '<div class="scroll"><table><tr><th>Task /阶段</th><th>方法</th><th>来源</th><th>执行状态</th><th>TF</th><th>PE</th></tr>',
    ]
    for r in sorted(v["cells"], key=lambda r: (r["task_id"], r["stage"], r["strategy"])):
        source = (
            "本轮 " + r["cell_id"]
            if r["block"] == "new_extension"
            else "复用旧六条试验 " + r["cell_id"]
        )
        parts.append(
            f"<tr><td>{r['task_id']} / {r['stage']}</td><td>{r['strategy']}</td><td>{source}</td><td>{r['execution_status']}</td><td>{r['TF']}</td><td>{r['PE']}</td></tr>"
        )
    parts += [
        "</table></div>",
        "<h2>最重要的成功与失败</h2><ul>",
        "<li><strong>真实产物改善：task283 Middle。</strong>候选保存36条记录=4个里程碑+32个具体叶任务；73/69/104/110小时合计356，与答案一致。它把两个过宽任务缩小范围，并新增四个具体任务承接工作；四个容器警告仍如实披露。同批次原Patch在M3分解期间耗尽轮数，M4–M8没有子任务。该配对支持本条件的完成与产物改善；不证明普遍因果效应。</li>",
        "<li><strong>候选完成≠代码有效：task133 Late。</strong>答案完整返回，但Python字典中<code>ast.Sub</code>缺少值，离线AST解析报SyntaxError；字符过滤还会拒绝其合法测试<code>sqrt(16)</code>。AST遍历不能检测原始括号层数。没有执行生成代码，也没有把安全性记为已验证。</li>",
        "<li><strong>保持任务的汇总错误。</strong>两组图表调用均保留原数字、顺序和金额单位，但候选Late年度合计24.2应为25.4，江苏服装4.5应为3.6；原Patch Middle合计23.4也错误。Late两组都误判最大地区差距。两组知识都是精确K0，不能归因于适应机制。没有归档图像，视觉质量仍未知。</li>",
        "<li><strong>旧成功轨迹的错误照样保留。</strong>复用的候选283 Late把M3的79小时说成67，并声称出现了轨迹中不存在的创建错误；复用的133 Middle示例安全完整性仍未知。不能因这些轨迹完成而忽略反证。</li>",
        "<li><strong>原Patch的执行失败。</strong>两个133条件输出截断，两个283条件耗尽轮数。283 Late即使无最终答复仍获TF10；283 Middle只完成部分任务拆分。其Late数学示例还引用不存在的<code>ast.Comprehension</code>。完成状态、judge分数和质量结论分别记录。</li></ul>",
        "<h2>公平性与解释边界</h2><p>两组新调用均为DeepSeek v4.1 Flash指定快照、DigitalOcean端点，无fallback；温度0、12轮、4096输出tokens、900秒执行与120秒请求超时，原任务及5个评分槽固定。9份新知识均与原12条研究归档精确相同；没有新增探测或updater模型调用。新执行使用不含方法名的工作目录。</p>",
        "<p><strong>这是两批次、部分回顾性的分析。</strong>候选133 Middle、235 Middle和283 Late复用前一轮；来源在新结果产生前已写入协议，但前一轮结果当时已可见。总协议哈希不同，因为本轮移除了费用/单价准入上限并换用了账本路径；不能称为所有设置逐字相同。原judge实现、评分规则、模型及解码设置不变。每格仅1次执行，温度0也不保证确定性；供应商内部权重和运行条件不可控。</p>",
        "<p>此前完整12条研究中两组均4/6完成，候选TF10、PE8.8，原PatchTF9.9667、PE9.0；那些结果仍有效。本轮不能覆盖旧结果，也不能把当前较好的候选批次作为无偏总体估计。全部候选/失败保留，不重跑低分。</p>",
        "<h2>Judge、运行问题与成本</h2><p>独立复算直接读取原始评分响应，逐槽核对TF/PE，再从stop、exceeded和finish_reason确定完成状态。发现的judge理由错误单列：例如图表年度合计错误仍被称为全部数字匹配；283 Middle空最终答案被描述为存在最终回答；候选133 Late独立探测被误称重复。<strong>原分数没有修改，也没有重评。</strong></p>",
        "<p>283 Middle原Patch触发的JSONRPC警告来自上游工具将迁移信息用console.log写入stdio。轨迹继续执行；另有一次虚构父ID导致工具拒绝。没有证据说明迁移警告造成轮数耗尽。完整控制台流未另存，原始工具观察及持久化状态已保存；此限制在运行观察文件中披露。</p>",
        f"<p>本轮新增9轨迹、45有效评分、2预检，共<strong>{v['new_api_requests']}个API请求</strong>。新增已知费用<strong>US${v['new_known_usd']}</strong>（预检${v['new_preflight_usd']}），未知费用0；账本时长{v['new_elapsed_seconds']:.1f}秒，约{v['new_elapsed_seconds'] / 60:.2f}分钟。复用3条没有重复执行或收费。历史费用预估是估算，不是上限；实际按账本披露。</p>",
        "<h2>课程状态与下一步</h2><p>课程27条主实验仍是原正式结果；本研究尚无Early及匹配的No Update/Full Rewrite全阶段比较，不替代主表。Under-update受控案例是否合格、已确认的无关知识over-update证据、Full Rewrite解释等仍见HANDOVER中的TA问题草稿；没有发送消息。</p>",
        "<p><strong>本轮不晋级、不启动81/108条确认。</strong>已有完成率及TF正向信号，下一步应先围绕变化工具的“证据能支持什么结论”设计单一、可审计的修正，并检验完整回答是否含无效代码或无依据总结；保持任务错误需要作为相同K0下的波动记录，不能为修复它而偷改无关知识。继续研究不再以总额度为停止条件，但必须由具体假说和缺口驱动。</p>",
        '<h2>复现与证据</h2><p><a href="../results/evidence/matched-existing-20261031/trial-verification.json">独立复算</a> · <a href="../results/evidence/matched-existing-20261031/quality-review.json">逐属性审阅</a> · <a href="../results/evidence/matched-existing-20261031/artifact-checks.json">产物事实</a> · <a href="../results/evidence/matched-existing-20261031/judge-audit.json">Judge问题</a> · <a href="../results/evidence/matched-existing-20261031/runtime-observations.json">运行观察</a> · <a href="../results/evidence/matched-existing-20261031/raw-trial.tar.gz">382个原始文件</a> · <a href="../results/evidence/matched-existing-20261031/source-f896388.tar.gz">冻结源码</a> · <a href="../HANDOVER.md">交接</a></p>',
        "<pre><code>python3 results/evidence/matched-existing-20261031/verify_trial.py\npython3 results/evidence/matched-existing-20261031/check_artifacts.py</code></pre>",
        f"<p class=small>原始归档SHA-256：{v['new_archive_sha256']}。源码提交f896388；详细执行命令及环境信息见reproduction.json。离线复算不需API key，不启动模型。</p>",
        "<h2>逐格原始评分与质量审阅</h2>",
    ]
    for row in sorted(q["cells"], key=lambda r: (r["task_id"], r["stage"], r["strategy"])):
        score = next(
            r for r in v["cells"] if (r["block"], r["cell_id"]) == (row["block"], row["cell_id"])
        )
        parts.append(
            f"<details><summary>{row['task_id']} · {row['stage']} · {row['strategy']} · {row['block']} / {row['cell_id']}</summary>"
        )
        parts.append(
            "<p>五个TF："
            + str([r["TF"] for r in score["judge_values"]])
            + "；五个PE："
            + str([r["PE"] for r in score["judge_values"]])
            + "</p><ol>"
        )
        for prop in row["properties"]:
            parts.append(
                "<li><b>"
                + html.escape(prop["status"].upper())
                + "</b> · "
                + html.escape(prop["reason"])
                + "</li>"
            )
        parts.append("</ol></details>")
    parts.append("</main></html>")
    (ROOT / "reports/matched-existing-results.html").write_text("\n".join(parts) + "\n")


if __name__ == "__main__":
    main()

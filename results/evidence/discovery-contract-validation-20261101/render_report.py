"""Render the independently verified results without changing scores or reviews."""

import html
import json
from collections import Counter
from pathlib import Path


def esc(value):
    return html.escape(str(value))


def table(headers, rows):
    head = "".join(f"<th>{esc(x)}</th>" for x in headers)
    body = "".join("<tr>" + "".join(f"<td>{esc(x)}</td>" for x in row) + "</tr>" for row in rows)
    return f'<div class="scroll"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def main():
    folder = Path(__file__).resolve().parent
    root = folder.parents[2]
    v = json.loads((folder / "verification.json").read_text())
    assert v["verified"] and len(v["rows"]) == 36
    cost = json.loads((folder / "update-costs.json").read_text())
    review = json.loads((folder / "quality-review.json").read_text())
    verdict = "通过事前双重改善验证" if v["validation_gate"] else "未通过：淘汰本候选，研究 Goal 仍未完成"
    sections = []
    for block, data in v["blocks"].items():
        rows = []
        for arm, scopes in data["summary"].items():
            for scope in ("changed", "retention"):
                s = scopes[scope]
                rows.append([arm, scope, s["n"], f'{s["completed"]}/{s["n"]}',
                             f'{s["core_pass"]}/{s["n"]}', f'{s["TF"]:.3f}', f'{s["PE"]:.3f}'])
        sections.append(f'<h2>独立验证批次 {esc(block)}</h2>' + table(
            ["方法", "范围", "n", "正常完成", "全部质量属性通过", "TF", "PE"], rows))
        sections.append(table(["事前条件", "结果"], data["checks"].items()))
    prop_rows = []
    for arm in ("selective_patch", "discovery_contract"):
        selected = [r for r in v["rows"] if r["strategy"] == arm]
        props = sorted({p for r in selected for p in r["properties"]})
        for prop in props:
            counts = Counter(r["properties"][prop] for r in selected if prop in r["properties"])
            prop_rows.append([arm, prop, counts["pass"], counts["fail"], counts["unknown"]])
    sections.append('<h2>逐属性结果</h2>' + table(["方法", "属性", "pass", "fail", "unknown"], prop_rows))
    act = v["source_comparability"]["mechanism_activation"]
    activation = []
    for arm in ("selective_patch", "discovery_contract"):
        rows = [r for r in act if r["strategy"] == arm]
        activation.append([arm, len(rows), sum(r["discovery_calls"] > 0 for r in rows),
                           sum(r["discovery_calls"] for r in rows)])
    sections.append('<h2>机制与来源</h2>' + table(
        ["方法", "变化单元", "调用故障发现工具的单元", "故障发现工具调用数"], activation))
    sections.append('<p>' + esc(v["source_comparability"]["interpretation"]) + '</p><p>'
                    + esc(v["source_comparability"]["limits"]) + '</p>')
    cell_rows = [[r["block"], r["repeat_index"], r["review_id"], r["task_id"], r["stage"],
                  r["strategy"], r["execution_status"], r["core_pass"], r["TF"], r["PE"]]
                 for r in sorted(v["rows"], key=lambda r: (r["repeat_index"], r["task_id"], r["stage"], r["strategy"]))]
    sections.append('<h2>全部 36 个单元</h2>' + table(
        ["批次", "重复索引", "盲号", "任务", "阶段", "方法", "完成状态", "core", "TF", "PE"], cell_rows))
    base = '../results/evidence/discovery-contract-validation-20261101/'
    links = [('verification.json', '全部离线复算结果'), ('quality-review.json', '原盲审与逐属性证据'),
             ('source-comparability.json', '来源与机制核对'), ('raw-manifest.json', '原始文件哈希'),
             ('raw-trial.tar.gz', '完整原始证据'), ('source-manifest.json', '源码输入哈希'),
             ('source-validation.tar.gz', '执行前源码输入快照'), ('review-freeze.json', '36份盲审冻结'),
             ('verify_trial.py', '独立离线复算脚本')]
    sections.append('<h2>证据与复现</h2><ul>' + ''.join(
        f'<li><a href="{base}{name}">{title}</a></li>' for name, title in links) + '</ul>')
    sections.append('<p>离线复算：<code>python3 results/evidence/discovery-contract-validation-20261101/verify_trial.py</code>。'
                    '不调用模型、不重启原实验。盲审冻结提交：<code>' + esc(v['review_freeze_commit']) + '</code>。</p>')
    report = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Discovery Contract · 两批独立验证</title><style>
body{{font:16px/1.65 system-ui,sans-serif;color:#172132;background:#f4f6fa;margin:0}}main{{max-width:1160px;margin:auto;padding:32px 24px 64px}}
h1{{font-size:30px;line-height:1.3}}h2{{font-size:21px;margin-top:32px}}.verdict{{padding:16px 20px;background:#fff2da;border-left:5px solid #a85a00;font-weight:700}}
.scroll{{overflow:auto;background:white;margin:16px 0;border:1px solid #d4dbe5}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{text-align:left;padding:9px 12px;border-bottom:1px solid #e1e6ed;vertical-align:top}}th{{background:#eaf0f7;white-space:nowrap}}a{{color:#075aa6}}code{{overflow-wrap:anywhere}}p{{max-width:1000px}}
</style><main><h1>Discovery Contract：两批独立验证</h1><p class="verdict">{esc(verdict)}</p>
<p>仅替换 Middle/Late Context7 的两处失实发现接口说明，其余知识逐字保留原 Selective Patch；保持任务235两组均为相同 K0。原生工具、模型、供应商和单次预算不变。论文任务87按四项实际产物属性检查，图表任务235按数值与摘要准确性检查；unknown 不计通过。</p>
<p>A/B各18条，分别要求变化任务正常完成数与完整质量通过数同时严格提高，TF不下降；保持任务完成、质量、TF均不下降。开发试点不与验证合并计算。完成全部36条后才揭示方法与分数，同一协调者盲审，不是独立人工审阅。模型无seed保证，重复索引仅标记新独立请求。</p>
{''.join(sections)}
<h2>成本与限制</h2><p>{v['api_requests']}次API请求（agent {v['agent_requests']}、judge {v['judge_requests']}、preflight 2）；{v['judge_slots']}个评分槽完整。原始账本总费用 ${esc(v['known_usd'])}，未知费用项 {v['unknown_cost_items']}；账本请求时间跨度 {v['elapsed_seconds']:.3f} 秒。确定性知识更新模型调用/令牌/美元均为 {cost['model_calls']}/{cost['tokens']}/{cost['usd']}；ECS为null，本局部日程不估计该指标。</p>
<p>归档原始文件 {v['file_count']} 个、源码输入 {v['source_files']} 个；计划输入 {v['plan_inputs_verified']} 项及补充输入 {v['extra_inputs_verified']} 项哈希均已核验。所有失败、unknown、原评分及产物原样保留。外部检索内容并非完全受控；图表视觉渲染未知且未事后加入门槛。结果仅适用于暴露过的固定任务及当前执行环境，不支持未见任务总体、因果或统计显著性主张。课程全量基线、恢复、保持、ECS及最终展示材料仍需在整体目标达到后统一核对。</p>
</main></html>'''
    assert len(review['reviews']) == 36
    path = root / 'reports/discovery-contract-validation.html'
    path.write_text(report)
    print(path)


if __name__ == '__main__':
    main()

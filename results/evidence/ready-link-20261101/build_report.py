"""Render this development decision from audited evidence, not hand-copied scores."""
import html
import json
from pathlib import Path
E=Path(__file__).resolve().parent
ROOT=E.parents[2]
d=json.loads((E/'decision.json').read_text())
i=json.loads((E/'interpretation.json').read_text())
a=json.loads((E/'accounting-comparison.json').read_text())
esc=html.escape
def link(name,label):return f'<a href="../results/evidence/ready-link-20261101/{esc(name)}">{esc(label)}</a>'
metric_rows=[]
for group,label in [('project','283项目子集'),('changed','原冻结变化子集133+283'),('retention','235不变任务')]:
    for method in ['selective_patch','ready_link']:
        m=d['metrics'][method][group]
        metric_rows.append(f'<tr><td>{label}</td><td>{method}</td><td>{m["completed"]}/{m["n"]}</td><td>{m["core_pass"]}/{m["n"]}</td><td>{m["TF"]:.2f}</td><td>{m["PE"]:.2f}</td></tr>')
rows=[]
for r in d['rows']:
    rows.append(f'<tr><td>{r["review_id"]}</td><td>{r["task_id"]} {r["stage"]}</td><td>{r["strategy"]}</td><td>{r["execution_status"]}</td><td>{r["core_pass"]}</td><td>{r["TF"]:.2f}</td><td>{r["PE"]:.2f}</td><td>{r["rounds"]}</td><td>{r["tool_calls"]}</td></tr>')
paragraphs=''.join(f'<p><strong>{esc(k)}</strong>：{esc(v)}</p>' for k,v in i['findings_zh'].items())
page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PE6203 · Ready Link 原题开发</title><style>
body{{font:16px/1.7 system-ui;margin:40px auto;padding:0 24px;max-width:1120px;color:#172430;background:#fafbfc}}h1{{font-size:30px}}h2{{font-size:21px;margin-top:32px}}a{{color:#095aa6}}table{{border-collapse:collapse;width:100%;font-size:14px;background:white}}th,td{{padding:9px 11px;text-align:left;border-bottom:1px solid #d7e0e8}}th{{background:#eaf0f6}}.scroll{{overflow-x:auto}}.decision{{padding:18px 22px;border-left:5px solid #b15900;background:#fff5e7}}code{{background:#edf1f5}}.muted{{font-size:14px;color:#4e5b69}}
</style><body><p class="muted">PE6203 · 同一完整研究 Goal · 2026-11-01 · 原 benchmark 开发，非正式验证</p>
<h1>{esc(i['title_zh'])}</h1><div class="decision">{esc(i['decision_zh'])}</div>
<h2>失败证据与具体机制</h2><p>旧 dependency_cut 原题项目运行都耗尽12轮，23条有依赖记录全部在创建后补链接。受控链式诊断的4次SP运行已保存正确状态却没有最终答复。它们支持调查创建/链接的执行负担，但停止字段不能证明根因。观察覆盖路线的后续诊断没有支持稳定减少读取，因此本轮回到写入依赖图。</p>
<p>新规则只把尚未取得完整依赖ID的记录留作待补；已有全部ID时在创建调用内写入完整依赖。一旦待补记录自身与全部依赖的ID就绪，补链接可与后续创建交错执行，取消全局“建完再链接”屏障。它改变写入选择和依赖图；没有增加actor调度器或预算。所有字段、工作范围和最终准确交付仍须保留。</p>
<h2>原始论文、作者源码与原生检查</h2><p><a href="https://arxiv.org/html/2312.04511v3">LLMCompiler v3</a>使用规划器产生依赖图，由任务获取单元在前置任务完成后释放操作。
作者<a href="https://github.com/SqueezeAILab/LLMCompiler/blob/a00c9d35507507da70e8c637eee64efc8c1857ae/src/llm_compiler/task_fetching_unit.py#L100">固定源码 a00c9d3，第100–133行</a>检查已完成依赖、替换参数并调度就绪任务。本项目只借鉴就绪释放；条件内联写入是对原生API的适配，没有引入作者规划器、并行执行器、重规划、示例或任务轨迹。</p>
<p>三类通用8节点图 × 两阶段 × 三种写入路径，共18个最终状态全部字段等价，6次错误ID更新拒绝且状态不变。232次原生调用、18次catalog、模型费用0。相对旧全延期规则，新规则的正常调用数16→10、17→14、14→12；理论轮次8→7、8→8、8→7。直接写入在无需等待的图上可同样高效，不能声称新规则普遍最优，也不能把静态轮次当成actor实测收益。</p>
<h2>冻结与验收</h2><p>原生冻结<code>0cc2005</code>，精确知识/188个源文件及原题计划冻结<code>a95ad2d</code>。76项针对性测试通过。10个开发单元涵盖133M/L、283M/L和保持235L，两组各一次。只有实际变化的create_project描述不同；133/235知识与SP逐字节一致。更新器模型调用0，证书只含无题目原生事实。</p>
<p>原模型DeepSeek v4.1 Flash、DigitalOcean、温度0、4096单次token、12轮、工具与五槽评分协议均保持不变。项目子集和完整变化子集都须正常完成与全部产物属性严格提升、TF不下降，并保持235能力。开发通过才运行两批各30个新执行，知识跨批不改。任务族已暴露；独立执行不代表未见任务或供应商统计独立。</p>
<h2>实际结果</h2><div class="scroll"><table><tr><th>范围</th><th>方法</th><th>正常完成</th><th>完整质量</th><th>TF</th><th>PE</th></tr>{''.join(metric_rows)}</table></div>
<p>完整质量要求每个冻结属性通过，unknown不算pass。原TF/PE保留；ECS因缺匹配三阶段为null。不能用正确保存状态、高官方分数或局部收益替代完整双提升。</p>
<div class="scroll"><table><tr><th>审查</th><th>任务</th><th>方法</th><th>状态</th><th>完整质量</th><th>TF</th><th>PE</th><th>轮次</th><th>工具数</th></tr>{''.join(rows)}</table></div>
<h2>事实、观察与未排除解释</h2>{paragraphs}
<h2>费用、复现与交付缺口</h2><p>{d['api_requests']}笔请求，已知费用<strong>USD {d['known_usd']}</strong>，新未知费用{d['unknown_cost_items']}。主key累计{a['key_cumulative_usage_usd']}、剩余{a['key_remaining_usd']}，均为只读接口快照；累计量不能结算旧factorial的单笔超时未知费用。备用变量已配置，本轮未启用。独立ledger无新增总额度上限。</p>
<p>{d['raw_files']}个原始文件、{d['source_files']}个冻结源文件、50原评分槽及知识/产物/账本哈希离线核验。全部产物审查先于官方评分和方法映射揭示。同协调者、非严格方法盲评，每条件只有一次actor执行；五槽评分不是五次actor重复。</p>
<p>保留历史NU/FR与E/M/L课程基线，不冒充同期对照。最终综合报告、复现包、展示和排练仍需完成；本页仅完成本轮研究链。完整Goal仍未完成。</p>
<p>{link('research-decision.json','约束、候选与审查意见')} · {link('native-decision.json','原生比较')} · {link('decision.json','完整结果')} · {link('interpretation.json','解释与下一步')} · {link('review-freeze.json','产物审查冻结')} · {link('behavior-projection.json','可见行为')} · {link('accounting-comparison.json','费用')} · {link('reproduction.txt','复现')}</p></body></html>'''
out=ROOT/'reports/ready-link-development.html';out.write_text(page);print(out)

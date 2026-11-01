"""Report the separately frozen diagnostic without redefining original success."""
import html
import json
from pathlib import Path
E = Path(__file__).resolve().parent
ROOT = E.parents[2]
d = json.loads((E / 'decision.json').read_text())
interpretation = json.loads((E / 'interpretation.json').read_text())
groups = []
for g in d['groups']:
    groups.append(f'<tr><td>{g["task_id"]}</td><td>{g["freshness"]} / {g["field"]}</td><td>{g["strategy"]}</td>'
                  f'<td>{g["normal_completion"]}/2</td><td>{g["core_pass"]}/2</td><td>{g["TF"]:.2f}</td>'
                  f'<td>{g["PE"]:.2f}</td><td>{g["tool_calls"]:.1f}</td></tr>')
rows = []
for r in d['rows']:
    m = r['evidence_measurements']
    rows.append(f'<tr><td>{r["review_id"]}</td><td>{r["repeat"]+1}</td><td>{r["task_id"]}</td>'
                f'<td>{r["strategy"]}</td><td>{r["execution_status"]}</td><td>{"通过" if r["core_pass"] else "未通过"}</td>'
                f'<td>{r["tool_calls"]}</td><td>{m["non_witness_read_calls"]}</td><td>{m["fresh_read_calls"]}</td></tr>')
links = ' · '.join(f'<a href="../results/evidence/observation-selection-20261101/{p}">{label}</a>' for p, label in [
    ('research-decision.json', '准入与候选比较'), ('native-decision.json', '原生检查'),
    ('decision.json', '全部指标与门槛'), ('interpretation.json', '判断与限制'),
    ('review-freeze.json', '审查冻结'), ('sensitivity-before-unblinding.json', '争议判断敏感性'),
    ('reproduction.txt', '复现说明')])
page = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PE6203 · 观察选择诊断</title><style>
body{{font:16px/1.7 system-ui,sans-serif;max-width:1120px;margin:40px auto;padding:0 24px;color:#1b2938;background:#fafbfc}}
h1{{font-size:29px}}h2{{font-size:21px;margin-top:32px}}a{{color:#075ba6}}table{{border-collapse:collapse;width:100%;background:#fff;font-size:14px}}
th,td{{padding:9px;border-bottom:1px solid #d6dfe8;text-align:left}}th{{background:#edf2f7}}.scroll{{overflow-x:auto}}
.decision{{padding:18px;border-left:5px solid #a96a00;background:#fff4e5}}.muted{{color:#526171;font-size:14px}}code{{background:#eef1f4}}
</style><body><p class="muted">PE6203 · 2026-11-01 · 独立编号的受控合成诊断</p>
<h1>观察覆盖知识是否改变证据选择？</h1>
<div class="decision">{html.escape(interpretation['decision_zh'])} 原题 observation_coverage v1 开发失败保持不变；没有启动正式验证，完整 Goal 未完成。</div>
<h2>为何进行这项诊断</h2>
<p>上一轮原题四个项目运行均没有 get_task 调用，因而不能把局部项目收益解释成减少该工具的读取。
本次将“证据覆盖差异是否影响行为”与“actor 自选项目计划负担”分开检验。完全复用原 283 Late 的 SP 和候选知识，不追加提示、不修改模型或执行器，不把旧失败改成成功。</p>
<p>沿用 <a href="https://arxiv.org/html/2304.11477v1">LLM+P 固定 v1</a> 与官方源码
<a href="https://github.com/Cranial-XIX/llm-pddl/tree/f5f897ccabfb19d5158e5a7ac4cb36517cd4c2e0">f5f897cc</a> 的显式事实/效应表示借鉴。
本项目的字段观察覆盖与失效条件是扩展，不等于完整 LLM+P。未引入规划器、benchmark 答案或训练轨迹。</p>
<h2>冻结设计与输入检查</h2>
<p>原生规则提交 <code>3249cfd</code>，全部模型输入与 136 个源文件冻结于 <code>4e15061</code>。
7 次原生调用生成真实创建回执及修改前后状态：名称从 Larch checkpoint 改为 Cedar checkpoint，优先级从 3 改为 7。
get_task 显示名称而不显示数值优先级；推荐工具可显示这个单一待办任务的数值优先级。4 次只读检查均未改变存储。</p>
<p>四种条件为新鲜/过期回执 × 名称/优先级，各由两种方法执行两次，共 16 个单元。所有条件使用同一历史回执，双方共享相同预置存储。
新鲜性由题目明确保证或否定，不声称测试了自主识别外部修改。只读任务禁止通过修改记录获取回执；工具仍全部可用，未加运行时过滤。
答案仅用于评测，不输入 updater。固定模型、DigitalOcean、温度 0、单次 4096 token、12 轮和原五槽评分协议不变；独立费用账本。</p>
<h2>实际结果</h2>
<div class="scroll"><table><thead><tr><th>任务</th><th>条件</th><th>方法</th><th>正常完成</th><th>完整质量</th><th>TF</th><th>PE</th><th>平均工具调用</th></tr></thead><tbody>{''.join(groups)}</tbody></table></div>
<p>{html.escape(interpretation['results_zh'])}</p>
<p>“非字段证据读取”指该次返回不直接显示所请求字段；它不自动等于无用，部分读取用于身份确认。
“新鲜条件读取”只计已有保证有效回执时发生的读取，不将省略必要核查当作收益。完整质量同时要求状态保持、当前值、有效证据和真实陈述。</p>
<div class="scroll"><table><thead><tr><th>审查</th><th>区组</th><th>任务</th><th>方法</th><th>停止状态</th><th>质量</th><th>调用</th><th>非字段证据读取</th><th>新鲜条件读取</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<h2>判别结果与下一步</h2>
<p>{html.escape(interpretation['mechanism_zh'])}</p>
<p>{html.escape(interpretation['sensitivity_zh'])}</p>
<p>{html.escape(interpretation['next_zh'])}</p>
<p>事先规定的支持条件要求：两个区组的过期优先级条件均有完整质量增益且其他条件不退化，或全部质量通过并在两个区组均减少过期优先级的非字段证据读取及新鲜条件读取。未根据结果修改门槛、删除失败或补采样。</p>
<h2>复现、成本与结论边界</h2>
<p>{d['raw_files']} 个原始文件、{d['source_files']} 个源文件及 80 个原评分槽已离线核验。
{d['api_requests']} 笔请求结算 USD <strong>{d['known_usd']}</strong>，新增未知费用 {d['unknown_cost_items']}，updater 调用 0。
旧 factorial 未知费用仍在独立历史账本中。准备脚本字段名错误发生于任何模型调用前，原部分复制文件和修复证据均保留。</p>
<p>同一协调者先审产物再揭方法/评分，非独立人工或严格方法盲评；工作目录包含 cell 编号。
两个区组是新进程/工作区中的重复执行，不代表未见任务或统计独立保证。合成审计不能替代原 benchmark 的完整开发门槛与两批验证。
NU/FR 历史课程基线保持不变，最终课程综合报告和展示仍待完成。</p>
<p>{links}</p></body></html>'''
out = ROOT / 'reports/observation-selection-diagnostic.html'
out.write_text(page)
print(out)

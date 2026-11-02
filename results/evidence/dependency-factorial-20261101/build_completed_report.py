"""Render the verified complete diagnostic, keeping the interrupted report separate."""
import html,json
from pathlib import Path
E=Path(__file__).resolve().parent;ROOT=E.parents[2]
d=json.loads((E/'decision.json').read_text());a=json.loads((E/'accounting-comparison.json').read_text())
assert d['verified_complete_diagnostic'] and d['planned_and_executed_cells']==16 and not d['goal_complete']
def table(headers,rows):
 return '<table><thead><tr>'+''.join('<th>'+html.escape(str(x))+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in r)+'</tr>' for r in rows)+'</tbody></table>'
groups=table(['条件','策略','正常完成','产物全项','平均TF','平均PE','平均轮数','平均调用'],[[g['topology']+'/'+g['payload'],g['strategy'],f"{g['normal_completion']}/2",f"{g['core_pass']}/2",round(g['TF'],2),round(g['PE'],2),g['rounds'],g['tool_calls']] for g in d['groups']])
rows=table(['单元','区组','条件','策略','结束','全项','TF','PE','轮数','调用'],[[r['review_id'],r['block_index'],r['topology']+'/'+r['payload'],r['strategy'],r['execution_status'],'通过' if r['core_pass'] else '未通过',r['TF'],r['PE'],r['rounds'],r['tool_calls']] for r in d['rows']])
report='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>PE6203 依赖结构与文本负担诊断结果</title>
<style>body{font:16px/1.7 system-ui,sans-serif;max-width:1180px;margin:36px auto;padding:0 24px;color:#172b3a;background:#fafbfc}h1{font-size:30px}h2{font-size:22px;margin-top:30px}table{border-collapse:collapse;width:100%;font-size:13px;margin:20px 0}td,th{border:1px solid #bdcbd5;padding:7px;text-align:left}th{background:#e8f0f5}a{color:#075b9b}code{background:#edf1f4;padding:2px 4px}.notice{border-left:5px solid #ad6700;background:#fff4db;padding:14px 20px}li{margin:8px 0}</style>
<h1>依赖结构 × 完整字段长度：16 单元诊断</h1><p>2026-11-01 · 独立受控合成扩展 · A1 明确批准后完成原日程</p>
<p class="notice">链式依赖中，候选正常完成 4/4，对照 SP 为 0/4；候选实际产物仅 2/4 全项正确。浅结构双方均 4/4 完成、4/4 全项正确。本轮支持研究结构相关的执行成本，但没有达成原 benchmark 双提升，也没有进入正式验证。</p>
<h2>失败证据 → 文献与源码 → 冻结试验</h2>
<p>原 dependency_cut v1 在冻结变化子集上的正常完成双方均 1/4、实际全项双方均 0/4，尽管候选采用延期链接并减少部分调用。该版本保持关闭。本轮以独立生成的 8 条记录控制记录数与父子层级，分别改变 0/7 条前序依赖和每条 128/1920 字符完整正文，区分依赖结构与文本负担的作用。</p>
<p>依据 <a href="https://arxiv.org/html/2312.04511v3">LLMCompiler v3</a> 与作者 <a href="https://github.com/SqueezeAILab/LLMCompiler/tree/a00c9d35507507da70e8c637eee64efc8c1857ae">固定源码</a>：<code>output_parser.py:97</code>、<code>task_fetching_unit.py:100–133</code> 解析符号依赖与前序观测、释放可执行任务。本项目只借静态操作依赖表示与原生 API 支持的创建/补链接拆分；没有移植作者规划器、并行执行器、在线反馈或模型提示。</p>
<p>本次机制差异在受控输入干预，候选知识未再改写：逐字复制已冻结的原 283Late SP 与 dependency_cut 知识。4 条件 × 2 策略 × 2 固定顺序区组，原日程一次执行完毕；温度0、固定 DeepSeek/DigitalOcean、单次4096、12轮、原工具和评分协议不变。生成规则/知识分别冻结在 <code>1984654</code>/<code>0c2a249</code>。两个区组复用同一输入，是诊断重复，不是两批未见验证。</p>
<h2>全部条件结果</h2>__GROUPS__
<p>全项通过要求记录、字段、结构与真实最终交付同时通过；unknown不算通过。ECS为空。四个链式SP保存状态均正确，却用尽12轮、没有最终交付；仅看工具成功或官方分数会遗漏这一失败。</p>
<h2>结果如何改变下一步判断</h2><ul>
<li><strong>依赖结构值得继续研究：</strong>在两种文本长度及两个区组中，SP浅结构均成功、链式均失败。链式SP都用了9个创建轮次，后续读回占据余下轮次；候选通常拆分依赖并更早结束。关系数量与深度同时改变，所以不能独立归因于纯深度。</li>
<li><strong>完整质量没有稳定跟上：</strong>F01遗漏一条依赖，却声称全部已保存，TF仍为10；F16额外tags被工具拼入项目description，破坏输入保真，TF仍为9.6。F16任务字段/引用定向检查无差异，但冻结records失败、fields/structure保持unknown。没有修改验收或产物。</li>
<li><strong>条件化路线仅获有限支持：</strong>链式按区组汇总候选每组完成2/2、全项1/2，SP均0/2；但每个精确条件的质量优势未跨区组重复。浅结构没有收益且平均调用更多。不把汇总改成新晋级门槛，也不重启旧v1。</li>
<li><strong>文本压缩不列优先：</strong>长文本没有两区组一致的完成或完整字段退化。16单元无finish_reason=length；F07曾有一轮4096输出的可见非结构化调用片段，随后恢复。停止字段与token数量都不足以单独证明根因。</li>
<li><strong>下一优先问题：</strong>验证工具返回究竟覆盖哪些属性。当前源码显示get_task不返回全部精确元数据/依赖引用，list_tasks只显示依赖数量。来源验证的观察覆盖表示可能减少无信息增益的读回，但必须先与旧语义契约方案查重、做任务无关原生覆盖检查；不能直接把减少检查当正确性保证。</li></ul>
<p>本轮产物和评分不进入 updater 或正例池。原题需要自行规划25/26条记录，与本诊断的8条预给记录不同；规模与规划负担仍是竞争解释。下一候选仍需独立冻结和原题严格开发门槛。</p>
<h2>逐单元结果：没有删除失败</h2>__ROWS__
<h2>A1、审查偏差与复核</h2>
<p>F07第三评分槽第一次请求超时且无generation ID。用户明确批准A1后，保留原未知账目和原失败，只补缺失评分并继续008–016；旧actor无重跑。A1属于公开的冻结停止规则例外。两条原成功preflight回执经校验复用，未扩展原2次上限。任何新的未知费用仍停止，本轮没有新未知。</p>
<p>全部16份产物均保存；F07语义审查前意外看到两个评分槽，其余15份先审查后看各自官方分数，偏差已冻结披露。审查来自同一协调者，非严格方法盲评或独立人工评审。原始档案649文件、冻结来源131文件、80首有效评分槽、全部产物、旧actor/评分保存、222结算ID与单一未知行的离线核验通过。恢复路径37项本地测试通过。</p>
<h2>费用与 key 查询</h2>
<p>诊断223笔已启动请求，222笔结算：已知 <strong>US$0.271760952</strong>；A1后新增已知 <strong>US$0.153673560</strong>；旧未知1笔，总实际费用仍未知。US$0.319488只是一笔预留估算，既不是收费也不是强制上界。updater调用0，actor重跑0。</p>
<p>使用.env中的key认证，<a href="https://openrouter.ai/docs/api/api-reference/api-keys/get-current-api-key">官方只读/key接口</a>于北京时间18:19:12返回key限额US$10、累计用量US$9.135587307、剩余约<strong>US$0.8644</strong>。这不是本实验专属账单：两次查询增量US$0.146815152，与本地逐请求新增结算值相差−US$0.006858408；没有exclusive-use或结算时点证据，不能据此补填旧未知请求。备用变量OPENROUTER_API_KEY_BACKUP尚未启用，凭据不入档。</p>
<h2>决策与复现</h2><p>本轮诊断结束；继续研究观察覆盖与条件化执行成本，完整的正确性交付尚未解决。不重复本16单元、不改变原题验收、不把合成收益当原题胜出。历史NU/FR保留；原题开发、两批独立验证、课程综合报告/复现包/展示仍未完成，Goal不标complete。</p>
<ul><li><a href="../results/evidence/dependency-factorial-20261101/interpretation.json">事实、现象、假说与方向比较</a></li><li><a href="../results/evidence/dependency-factorial-20261101/decision.json">完整数值与账本核验</a></li><li><a href="../results/evidence/dependency-factorial-20261101/reproduction.txt">无网络离线复现</a></li><li><a href="../experiments/extensions/dependency-factorial-v1/protocol.json">模型前冻结协议</a></li><li><a href="dependency-factorial-interruption.html">保留的中断时点报告</a></li><li><a href="dependency-cut-development.html">原题v1失败证据</a></li></ul></html>'''
(ROOT/'reports/dependency-factorial-completed.html').write_text(report.replace('__GROUPS__',groups).replace('__ROWS__',rows))
print('Rendered verified complete diagnostic report.')

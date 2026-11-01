"""Post-outcome report only; does not change frozen experiment inputs or judgments."""
import collections
import html
import json
from pathlib import Path

E = Path(__file__).resolve().parent
ROOT = E.parents[2]
D = json.loads((E/'decision.json').read_text())
P = json.loads((E/'mechanism-projection.json').read_text())
R = json.loads((E/'research-decision.json').read_text())
assert D['verified'] and not D['development_pass'] and len(P) == 4

def save(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n')

phase = []
for x in P:
    by = collections.defaultdict(collections.Counter)
    for c in x['calls']:
        by[c['round']][c['tool'] + (' [error]' if c['error'] else '')] += 1
    phase.append({k:x[k] for k in ('cell_id','strategy','stage','execution_status','persisted_records','created_with_dependencies','postcreation_dependency_writes','deferred_records_final_nonempty')} | {
        'per_round':dict(by),
        'all_response_finish_tool_calls':all(r['finish_reason']=='tool_calls' for r in x['responses']),
        'last_completion_tokens':x['responses'][-1]['completion_tokens'],
        'last_reasoning_tokens_metadata_only':x['responses'][-1]['reasoning_tokens'],
        'interpretation':'Descriptive counts only. Removing an error or repacking calls is not an observed counterfactual actor run.'})
save(E/'phase-accounting.json',phase)
interpretation = {
 'decision':'Close dependency_cut v1 under the frozen strict development gate. No conditional validation, no additional sampling of this version.',
 'goal_complete':False,
 'current_goal_state':'Active and incomplete; actual experiment progress, not a repeated blocking turn.',
 'mechanism_question':'Can source-certified deferred cross-task dependency linking improve original SP completion and complete artifact quality under the unchanged actor?',
 'direct_facts':[
  '10/10 original benchmark development cells evaluated; 50 original judge slots preserved. Changed133M/L+283M/L: each arm completes1/4 and core0/4. Project283M/L: both0/2 for both outcomes.',
  'Both candidate project runs create all records without dependsOn and subsequently attach valid references to23 records. The planned deferred-link behavior was used. SP Middle also defers27 records, so the mediator is not unique to the candidate.',
  'All four project runs stop at12 rounds with empty final answers and tool_calls finish reason, not length. This proves the observed stopping condition, not its unique cause.',
  'Candidate creates25/26 records, restores links over3 rounds in each run, and reaches verification/refinement at rounds11-12. SP Middle also spends3 rounds on link writes. Candidate Middle corrects5 tags-type failures; candidate Late corrects an overlength project description.',
  'Three of four project stores satisfy the coordinator semantic structure review; SP Late leaves material dashboard assembly work insufficiently decomposed. All four lack the required final truthful delivery.',
  'All four math artifacts fail implementation consistency. Both235 chart payloads pass but summaries fail; both official235 TF/PE remain10. 133/235 knowledge is byte-identical across arms.',
  '419 raw files,180 frozen source/data files and all costs verified offline.104 native test calls and8 catalog reads are separately retained with zero model cost.'
 ],
 'limited_observations':[
  'Project mean TF8.5→9.8 and PE8.5→8.7, with structure property1/2→2/2; neither completion nor all-property correctness improves. One repeat per condition cannot establish population or stage-independent effect.',
  'Project tool calls total123→116. Lower call or record counts do not prove better planning, appropriate scope, faster completion or less reasoning burden.',
  'Full changed TF9.05→9.70 and PE8.20→7.80 include133 with identical knowledge; those arm differences cannot be attributed to this patch.',
  'The native valid-input certificate establishes state equivalence for its frozen graph, not universal equivalence or actual actor latency. Theoretical waves10→8 include final handoff and exclude negative controls; normal calls10→15.'
 ],
 'hypotheses_and_competitors':[
  {'hypothesis':'Deferred links were ignored, as in the prior parse_prd candidate.','decision':'Contradicted for both candidate project runs; deferred-link behavior is directly observed. This does not prove that the added graph caused it because SP Middle also chose it.'},
  {'hypothesis':'Cross-task ID serialization alone is the main removable cause of original project non-completion.','decision':'This version provides counterevidence to sufficiency: it removes those creation waits but neither original stage completes. The entire class is not disproved.'},
  {'hypothesis':'Additional link writes, output packing, native argument errors and verification/refinement consume the saved dependency depth.','decision':'Consistent with visible phases; relative contributions and error-free/counterfactual completion remain unknown. No reason-text reading or invented causal attribution.'},
  {'hypothesis':'Native correctness and official score gains are sufficient evidence of complete artifact quality.','decision':'Rejected by actual empty handoffs and code/statistical errors; keep the original complete product gate.'}
 ],
 'five_failure_classes':[
  {'class':'知识适应','fact':'候选2/2采用延期依赖；SP Middle也采用。','limit':'已采用不等于新增知识具有因果效果；不再优先做同一路线的采用提示微调。'},
  {'class':'执行与预算','fact':'项目4/4轮次耗尽；候选补链接各占3轮，验证/细化落在末轮。','limit':'停止字段不能区分参数输出、规划、错误恢复、验证开销的因果贡献。'},
  {'class':'产物生成','fact':'项目4/4无最终交付；数学4/4实现一致性失败；235两组摘要错误。','limit':'不能将结构属性通过、工具成功或TF高分当完整任务质量通过。'},
  {'class':'环境/数据','fact':'原133/283/235输入完整，377关闭；出现已保存的health故障、project长度和tags类型错误。','limit':'没有证据表明修复其中一个接口错误必然带来严格双提升；不修改冻结工具环境。'},
  {'class':'评测不确定性','fact':'235官方TF/PE10与实际摘要失败并存；同知识会有结果差异。','limit':'同协调者先验收后官方揭分；工作目录暴露cell IDs，方法遮蔽不完整。'}
 ],
 'next_decision':{
  'priority':'Do not reword deferred-link or batch hints. The highest unresolved issue is complete construction plus final handoff under the fixed actor, followed by semantic output consistency; local interface errors are contributory observations, not the assumed root cause.',
  'possible_discriminating_study':'If a next mechanism is admitted, a separately frozen controlled diagnostic can independently vary dependency depth and complete-field payload length on new task-free graphs, with the same SP/candidate/runtime and exact state plus final-answer acceptance. It would distinguish topology benefit from payload/phase cost. It is not currently frozen or authorized by this protocol, not a retry of900401/402, and cannot replace original benchmark success.',
  'admission_caution':'A diagnostic is worth model cost only if its outcomes select materially different lawful knowledge mechanisms. No immediate repeat is warranted merely to get a positive sample. No successful counterfactual or new candidate is claimed.',
  'remaining_legal_space':'Source-grounded knowledge representation, validated retain/delete decisions and LLM-assisted local updates remain allowed. Prior positive-episode gates apply only to their own closed methods; no whole-method impossibility conclusion.'
 },
 'review_limits':json.loads((E/'review-freeze.json').read_text())['method_blinding'],
 'native_failure_handling':R['native_v1_failure'],
 'course_gaps':[
  'Retain historical NU/FR/SP baselines; they are not contemporaneous controls for this candidate.',
  'Integrated final course report, reproducibility package and10-minute presentation plus5-minute discussion/rehearsal remain outstanding.',
  'Under-update/over-update causal case attribution remains limited; the report must distinguish observed failures from controlled causal proof.',
  'The user research requirement of strict original-task dual gains and two independent passing validation batches is still unmet and cannot be replaced by course minimums.'
 ],
 'provenance':{
  'native_v1_freeze':'5e539a6','native_v2_correction_freeze':'89e3bfe',
  'source_protocol_freeze':'9a5c78b','exact_knowledge_freeze':'cc5b9a6',
  'uptake_audit_predeclaration':'c220dbb','all_product_reviews_before_scores':'d503f8d',
  'independent_review':'../semantic-contract-maintenance-20261101/review-decision.json',
  'literature':R['literature']
 },
 'cost':{'requests':119,'actor':67,'judge':50,'preflight':2,'updater':0,'usd':D['known_usd'],'unknown_items':0,'unsettled_items':0,'native_calls':104,'native_catalog_reads':8,'native_model_usd':'0'}
}
save(E/'interpretation.json',interpretation)

esc=html.escape
rows=''.join('<tr>'+''.join('<td>'+esc(str(v))+'</td>' for v in [r['task_id'],r['stage'],r['strategy'],r['execution_status'],int(r['core_pass']),f"{r['TF']:.2f}",f"{r['PE']:.2f}",r['tool_calls'],r['review_id']])+'</tr>' for r in sorted(D['rows'],key=lambda r:(r['task_id'],r['stage'],r['strategy'])))
def lis(xs):return '<ul>'+''.join('<li>'+esc(x)+'</li>' for x in xs)+'</ul>'
def section(title,body):return '<section><h2>'+esc(title)+'</h2>'+body+'</section>'
body='<h1>依赖拆分知识策略：原 benchmark 开发结果</h1><p class="lead">具体版本未通过严格双提升；不启动独立验证。原 Goal 保持未完成。</p><p>2026-11-01 · 原冻结变化子集133 Middle/Late、283 Middle/Late；保持任务235 Late；每条件1次，SP为同期直接对照。全部10单元、失败、原评分和费用均保留。</p>'
body+=section('失败证据 → 机制选择','<p>上一轮独立合成训练中，两个12-record运行已保存完整正确状态，但按真实依赖ID逐项创建耗尽12轮、没有最终交付。此前 parse_prd 批量路径未被采用，完整字段恢复也使其调用成本增加。本轮选择“创建时保留所有正文、标量字段和parent层级；待真实ID齐备后，写入完整dependsOn”的不同操作依赖图。</p><p>借鉴 <a href="https://arxiv.org/html/2312.04511v3">LLMCompiler 2312.04511v3</a> 的显式依赖表示。<a href="https://github.com/SqueezeAILab/LLMCompiler/tree/a00c9d35507507da70e8c637eee64efc8c1857ae">作者源码固定SHA a00c9d3</a>：output_parser.py:97解析依赖，task_fetching_unit.py:100–133按观察解析引用、放行就绪任务。完整原方法需要LLM规划器、任务获取器及并行执行器；本项目只借表示机制，不采用其运行时、提示或样例，也不声称复现原论文收益。</p>')
body+=section('知识范围与公平条件','<p>确定性生成，updater调用0。仅在283实际变化工具create_project的description增加1862字符符号图；其他字段、工具、路由和schema逐字保护。133与235知识完全等于SP。图只来自原生源码和无任务通用合约；没有benchmark问题、答案、已评分轨迹或人工答案配方进入生成。固定模型deepseek/deepseek-v4.1-flash-1017、DigitalOcean、temperature0、单次4096含reasoning、12轮及原工具/评分协议均不变。</p><p>课程要求与用户要求分列在research-decision.json；严格开发双提升及两批独立验证来自用户。旧正例训练门槛、append-only或一跳关系是特定方法的实现选择，未成为通用禁区。已完成独立审查的意见用于本轮准入；未为取得一致意见再开审查agent。</p>')
body+=section('原生诊断与冻结','<p>v1的4条路径均因测试生成器details尾空格被原生.trim()删除而未通过逐字字段验收；52次调用和失败完整保留。按源码冻结v2，只移除测试输入尾空格，保持8节点、全部字段、图结构、顺序及4路径，使用新工作目录；另52次调用全部状态等价，2个无效链接负控正确拒绝且状态不变。没有重试模型或更改原题验收。正常直接路径10调用，延期路径15调用；理论依赖轮次10→8（含最终答复），不等于实测actor轮次。</p><p>5e539a6原生v1 → 89e3bfe修正v2 → 9a5c78b候选/协议 → cc5b9a6精确10份知识锁定，之后才开始模型调用。开发必须同时通过项目子集与全部变化子集的完成、core严格提升，且TF/保持不下降。条件验证预设两批各30单元、每条件3次、新工作区；仅同任务族的新执行独立，不能称未见任务或证明供应商随机独立。本轮未达到入口，不执行。</p>')
body+=section('实际开发结果','<table><thead><tr><th>任务</th><th>阶段</th><th>方法</th><th>停止状态</th><th>core</th><th>TF</th><th>PE</th><th>工具调用</th><th>验收ID</th></tr></thead><tbody>'+rows+'</tbody></table><p><strong>变化子集：</strong>SP与候选正常完成均1/4、core均0/4；TF9.05→9.70，PE8.20→7.80。<strong>项目子集：</strong>均完成0/2、core0/2；TF8.5→9.8、PE8.5→8.7。<strong>235保持：</strong>两组均正常完成，TF/PE均10，core均0/1。ECS因不含匹配三阶段为null。</p><p>三个项目结构被评为可执行且范围完整，但四个均没有最终答复。数学四份交付均有实现一致性问题；235两份图表调用参数正确，最终统计或趋势解读错误。core要求全部原定属性通过，unknown不能当pass。133/235知识相同，其跨组波动不归因为本补丁。</p>')
body+=section('机制采用与竞争解释',lis(interpretation['direct_facts'][1:4])+lis([x['hypothesis']+' '+x['decision'] for x in interpretation['hypotheses_and_competitors']])+'<p>候选项目调用总数123→116，结构属性1/2→2/2，属于有限样本局部差异；不会替代完整双提升。原SP Middle也使用延期链接，削弱“路径采用即候选因果效果”的解释。新增链接阶段各占3轮；参数修正、验证及细化也可见，但未做隔离干预，不能给它们分配因果贡献。</p>')
body+=section('证据边界与评测限制','<p>所有10份实际产物判断在d503f8d提交后才查看官方分数。<strong>方法遮蔽不完整：</strong>冻结collector保留workingDirectory中的cell编号，结合已见执行顺序可能推断方法；因此这是同协调者“先验收后官方揭分”，不是严格方法盲评或独立人工。原始包不事后脱敏重写，评判标准没有改变。语义可管理性有判断空间；把相关pass改为unknown也不会改变本轮core全失败和停止决定。</p><p>每条件1次、历史已暴露任务族；5次judge评分不是5次actor重复。未读取隐藏reasoning文本，仅读用量和停止元数据。原生等价、TF/PE高分和短调用路径均不证明正常完成或产物正确。</p>')
body+=section('决定与剩余工作','<p>关闭dependency_cut v1，不执行条件验证，不补采到胜出。此次证据否定该具体版本的充分性，并排除候选“两次均未采用延期路线”的解释；不否定所有依赖表示、LLM更新或经验学习方法。</p><p>'+esc(interpretation['next_decision']['priority'])+'</p><p>'+esc(interpretation['next_decision']['possible_discriminating_study'])+'</p>'+lis(interpretation['course_gaps']))
body+=section('费用、验证与复现','<p>119笔API请求＝67 actor＋50 judge＋2 preflight；updater0；<strong>USD0.205121340</strong>，未知/未结均0。两版原生诊断共104调用＋8次目录读取，无模型费用。74项针对性测试通过；419原始文件、180冻结源/数据文件及272原生归档文件离线核验。</p><pre>python3 results/evidence/dependency-cut-20261101/verify_native.py\npython3 results/evidence/dependency-cut-20261101/verify_development.py\npython3 results/evidence/dependency-cut-20261101/measure_uptake.py</pre><p>核验无需模型调用。证据目录保留冻结协议、源/原始归档、所有逐项验收、官方5槽位、费用ledger和复核脚本；reproduction.txt给出准确恢复/重跑边界。NU/FR历史课程基线未改变，不冒充同期对照。</p>')
page='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Dependency-cut 原题开发结果</title><style>body{max-width:1120px;margin:40px auto;padding:0 24px;font:16px/1.75 system-ui,sans-serif;color:#243345;background:#fafbfc}h1{line-height:1.3}h2{font-size:21px;margin-top:34px}section{background:white;padding:14px 22px;margin:22px 0;border:1px solid #dae2ea;border-radius:8px}.lead{font-size:21px;color:#9d3927}table{width:100%;border-collapse:collapse;font-size:13px}th,td{border:1px solid #dce4eb;padding:7px;text-align:left}th{background:#edf2f6}pre{white-space:pre-wrap;background:#edf2f6;padding:14px}a{color:#215d98}li{margin:8px 0}</style><body>'+body+'</body></html>'
(ROOT/'reports/dependency-cut-development.html').write_text(page)
print(json.dumps({'report':'reports/dependency-cut-development.html','decision':interpretation['decision'],'goal_complete':False}))

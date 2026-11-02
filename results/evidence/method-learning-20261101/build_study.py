"""Distill bounded evidence; never read trajectories, questions, answers or credentials."""
import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def read(path):
    return json.loads((ROOT / path).read_text())


def write(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def main():
    prefix = "results/evidence/"
    studies = {}
    evidence_files = []
    for name, file in [
        ("contract_reconcile", "contract-reconcile-pilot-20261101/trial-verification.json"),
        ("weather_provenance", "weather-provenance-pilot-20261101/trial-verification.json"),
        ("project_state_contract", "project-state-pilot-20261101/trial-verification.json"),
        ("discovery_contract", "discovery-contract-validation-20261101/verification.json"),
    ]:
        path = prefix + file
        d = read(path)
        studies[name] = {"source": path, "summary": d["summary"], "ECS": d.get("ECS"),
                         "known_usd": d["known_usd"], "api_requests": d["api_requests"]}
        evidence_files.append(path)
    original = prefix + "selective-search-20261031/confirmation-r1-review.json"
    d = read(original)
    studies["sufficiency_feedback"] = {"source": original, "summary": d["summary"]["arms"],
                                        "decision": d["summary"]["decision"],
                                        "interpretation": d["interpretation"]}
    evidence_files.append(original)
    extension = prefix + "extensions/magicui-log-dashboard-v1/decision.json"
    d = read(extension)
    studies["native_argument_routing_extension"] = {
        "source": extension, "group_results": d["group_results"], "costs": d["costs"],
        "development_gate_passed": d["development_gate_passed"], "ECS_reason": d["ECS_reason"]}
    evidence_files.append(extension)
    write("reused-metrics.json", studies)

    failures = [
        {"category": "知识适应问题", "proven": "workflow_notes v2 被语义审查发现把另一条已失败路径当替代；更新器输入验证通过不等于行为知识正确。", "observed": "MagicUI 两次失效调用降为零；Context7 候选也避开已知坏接口，但原题验证完成数均11/12、实际质量均0/12。", "hypothesis": "应以可复用动作/产物的正反经验约束知识，而不只记住局部调用错误。", "source": prefix + "selective-search-20261031/generation-v2-rejection.json"},
        {"category": "执行与预算问题", "proven": "MagicUI 两组最后响应均finish_reason=length，4096 completion全部计为reasoning，未产生最终答复或工具提议；这是可直接定位的停止条件。", "observed": "contract_reconcile调用从40降至10、PE从5.9升至9.2，完成和core仍均0/2；项目候选最后一轮同样4096 reasoning截断，SP则轮数耗尽。", "hypothesis": "减少探索没有减少产物构造的推理负担；大返回可能加重负担，但未建立因果。", "source": prefix + "extensions/magicui-log-dashboard-v1/mechanism-projection.json"},
        {"category": "产物生成错误", "proven": "已有验收确认数学代码的运算符/边界处理矛盾、RT-2摘要能力混淆，以及235最终统计解读错误；扩展两组均未写出parser/data/page。", "observed": "weather_provenance曾把变化任务core由0/2提高至1/2，但两组完成本已2/2，保持任务core又未达门槛。", "hypothesis": "有执行证明的程序记忆可能减少从接口知识到正确产物之间的重新推导。", "source": prefix + "contract-reconcile-pilot-20261101/final-response-inspection.json"},
        {"category": "环境/数据问题", "proven": "377原始输入缺失、当前不可评估；171缺所需服务且不属201题，217缺读取工具且不属201题，246输入缺购买频次且无读取工具。12306旧探针在原生初始化停止，未发生agent试验。", "observed": "完整的合成日志已能读写；输入完整没有自动解决产物生成。", "hypothesis": "输入/依赖准入必须先于方法优劣判断。不能将这些排除记为策略失败。", "source": prefix + "mechanism-screening-20261101/magicui-task-readiness-screen.json"},
        {"category": "评测不确定性", "proven": "扩展保持235的两组官方TF/PE都是10，但盲审发现最终事实错误。官方prompt确实接收最终answer，不能归因于没有把答案传给judge。", "observed": "同K0的保持结果会波动；sufficiency_feedback旧确认总体完成14/27对SP17/27，但变化阶段均11/18，差异在Early，不能断言补丁致损。", "hypothesis": "官方高分不足以作为经验入库的正确性标签；需独立产物验证。", "source": prefix + "extensions/magicui-log-dashboard-v1/blind-review/cell-003-review.json"},
    ]
    evidence_files.extend(x["source"] for x in failures)
    evidence_files.extend([
        "src/pe6203/patch_variants.py", "src/pe6203/runner.py", "src/pe6203/judge.py",
        "experiments/.context/selective-literature.json",
        prefix + "project-state-pilot-20261101/response-diagnostics.json",
        prefix + "discovery-contract-validation-20261101/decision.json",
    ])
    write("failure-matrix.json", {"scope": "Six selected summaries plus targeted native/source/response metadata; not an exhaustive failure census.", "classes": failures,
                                  "labels": {"proven": "源码、原生返回、停止字段或确定性产物检查直接支持；不等于证明策略因果。", "observed": "有限运行中的共同现象/差异。", "hypothesis": "须新干预检验，不能写成既定原因。"}})
    repos = {x["id"]: x for x in read("results/evidence/method-learning-20261101/sources/repo-index.json")}
    methods = [
        {"id": "ace", "paper": "ACE · 2510.04618v1 · 2025-10-06", "url": "https://arxiv.org/html/2510.04618v1", "sections": "3.1、3.2", "mechanism": "条目ID与helpful/harmful计数、分工反思与局部合并；实现另有相似条目合并。", "code": ["ace/ace.py:510", "playbook_utils.py:50", "playbook_utils.py:96", "ace/core/bulletpoint_analyzer.py:273"], "old_gap": "旧delta_notes是确定性追加说明，没有Generator/Reflector/Curator循环或效用计数。", "implementation_limit": "此SHA的apply_curator_operations只实现ADD，UPDATE/DELETE等标成TODO；不能把论文所有编辑能力都说成该函数已经实现。"},
        {"id": "amem", "paper": "A-MEM · 2502.12110v1 · 2025-02-17", "url": "https://arxiv.org/html/2502.12110v1", "sections": "3.1–3.3", "mechanism": "结构化记忆、语义检索和邻居演化；演化可以修改相关旧记忆，而非只向新条目追加文字。", "code": ["memory_layer.py:777", "memory_layer.py:819", "memory_layer.py:828", "memory_layer.py:945"], "old_gap": "旧linked_notes只按同服务词项相似度取两个邻居；没有完整图演化或执行期检索。", "implementation_limit": "核读的是作者论文复现实验仓库的2026版本，晚于v1；README另链接生产库A-mem-sys。没有声称本地复现其效果或读过新FlexA-MEM全文。"},
        {"id": "reflexion", "paper": "Reflexion · NeurIPS 2023 proceedings", "url": "https://proceedings.neurips.cc/paper_files/paper/2023/file/1b44b878bb782e6954cd888628510e90-Paper-Conference.pdf", "sections": "复用既有section2阅读；此次核读编程实现", "mechanism": "测试执行反馈推动代码反思与后续尝试；可执行检验与语言反思不同。", "code": ["programming_runs/reflexion.py:8", "programming_runs/reflexion.py:43", "programming_runs/executors/py_executor.py:11"], "old_gap": "旧feedback_notes是事前冻结的工具探针记忆，没有整任务反思重试。", "implementation_limit": "完整执行循环会增加任务尝试/模型调用或反馈通道，不可直接放进当前固定agent协议。"},
        {"id": "expel", "paper": "ExpeL · 2308.10144v3 · 2024-12-20", "url": "https://arxiv.org/html/2308.10144v3", "sections": "4.1–4.3", "mechanism": "比较同任务成功与失败经验；以增删改和支持计数整理规则，再检索成功示例。成功经验也可能低效，不能照单全收。", "code": ["agent/expel.py:124", "agent/expel.py:287", "agent/expel.py:665", "agent/expel.py:696"], "old_gap": "旧候选没有成功/失败成对经验、规则支持计数与淘汰；只用原生调用成败不能声称已实现ExpeL。", "implementation_limit": "当前updater边界只容许元数据及冻结通用探针，不得输入原benchmark题目、答案或评分轨迹；论文的任务示例检索不可原样照搬。"},
        {"id": "voyager", "paper": "Voyager · 2305.16291v2 · 2023-10-19", "url": "https://arxiv.org/html/2305.16291v2", "sections": "2.2、2.3", "mechanism": "把成功后接纳的可执行程序作为技能存储和检索，程序与执行环境共同构成复用条件。", "code": ["voyager/agents/skill.py:53", "voyager/agents/skill.py:61", "voyager/agents/skill.py:114", "voyager/voyager.py:353"], "old_gap": "旧document_sequence曾提供短格式例子，但没有可执行程序库和成功门控；不能把换一种顺序说明称为程序记忆。", "implementation_limit": "官方实现不仅把技能放进prompt，也将程序送入环境执行。当前候选只能把代码作为工具知识数据，不能偷加执行钩子或候选专用文件。"},
    ]
    for method in methods:
        repo = repos[method["id"]]
        method.update(repo=repo["repo"], sha=repo["sha"], commit_date=repo["commit_date"])
    write("method-review.json", {"papers": methods, "primary_only": True, "reading_date": "2026-11-01", "code_executed": False,
                                 "scope": "Original three readings reused; original implementations inspected; two additional mechanisms ExpeL/Voyager read. No upstream full histories, datasets or rollouts loaded."})

    candidates = [
        {"id": "effect_credited_memory", "bottleneck": "局部知识有用但未产生正确产物，且官方高分不可靠地标记经验质量。", "new_mechanism": "借鉴ACE/ExpeL，按独立可执行结果给原子经验支持/反例信用，用替换/撤销而非无条件追加维护局部知识。", "dual_gain_hypothesis": "不传播失败替代和无产物的高分经验，可能同时少走弯路、少输出错误。", "readiness": "原题133/283输入可以完整；但现有可用updater训练材料主要是原生工具收据，缺少在不读原题答案条件下的端到端成功/失败程序对。", "falsifier": "规则在预留通用反例上仍推荐失败路径；或更新结果等价于旧feedback_notes，不能建立新机制。", "decision": "不选入本轮模型试验。缺少学习信号是可补充的设计缺口，不是整类方法无效；不能拿已评分benchmark轨迹回灌补足。"},
        {"id": "retrieved_context_memory", "bottleneck": "大批原生代码/日志进入上下文，最后4096 reasoning截断。", "new_mechanism": "借鉴A-MEM的存储/检索分离，按相关性仅展开需要的记忆内容。", "dual_gain_hypothesis": "保留可追溯证据同时减少无关内容，可能给产物推导留下空间。", "readiness": "现agent_loop每轮提供固定全工具知识和累积原生消息。动态检索/历史压缩需要改变执行器；直接删减原生返回也违反固定公平条件。静态知识压缩只能触及一小部分已观察prompt。", "falsifier": "需要改runner才能达成目标，或在固定轨迹下无法改变主体上下文。", "decision": "当前范围不准入动态版本；没有据此否定静态知识通过改变调用行为产生收益的可能。"},
        {"id": "verified_component_memory", "bottleneck": "工具路由正确后仍要重新把大批源码转换为可运行产物。", "new_mechanism": "借鉴Voyager，把原生返回中完整、依赖闭合、已验证效果的程序作为知识值；按能力而非题目检索，冻结后仅写入受影响工具记录。", "dual_gain_hypothesis": "减少重新搜索和代码改造负担，同时复用已执行验证的组件；不包含日志解析器、统计答案或完整dashboard。", "readiness": "路线1无已就绪MagicUI原题；路线3已有独立日志与解析/展示检查。选此项做零模型准入：代码2481字节合格，但当前Node环境不具备TSX/React/别名/样式闭合，渲染未验证。", "falsifier": "两段预先选定代码不能在共同冻结环境执行并呈现原生声明效果；后续若补足环境仍无完成/core增益，否定该具体版本。", "decision": "本轮所选，离线准入not_ready。未生成agent知识、未运行模型对照；不得换成下一短组件或把依赖失败算成策略任务失败。"},
    ]
    write("candidate-designs.json", {"candidates": candidates, "selected": "verified_component_memory", "model_trial_registered": False,
                                    "next_admissible_work": "要继续此方向，需单独声明并验证双方相同的依赖/样式构建环境，并证明与冻结原生组件兼容；或为effect_credited_memory先建立不含benchmark答案的通用程序经验对。均不得复用失败版本反复抽样。没有准入候选前不启动agent试验。",
                                    "validation_policy": "新的完整开发试验先冻结输入/知识/验收/日程；开发通过后两批独立验证，每批完成及实际质量均严格高于SP，TF及保持不降；原NU/FR证据继续保留。", "goal_complete": False})
    write("evidence-index.json", {"files": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sorted(set(evidence_files))},
                                  "not_loaded": ["full chat history", "full trajectories", "secrets", "benchmark reference answers"],
                                  "original377": "原始输入缺失，当前不可评估；查找/等待路线关闭，不重查。"})

    esc = html.escape
    def table(headers, rows):
        return '<div class="scroll"><table><thead><tr>' + ''.join('<th>'+esc(h)+'</th>' for h in headers) + '</tr></thead><tbody>' + ''.join('<tr>'+''.join('<td>'+esc(str(c))+'</td>' for c in row)+'</tr>' for row in rows) + '</tbody></table></div>'
    report = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>有边界的方法复盘与程序记忆准入</title><style>body{font:16px/1.7 system-ui,sans-serif;max-width:1180px;margin:32px auto;padding:0 20px;color:#203040;background:#fafbfc}h1{font-size:28px}h2{margin-top:32px}a{color:#0668a2;overflow-wrap:anywhere}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border:1px solid #ccd6df;padding:10px;vertical-align:top;text-align:left;overflow-wrap:anywhere}th{background:#edf2f7}.scroll{overflow:auto}code{overflow-wrap:anywhere}.notice{padding:16px;border-left:4px solid #b27616;background:#fff6e7}p,li{max-width:105ch}</style><main><h1>失败证据 → 文献/源码 → 新机制 → 可执行准入</h1>
<p class="notice"><strong>Goal仍未完成。</strong>已结束的试验保持原协议和原分数。本轮没有启动新agent/updater/judge试验，没有改模型、预算或评分。新程序记忆设计完成了事前冻结的离线准入，结果为尚未就绪；不是agent策略失败，也不是双重改善证据。费用USD0。</p>
<p>范围：复用六组汇总、必要的定向事实与两份原生代码返回；不读完整聊天、全量轨迹、原benchmark参考答案或密钥。保留全部旧结果。任务377仍为“原始输入缺失，当前不可评估”，关闭的查找路线未重开。</p><h2>一、经验复盘</h2>'''
    report += table(["类别", "直接证据支持", "观察现象", "待检验假说"], [[x[k] for k in ["category", "proven", "observed", "hypothesis"]] for x in failures])
    report += '<p>这里的“已证明”仅指停止字段、源码或产物检查直接支持的事实；不把相关现象解释为策略因果。失败的具体实现也不代表ACE、A-MEM或Reflexion整类无效。</p><h2>二、哪些收益未转化为双改善</h2>'
    rows=[]
    for name in ["contract_reconcile", "weather_provenance", "project_state_contract", "discovery_contract"]:
        entry=studies[name]
        for method, groups in entry["summary"].items():
            g=groups["changed"];r=groups["retention"]
            rows.append([name, method, f'{g["completed"]}/{g["n"]}',f'{g["core_pass"]}/{g["n"]}',f'{g["TF"]:.3f}',f'{g["PE"]:.3f}', f'{r["completed"]}/{r["n"]}; {r["core_pass"]}/{r["n"]}; TF {r["TF"]:.3f}', '不适用：未配齐三阶段'])
    report += table(["原benchmark研究", "方法", "变化任务正常完成", "实际产物core", "TF", "PE", "保持：完成/core/TF", "ECS"], rows)
    report += '<p>以上是各自冻结试验的描述性结果，不跨试验合并为胜率。Context7表为两批合计，原两批均未通过；它不是新的独立验证。contract_reconcile的PE改善和weather的单例core改善分别缺少完成提升，后者还未通过保持门槛。保持知识相同的差异不能归因于适应。</p>'
    report += '<p>旧sufficiency_feedback确认：post-change PE提高0.9111，但变化阶段完成均11/18；总完成14/27对SP17/27，差异来自相同K0的Early。原NU/FR也在该108单元确认中保留：完成20/27、18/27，ECS分别9.8890、9.8853；SP与候选ECS均9.9821。旧晋级门槛仍按当时冻结规则失败，不能用现在的新目标改写历史。</p>'
    report += '<p>扩展900001单独解释：SP与native_argument_routing均完成0/1、core0/1、TF1、PE3.2；235保持两者均完成1/1、core0/1、TF10、PE10。ECS不适用。37请求USD0.040553940为旧扩展成本，本轮成本另为0，未混入原benchmark汇总。</p><h2>三、原始论文与固定源码版本</h2>'
    for m in methods:
        report += '<h3>'+esc(m["paper"])+'</h3><p><a href="'+m["url"]+'">论文（'+esc(m["sections"])+')</a> · <a href="https://github.com/'+m["repo"]+'/tree/'+m["sha"]+'">作者仓库 '+m["sha"][:12]+'</a>（提交日期 '+esc(m["commit_date"])+ '）</p><p>'+esc(m["mechanism"])+' '+esc(m["old_gap"])+' '+esc(m["implementation_limit"])+'</p><ul>'
        for code in m["code"]:
            file,line=code.rsplit(':',1)
            report += '<li><a href="https://github.com/'+m["repo"]+'/blob/'+m["sha"]+'/'+file+'#L'+line+'">'+esc(code)+'</a></li>'
        report += '</ul>'
    report += '<h2>四、三个有区别的候选与决定</h2>'
    for c in candidates:
        report += '<h3>'+esc(c["id"])+ '</h3>' + ''.join('<p><strong>'+esc(label)+'：</strong>'+esc(c[key])+'</p>' for label,key in [("证据瓶颈","bottleneck"),("机制差异","new_mechanism"),("双改善假说","dual_gain_hypothesis"),("输入与环境","readiness"),("否定条件","falsifier"),("决定","decision")])
    admission=read("results/evidence/method-learning-20261101/admission-result.json")
    report += '<h2>五、本轮已执行的准入，而非新的模型成绩</h2><p>386649a在选择组件和检查依赖之前冻结：每个完整类别只选UTF-8源码最短者，同长按名称，禁止失败后换下一个。两个选择均保留原生代码；没有手写解析器、统计答案或dashboard进入知识。</p>'
    report += table(["类别", "固定选择", "源码字节", "运行结果"], [[x["category"],x["name"],x["code_bytes"],"原Node不能直接解析TSX；react和@/lib/utils未解析；渲染未验证"] for x in admission["selections"]])
    report += '<p>合计2481字节，低于事前16000字节上限。本准入的直接Node路径没有闭合运行/样式依赖，不能把原生代码片段叫作已验证技能。没有枚举所有已安装编译器，也没有测试原生run-code的TypeScript模式；其他构建路径仍未知。它不证明agent无法自行改写成另一种实现；那是另一条尚未验证的路径。</p><p>固定已观察轨迹，仅移除静态首轮输入的宽松占比上界：SP 2526/18890≈13.37%，候选2611/55195≈4.73%。首轮还含任务和系统文本，实际工具知识更小。此计算没有重编码完整请求，且不包含知识改变后续行为的效应；不证明上下文导致截断。</p>'
    report += '<h2>六、两条路线与下一步边界</h2><p>原benchmark路线：本轮没有新纳入MagicUI原题。171/217/246沿用原始数据和工具准入结论，377保持不可评估。133/283的输入完整，但将这些题的成功答案回灌ExpeL式经验池会越过现有updater输入边界；本轮未这样做。</p><p>扩展路线：现有独立日志、固定种子/哈希/统计oracle、解析重放/变形/网页验收均可复用；原900001已暴露，不能伪装成盲验证。若继续程序记忆，需要先单独验证双方相同的React/TSX/别名/样式构建环境，证明冻结原生程序确能执行，而不是把依赖装进候选专用workspace。新的完整试验须使用独立ID/目录并冻结知识、任务、验收与日程。开发通过才开两批独立验证，每批完成和core严格高于SP，TF与保持不降；合成胜出仍不能完成原benchmark Goal。</p><p>当前没有通过准入、可直接启动模型对照的新候选。具体缺口已定位为程序执行闭合和不泄漏答案的经验标签；不是等待377，也不是证明方法空间已穷尽。没有重跑旧候选、推送、部署或外发。</p><h2>复算与证据</h2><ul>'
    links=[("准入协议","../experiments/verified-component-memory-admission-v1.json"), ("失败矩阵","../results/evidence/method-learning-20261101/failure-matrix.json"),("原始指标投影","../results/evidence/method-learning-20261101/reused-metrics.json"),("论文与代码版本","../results/evidence/method-learning-20261101/method-review.json"),("候选设计","../results/evidence/method-learning-20261101/candidate-designs.json"),("可执行准入脚本","../results/evidence/method-learning-20261101/run_admission.py"),("准入原始结果","../results/evidence/method-learning-20261101/admission-result.json"),("离线复核脚本","../results/evidence/method-learning-20261101/verify_study.py")]
    for label,url in links:report+='<li><a href="'+url+'">'+label+'</a></li>'
    report += '</ul><p><code>python3 results/evidence/method-learning-20261101/verify_study.py</code>仅核验本轮文件和定向旧证据，不启动模型或原生服务。</p></main></html>'
    (ROOT / "reports/method-learning-and-program-memory.html").write_text(report)


if __name__ == "__main__":
    main()

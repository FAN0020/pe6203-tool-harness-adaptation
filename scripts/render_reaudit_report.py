"""Render the reproducible, condition-stratified audit. No ranking or model calls."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "results/evidence/unified-reaudit-20261102"


def read(name):
    return json.loads((E / name).read_text())


def main():
    inv, audit, comparison, costs = (read(n) for n in ["candidate-inventory.json", "audit.json",
                                                    "condition-comparison.json", "cost-audit.json"])
    special = {
        "workflow_notes":"v2生成后语义拒绝；没有actor结果",
        "semantic_contract_closure":"联合edit/edge生成未准入；没有closureactor结果",
        "active_contract_probing":"v1及一次引用恢复共13updater请求；语义/规则准入失败，没有actor结果",
        "observed_contract":"原题pilot6格；验证36格=两批各18格；两批均失败",
        "discovery_contract":"原题pilot6格；验证36格=两批各18格；两批均失败",
        "sufficiency_feedback":"完整108格四臂确认；供应商未固定；SP/SF54格产品补审已完成，非当前Goal通过",
        "budget_feedback":"v3开发、两次中断108格计划、后续固定供应商复查；不得称108已完成",
        "artifact_contract":"原题457必须区分缺fixture、补PDF、补runtime各准备版本；执行数不是全部原计划数",
        "semantic_contract_direct":"v1生成拒绝；v2主张修复与后续optional_projection共同对照分开记录",
        "native_argument_routing":"原377缺输入未执行；actor证据来自独立合成扩展及235保持",
        "verified_component_memory":"原生准入及共同运行依赖通过后仅合成扩展actor；不能替代原377",
        "shared_contract_refs":"10格中9评分+1原429失败；A2只补未开始4格，未重复失败格",
    }
    lines = ["# PE6203 统一复评工作记录（2026-11-02）", "",
        "状态：审计与新机制迭代进行中，完整研究Goal未达成。旧实验结论、评分与失败均未改写。", "",
        "36项的可核实定义是请求前提交 `d6b60d2` 的 `patch_variants.VARIANTS`。这是登记项清单，不等于36个均完成实测的方法；描述压缩生成器等额外原型另有费用与证据，不塞进这36项。", "",
        "**Top 5来源已由用户补齐。** 明确名称为sufficiency_feedback、observed_contract、discovery_contract、budget_feedback、shared_contract_refs；第5项原文为“shared_contract_refs等最近候选”，未指明的集合成员不擅自补列。budget_feedback与observed_contract合并后无需新增重复项。版本和原记录见top5-provenance.json。以下36项按登记顺序列出，不是排名。", "",
        f"离线复算：{audit['cohorts']}个队列、{audit['planned_cells']}计划格、{audit['executed_cells']}已执行格、{audit['judge_slots']}有效评分槽；{audit['reviewed_products']}格已有可映射的逐属性产品判断。原始槽与TF/PE均值不符0，冻结知识文件哈希不符0。未执行格与缺失判断不计成功。", "",
        "| 登记候选 | Actor/5槽评分格 | 已有逐属性审查格 | 原题 / 固定fixture原题 / 合成 | 版本与证据边界 |", "|---|---:|---:|---|---|"]
    for r in inv:
        cc = r["condition_classes"]
        classes = " / ".join(str(cc.get(c,0)) for c in ["original_benchmark","original_with_fixed_fixture","controlled_synthetic_extension"])
        protocols = ", ".join(r["protocols"]) or "无actor协议执行"
        note = special.get(r["candidate"], "协议：" + protocols)
        lines.append(f"| `{r['candidate']}` | {r['executed_cells']}/{r['evaluated_cells']} | {r['products_reviewed']} | {classes} | {note} |")
    lines += ["", "所有数字均为该候选臂自身，不重复计入SP。每个协议、知识哈希、原题文本/哈希、评分槽、状态与审查来源见 `candidate-inventory.json`、`cohorts.json`、`cells.json`；精确条件表见 `condition-comparison.csv`。", "",
        "## 优先复评：相同任务条件逐项展示", "",
        "下面展示5个已核实名称及所在队列SP；不同队列、任务或阶段不求统一均值、不作加权排名。完成/全属性列分母是实际执行格；全属性分子后另列审查覆盖，避免把未审查混成失败。缺分或未跑完整计划时完整TF/PE保持空值。", "",
        "| 队列 | 题/阶段 | 方法 | 完成/执行 | 全属性通过/已审查 | TF/PE（评分n） | 外层工具错/调用 | Actor+Judge已知$ |", "|---|---|---|---:|---:|---|---:|---:|"]
    cohorts = {r["cohort"] for r in comparison if r["strategy"] in ["sufficiency_feedback","observed_contract","discovery_contract","budget_feedback","shared_contract_refs"]}
    for r in comparison:
        if r["cohort"] not in cohorts or r["strategy"] not in ["selective_patch","sufficiency_feedback","observed_contract","discovery_contract","budget_feedback","shared_contract_refs"] or not r["executed"]:
            continue
        tf = f"{r['TF']:.3f}" if r["TF"] is not None else "缺失"
        pe = f"{r['PE']:.3f}" if r["PE"] is not None else "缺失"
        lines.append(f"| {r['cohort'].split('/')[-1]} | {r['task_id']}/{r['stage']} | {r['strategy']} | {r['completed']}/{r['executed']} | {r['core_pass']}/{r['product_reviewed']} | {tf}/{pe}（{r['TF_n']}） | {r['tool_outer_errors']}/{r['tool_calls']} | {r['actor_judge_known_usd']} |")
    lines += ["", "**可比性限制：** 早期sufficiency_feedback完整108格实际涉及12个actor供应商；completion-quality旧12格也采用价格路由，不能与固定DigitalOcean结果合并归因。existing-method-recheck、paired-extension和observed_contract验证实际均为DigitalOcean。`comparability.json`保留每队列实际供应商计数、原题/工具来源与知识锁。两批observed_contract验证已经包含全属性审查，不重跑。", "",
        "235在这些固定实验中是精确同K0的保持任务；其完成、TF/PE与产品差异应作为运行波动报告，不能归因为知识干预。457补齐PDF/共同渲染依赖的版本单列固定fixture原题。900000以上独立编号为受控合成；377原输入缺失始终不纳入可执行比较。", "",
        "## 费用与未知", "",
        f"响应ID去重并集：{costs['deduplicated_union']['responses']}个已定价响应，已知USD **{costs['deduplicated_union']['known_usd']}**。这是下界，不是已结清总额。", "",
        f"其中匹配队列actor/judge收据USD {costs['matched_cohort_actor_judge']['known_usd']}；较广历史账本USD {costs['broader_historical_ledger']['known_usd']}；updater收据USD {costs['updater_receipts']['known_usd']}。三者有重叠，**不可相加**。较广账本含课程基线、准入、原生诊断相关模型请求等。保留{len(costs['unresolved_ledger_requests'])}笔未决账本请求；另有早期失败actor请求缺ID，不能仅用网页/key累计额度补记为0。", "",
        "`cost-receipts.json`给出去重来源；`cost-audit.json`给出账本原数、复算、范围和未知。新字典、差分与能力合并轮费用在独立账本另报，不混入以上历史快照。", "",
        "## 已推进的新机制", "",
        "第一方向：对observed_contract原16条探针证据做无损表示。首版observed_dictionary共享完全相同的结果，保留全部输入/结果与边界，解码可恢复原记录；只改真实变化的validate_syntax知识。它不同于跨工具参数描述引用、语义主张替换和额外预算提示。", "",
        "来源依据：本地observed_contract_note每条重复相同文本与限制；复用EasyTool论文2401.06201v3及官方JARVIS SHA7624cf388b47334ff8a0868e7d862dde18cfda86中的紧凑工具文档思想，未采用其分段执行器。这是本项目的无损编码机制，不声称复现完整EasyTool。", "",
        "第一轮10格已完成，源冻结0393d55、盲审封存cbcfa17。SP→字典版：133正常完成2/2→0/2、完整产物0/2→1/2；全变化完成2/4→0/4、完整产物0/4→1/4、TF9.60→9.25。开发失败，不验证。117笔请求全部结算$0.236955324；50评分槽、335原生调用。92源文件/421原始文件与知识哈希、评分、响应ID全部核验。R04宽松主判通过但最终答复截断；预存严格敏感性将其guidance判unknown时也不晋级。", "",
        "第二轮observed_contrastive已完成10格开发，知识冻结664057a、盲审封存f07cef0。同表达式基准参数+精确set/remove差分，保留16条输入/结果。133完成0/2→1/2、完整产物均0/2、TF均9.7；全变化完成0/4→1/4、完整产物均0/4、TF8.9→9.75。质量未改善，关闭具体版本，不验证。120笔请求全部结算$0.223354932。283/235知识相同，差异不归因为干预。", "",
        "第二方向为能力合并：源代码与44次原生调用、22组配对检查证明合法输入域的validate_syntax可由evaluate(validate_only=true)实现。只从模型知识删除重复能力，并注释既有代表模式；原生工具与actor不改。10格开发已结束，f60f96b冻结、e9e81e6盲审封存。133正常完成2/2→0/2、完整产物0/2→0/2、TF9.7→9.2；全变化完成2/4→0/4、完整产物均0/4、TF9.4→9.1。124笔请求已结算$0.253853268，50评分槽，412原生调用，未知费用0。开发失败，不验证；原生能力等价不能推导agent行为等价。", "", "108格确认的SP/SF54份补审已完成：SP全属性4/27，SF3/27（数学均0/9；项目均2/9；图表SP2/9、SF1/9）。这是事后、已暴露评分的统一审查，原实验结论不改。数学代码与工具边界错误、项目空白最终答复，以及图表正确但数值总结错误均保留逐格依据。", "", "三份当前工具ZIP重新计算SHA全部匹配锁定记录；45队列原题投影无不符、相同题/阶段的原生catalog哈希无分歧。但catalog快照不是进程启动日志，也不能证明每次旧运行的可执行文件字节均已冻结。", "", "## 定向错误归因", "", "补审35份历史产物后，Swift编译检查确认：budget_feedback一份CardView声明直接复制了原生工具返回的无效示例；另一份List.onDelete错误未出现在已见工具返回中。Apple Swift6.3.3类型检查分别失败，一个CounterView对照通过。只检查代码，未执行程序。项目空答复与复杂度字段修改分别记录，不能从降低数字直接推断工作真正被拆分。", "", "独立24调用parser状态诊断发现无效调用保留旧诊断与位置，后续有效调用清空。最初怀疑的fresh-invalid崩溃未发生；不把状态现象写成产物错误根因。此诊断$0，不算开发通过。", "", "三项新开发已知费用合计$0.714163524，加历史去重下界$7.2084398105，共$7.9226033345；历史未知费用仍未结清。", "", "## 复算", "", "```sh", "uv run python scripts/review_confirmation_charts.py", "uv run python scripts/review_confirmation_math.py", "uv run python scripts/review_confirmation_projects.py", "uv run python scripts/review_reaudit_gap_charts.py", "uv run python scripts/review_reaudit_gap_math.py", "uv run python scripts/review_reaudit_gap_projects.py", "uv run python scripts/review_reaudit_daily.py", "uv run python scripts/review_reaudit_swift.py", "uv run python scripts/research_reaudit.py", "uv run python scripts/research_comparability.py", "uv run python scripts/research_cost_reaudit.py", "uv run python scripts/render_reaudit_report.py", "```", "",
        "上述均不调用模型、judge或MCP。离线哈希/分数复算不能替代语义产品审查；原生工具错误、模型输运错误、产品错误与审查代码错误必须分开记录。Top5名称已核实且候选自身逐属性审查覆盖完整：sufficiency_feedback39/39、budget_feedback34/34、observed_contract21/21、discovery_contract21/21、shared_contract_refs5/5。同队列SP缺口也已补审。其他登记项仍有明确标注的历史审查缺口；新方向及后续轮次仍待完成。新补的历史审查标注posthoc_scores_exposed，不能冒充盲态验证。审计映射修正见audit-corrections.json：不向未执行的准备计划挂载同ID后续产物审查。"]
    (E / "REPORT.md").write_text("\n".join(lines)+"\n")
    print("Rendered36-candidate audit with condition-level comparisons; unfinished work explicit.")


if __name__ == "__main__":
    main()

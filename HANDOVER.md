# PE6203 交付交接 · 2026-10-31

课程交付已冻结。四条获批诊断已经结束；PE +0.5 和历史 promotion gates 不属于课程要求。后续新增的完成率 / 任务质量研究另列在文末；现已单独获批文末限定的 12 条试验、原协议评分和预检，合计上限 US$1；**不自动扩展实验或部署**。课程验收仍需组内审阅及 TA 澄清，不以策略胜出为条件。

## 当前可交付内容

- 最新整合报告：[`submission/PE6203-final-report.pdf`](submission/PE6203-final-report.pdf)，可读 HTML：[`submission/report-final.html`](submission/report-final.html)。原报告、诊断附录、两个本机 ZIP 保留为历史快照，旧的“strict natural”措辞由本次 brief 核查取代。
- 27 条主实验和 135 个评分从归档独立复算一致。Patch 九个 PE：133 = 10/8/7，235 = 10/10/10，283 = 9/9.4/8.6；82/9 = 9.1111。它的 PE 最高，但 TF、ECS 和正常完成率不领先。评分与完成状态分开，历史分数未修改。
- 最新离线审计：[`submission/handover-20261031/audit.json`](submission/handover-20261031/audit.json)。完整原始轨迹路径、变化前后字段和实际调用均在其中或以下案例文件中。
- [共享 Slides](https://docs.google.com/presentation/d/1vcofhraTu_EJuhCm45WDVUMQzRFrY36T/edit)：13 页主讲 + 5 页 Q&A 附录，团队仍需排练 10 分钟讲解 / 5 分钟问答。当前讲稿见 [`speaker-notes-final.html`](submission/handover-20261031/speaker-notes-final.html)，机器版本为同名 JSON。
- 仓库未找到适用的 AGENTS.md 或已有 handover，因此创建本文件。入口仍为 README，细节保存在 submission/。

## 证据结论与未完成项

| brief 条款 | 已核实 | 未解决 / 下一步 |
| --- | --- | --- |
| §§2、4.1 三方法 | 原 No Update、确定性 Patch、全目录 Full Rewrite 均有实测轨迹；Early 共用 K0。 | Full Rewrite 重建全部目标记录，LLM 改写每条 description；schema、routing、output schema 和 usage rules 从目标元数据复制，并非每字段都由 LLM 生成。是否符合教师对“all knowledge regenerated”的预期，列入 TA 草稿。不能改实现后沿用旧成绩。 |
| §3.2 固定设置 | 3 tasks × 3 stages × 3 methods × 1 execution = 27。模型、温度、agent 预算、任务、judge rubric/槽位一致。 | 单次执行不支持总体显著性或广泛泛化；5 次 judge 不是 5 次 agent。方法同时改变更新范围与生成机制，不能解释为纯范围消融。 |
| §3.2 三类变化 | PARAM：133 validator；DESC：283 create_project；TOOL：283 Late 新增 workspace review，FR/Patch 各调用一次。 | TOOL 是可选新增，未测必需工具删除/重命名；部分新增工具零调用。描述被呈现、工具被调用不证明描述改写引起行为差异。详见报告覆盖表与 audit.json。 |
| §4.2 under-update | 受控删除 allow_variables 后 8 次缺参拒绝，完整条件 0 次；机制 confirmed。 | 这是人为修改已有知识快照，未证明原 updater 自身遗漏。TF 均 10，PE 5.8 vs 5.6，截断 vs 完成。brief 没有要求“自然发生”；人工注入是否足够作为课程案例仍待 TA 判断。 |
| §4.2 over-update | 一条 evaluate usage rule 保留时 22 次调用、PE 7.8、截断；回退时 4 次、PE 10、完成，但 TF 10→9.8。 | 该规则涉及变化后的 validator，语义上有关联。元数据未变不等于知识无关；单次对照不能确认规则造成损害。因此仅 suggestive，尚无已确认的“无关知识修改→正常行为受损”链条。 |
| §4.2 负例、成本 | 旧 6 条 chart 回退诊断均 TF/PE 10，负结果保留；已审计 317 条历史轨迹。主实验已知 $0.40691929208 + 1 笔未知费用；4 条诊断 $0.04600192，无未知项。 | 不将未知费用填零；不把上游缺陷、网络失败、judge 错误或预算耗尽自动算成补丁错误。完整账单需用户查供应商记录。 |
| §4.3 展示 / 提交 | 报告、来源、离线复算、Slides 和讲稿可审阅。 | 团队核对姓名/分工、排练、确认 TA 接受范围及课程提交记录。推送 GitHub 不等于已完成课程系统登记。 |

## 案例索引

- **U1 confirmed，仅 No Update 局部失败**：`submission/evidence/case-details/U1.json`。主实验 task133 Late，旧 schema 缺少 mandatory allow_variables，最初 4 次调用被拒绝，之后自行恢复。不能直接称为 Patch under-update。
- **U2 contradicted，原 Patch 漏参假说**：`submission/evidence/case-details/U2.json`。正确字段已存在，三次 validator 调用均传入，零工具错误。
- **受控 under-update**：`submission/diagnostics-20261031/exact-knowledge-diffs.json`、`audit.json`、`plan.json`；原始包 `submission/evidence/targeted-diagnostics-20261031.tar.gz` 内 `raw/cells/under_omitted` 和 `raw/cells/under_complete`。只删除 validator 属性及 required 条目，错误观察能直接支持缺参机制。complete 条件另外遇到 batch_evaluate 实现缺陷，四个 judge 理由错误声称工具不存在，分数保留。
- **受控 rule 对照，suggestive**：同包 `raw/cells/over_note` 与 `raw/cells/over_reverted`。只回退一条 evaluate usage rule，其他三个历史规则保持相同。它是历史 linked_notes 变体，不能冒充主实验 Patch；没有证明规则“无关”。
- **O1 suggestive / O3 inconclusive**：`submission/evidence/case-details/O1.json`、`submission/evidence/diagnostic-review.json`。历史 FR 重写未变化的 28 个 chart 描述并低分，但 dataValueUnit 指引仍在；六次反事实未复现损害，3 份答案的算术错误分布在两组。不能用这个例子宣称 Patch over-update 因果已确认。
- **O2 suggestive**：`submission/evidence/case-details/O2.json`，旧 linked_notes 有四个记录同时不同，比本次单规则对照混杂更多。
- 主实验归档：`results/evidence/course-v1.3-20261031/raw-trial.tar.gz`，前缀 `course-v1.3-final-20261031/cells/`。知识在各 cell 的 `adaptation/knowledge.json`，调用/观察在 `run/raw_trace.json`，评分在 `run/EVAL/` 和 `judge-attempts/`。诊断原始包的路径以实际 raw-manifest.json 为准。

## 待 TA 确认的问题草稿（未发送）

1. brief §4.2 要求 under-update 轨迹。我们从正确的更新知识中受控删除一个必需参数，确认 8 次对应拒绝和最终截断，完整条件没有缺参拒绝；但这是 fault injection，且 TF 没降低、PE 没改善。明确披露这些限制后，是否可作为该类失败分析？是否还要求证明开发的 updater 自身会遗漏？我们不假定必须自然发生，也不假定注入自动合格。
2. over-update 定义要求修改无关知识并损害正常行为。现有一条规则对照涉及语义相关工具；历史未变化 chart 描述的回退实验未重现损害。可以提交提示性案例、负结果与未证实结论，还是需要另一个有直接证据的案例？我们不会把相关工具等同于无关知识。
3. Full Rewrite 对完整目录所有记录重新构建，LLM 改写全部 description，schema/output schema/routing 取目标元数据，usage rules 原样保留。这是否满足 §§2、4.1 的完整知识再生成，还是希望 usage rules 等文本也重新生成？现有结果仅代表已描述实现。
4. 当前子集实际调用覆盖 PARAM、DESC 与 TOOL 新增；新增工具是可选的 workspace review，FR 成功而 Patch 因上游缺陷失败。必需删除/重命名、某些新增工具未覆盖。这样的有限覆盖是否符合 §3.2，还是期待特定子类型？

## 离线复核与禁止自动执行的边界

从 repo 根目录运行（Python 3.12+ 标准库，不需要 key、依赖下载或网络）：

```bash
python3 submission/handover-20261031/verify.py
```

脚本重建 10,959 个冻结历史文件到临时目录，复核 27 主轨迹 / 135 评分、209 条 FR 描述、三类目录差异及实际调用、72 个候选 / 9 个深审案例 / 6 个旧负诊断，并独立复算 4 条新诊断 / 20 个评分。输入只读，网络显式禁用。新增 `corpus-extra.tar.gz` 仅补足 19 个原归档未含的 424 个历史文件，不含新实验。

原 205 MB 主 ZIP、2.2 MB 诊断 ZIP 和原 PDF 仍是冻结快照，未覆盖；不要重新运行它们的打包脚本去混入后来结果。GitHub 通过既有历史归档、补充日志包和源码包提供复核输入；大型 ZIP 不进入 Git。当前整合报告与本 handover 优先于旧包的交付状态叙述，评分与费用数据仍以原始归档为准。

已取消 `.env copy` 跟踪并保留本机文件，避免在最新提交树继续分发凭据。旧 Git 历史已包含该文件；删除最新版本不会撤回旧凭据。用户应轮换其中仍有效的 key；本次不擅自操作账户或重写共享历史。

下一位接手者先查看本文件、最新报告与 `submission/handover-20261031/verification.json`。未得到用户新批准，不运行 experiment/driver/preflight，不重评已有轨迹、不扩充实验、不部署 Netlify。TA 回复如要求补充，先提出最小、独立计费的方案再获批执行。

## Git 交付回执

主交付已通过非 force push 合并到 main：`e95b51a3601a5966d06f05ae1e729f8e8bad60f9`。远端 ref 已核对，GitHub Adapter checks 成功；核查内容提交为 `61a3cf3`。本节和 [`delivery.json`](submission/handover-20261031/delivery.json) 的后续记录提交仅补交付回执。当前未解决项仍以上表为准，没有宣称课程验收已完成。

## 后续研究：完成率与任务质量（独立，12 条已批准）

用户新增目标是找到完成率和任务质量更好的策略。工作位于 `codex/completion-quality-study`，基于已推送的 main `ef96d08`；此研究尚未合并或推送，不修改冻结课程报告、Slides 或历史评分。

- 先验证已有 `budget_feedback`，没有新增策略实现。18 个 task/stage/arm 知识条件完成离线检查；12 个 Middle/Late 条件与历史归档相同，Early 和 task235 保持精确 K0。
- 已新增只读提取器 `scripts/audit_completion_quality.py` 与测试。它读取归档中的原评分、实际完成状态、调用、费用与持久化任务，不产生新 judge 分数。事实包位于 `results/evidence/completion-quality-20261031/development-v3/facts.json`，知识检查为同目录上一级 `freeze-audit.json`。
- 历史开发结果：budget_feedback 6/6 正常结束、TF 10；原 Patch 5/6、TF 10。候选 task283 Middle 的最终复杂度概述与三个里程碑数据不一致，故没有宣布质量改善或策略胜出。低任务数、低自报复杂度和高 judge 分数均不能单独证明质量。
- 已批准协议：`experiments/completion-quality-v1.json`；人读版 `reports/completion-quality-plan.html`。提议 3 tasks × Middle/Late × 2 arms × 1 repeat = 12 条，60 个原协议评分槽；不定义自动确认阶段。预计 US$0.12–0.30、10–20 分钟，已批准上限 US$1，费用与时间预估基于旧账单。
- **批准记录：**用户回复“批准这 12 条，费用上限 US$1”；见 `results/evidence/completion-quality-20261031/approval.json`。`configs/completion-quality-v1.json` 复制原模型/预算协议，仅新增相同的价格路由限制及 `spend_guard`。每个请求在发出前保守预留全上下文 + 最大输出费用，费用未知或不足时停止；SDK 内部重试禁用。公开价格依据在 `pricing.json`，未修改账户设置。
- **下一步：**完成冻结输入核对后执行这一轮，保留所有中断及费用；不得超过 12 条或自动重新运行低分轨迹。费用保护覆盖 agent、judge 和预检，受供应商公开上下文与 max_price 合同约束。
- 判定要求：变化任务完成数增加；原 TF 均值不降低；有独立于完成状态的产物/答案正确性改善，且无实质性质量退化。若质量持平或证据不足则 hold。不能用 PE +0.5、任意加权分、删除网络失败或重新标记历史实验得到赢家。
- 后续 Early/ECS、No Update/Full Rewrite 的新同期比较、重复或新任务均须另行提出成本与证据收益并获批。本轮没有 Early，不拼接旧 Early 冒充新 ECS。已有课程完整矩阵只作为注明时间与实现版本的历史参照。
- 上文 TA 问题与 over-update 证据缺口未关闭。性能研究不自动满足这些课程验收事项。

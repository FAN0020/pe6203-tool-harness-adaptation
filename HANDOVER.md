# PE6203 交付交接 · 2026-10-31

**最新授权：用户要求“请不要设置上限和额度限制，以完成任务为优先目标”。后续研究按证据继续，不设总费用/轨迹额度；保持逐条记账、公平执行设置及历史证据。下文各轮限额及等待批准的表述仅描述当时状态。最新已完成协议：`experiments/evidence-scope-v1.json`；不含部署授权。**

课程交付已冻结。四条获批诊断已经结束；PE +0.5 和历史 promotion gates 不属于课程要求。后续新增的完成率 / 任务质量研究另列在文末；文末获批的 12 条试验已执行并归档，总费用 US$0.1572164470；**授权已用完，不自动扩展实验或部署**。课程验收仍需组内审阅及 TA 澄清，不以策略胜出为条件。

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

## 后续研究：完成率与任务质量（12 条完成，未晋级）

工作位于 `codex/completion-quality-study`，基于已推送的 main `ef96d08`；此研究仅本地提交，尚未合并或推送。课程报告、Slides、27 条主实验及所有历史评分保持冻结。

- 用户明确批准“这 12 条，费用上限 US$1”。按原计划验证已有 `budget_feedback`，没有新增策略。3 tasks × Middle/Late × 2 arms × 1 次，12/12 轨迹、60/60 原协议评分已结束。两组正常完成均 **4/6**（变化任务 2/4、保持任务 2/2），133 Middle 均截断、283 Late 均耗尽轮数。
- 原 Patch：TF **9.9667**、PE **9.0**、agent+judge **$0.0726556104**；候选：TF **10**、PE **8.8**、**$0.0845529246**。共享预检 $0.000007912，合计 **$0.1572164470**，未知费用 0；69 agent + 60 judge + 2 preflight = 131 请求，约 10.56 分钟。更新无模型调用、无新增探测。没有 Early，不计算新 ECS。
- **判定：未证明完成率与任务质量同时改善，不晋级。** 候选图表答案的部分算术更准确，283 Middle 容器解释更清楚；但两个保持格的地图缺少金额单位，133 Middle 误把不支持 `**` 推断成不支持指数及消除 DoS。原 Patch 也有月度合计和安全代码测试错误。没有改 judge 分数；逐属性 pass/fail/unknown 与证据均保留。
- **公平性限制：**模型 ID、解码、任务、预算、judge 协议相同；57 个冻结输入和执行前源码哈希未漂移，task235 两组是精确 K0。但 OpenRouter 实际后端供应商不同，工作目录也含策略名；冻结协议“只有知识不同”的措辞过强。原协议保留，结果报告明确补充这项限制，不能作纯补丁因果结论。相同 K0 下的输出差异不能证明适应机制造成保持退化。
- **可读入口：**[`reports/completion-quality-results.html`](reports/completion-quality-results.html)。完整证据目录：`results/evidence/completion-quality-20261031/`：`raw-trial.tar.gz`（500 文件）、`raw-manifest.json`、`source-98c4f8e.tar.gz`、`trial-verification.json`、`trial-facts/facts.json`、`quality-review.json`、`artifact-checks.json`、`post-run-input-verification.json`、`reproduction.json`。知识/工具/调用在原始包，五个 judge 原始分值逐格披露。
- `quality-review-template.json` 是填表前模板，最终状态以 `quality-review.json` 为准。`protocol-audit.json` / `verification.json` 是批准前快照；`approval.json` / `approved-verification.json` 是执行前批准及核验。勿将快照状态当成当前状态。
- 冻结执行代码为 `98c4f8e`。`experiments/completion-quality-v1.json` 与 `configs/completion-quality-v1.json` 未因结果修改。请求级费用预留和相同 provider 价格上限已覆盖全部调用；账本已结算，未触发预算封锁。供应商接口价格/上下文约定仍是保护前提。
- **未完成：**没有找到本轮标准下同时改善两项的策略。上文 TA 接受范围、over-update 因果证据和 Full Rewrite 解释仍未解决。不能用本轮 TF 接近满分关闭这些问题，也不能把旧开发阶段的 6/6 代替这轮 4/6。
- **下一步：**先审阅本报告。课程可按已有交付推进；若继续性能研究，先提出针对后端控制、截断和知识边界的最小方案、费用和预期证据，再单独获批。当前没有新候选、重复或扩展获批，不恢复旧 R2/R3，不重跑低分，不部署，不自动改课程 Slides。

本轮离线核查（只用 Python 标准库，不启动模型或服务）：

```bash
python3 results/evidence/completion-quality-20261031/verify_trial.py > /tmp/pe6203-trial-verified.json
```

原始包 SHA-256：`9954a1039a946f7e7bd46c39e56b1ce63cb35d1d188941d3889b5a5b4370d9b6`。源码包不含安装后的全部依赖；原 CLI 命令只是历史复现说明，不是新增付费调用的授权。


### 下一候选的离线提案（批准前历史快照；当前状态见下节）

上一目标回合属于 progress：12 条真实试验得到新反例并完成归档。随后离线追踪确认：预算规则已注入，但不含具体 12 轮 / 4096 token 限额；133 Middle 在最终答案处截断，283 Late 无工具错误仍逐组扩写到轮数耗尽。因果修复仍是待检验假说。

- 已拟且仅拟一个 `budget_contract`：以 `budget_feedback` 为对照，只替换一条预算规则，明确限额、先覆盖所需工作再细化、预留核验/汇报；不提高预算、不放宽质量属性、不修改不变工具。候选尚未注册到运行框架。
- [可读提案](reports/budget-contract-proposal.html)；`results/evidence/budget-contract-proposal-20261031/proposal.json` 为机器方案，`knowledge-diffs.json` 是精确差异，`mechanism-evidence.json` 是逐轮证据。9 个静态知识条件仅替换原有 29 处规则；5 个 Early/retention 条件保持 K0。复核：`python3 results/evidence/budget-contract-proposal-20261031/verify_preview.py`。这些不是新轨迹或新质量分数。
- 拟申请 6 条：133 Middle、283 Late、235 Middle × 原 budget_feedback / 新候选，各 1 次；30 个原协议评分槽、至多 2 次可用性预检。拟固定 DigitalOcean 端点、禁止 fallback，使用不含方法名的 cell/workspace IDs。公开端点元数据已读取，无凭据、无推理调用；真实端点可用性仍未测试。
- 预计 US$0.15–0.40、5–12 分钟，申请独立 US$1 上限。先前 12 条批准不能复用于这一轮。完整路径也已说明：初筛阳性后，与原 Patch 的完整 Middle/Late 对照最多再需 9 条；若将新方法列为课程主结果，匹配三阶段及 No Update/Full Rewrite 最多再需 21 条。均须另批，阴性/不确定即停，绝不自动执行后续矩阵。
- **当前等待事项：**用户批准或拒绝这 6 条及单候选接入。在回答前不注册新策略、不预检模型、不评分、不运行新实验。独立可做的设计、差异检查、费用估算和文档已完成；仍没有验证出符合双重改善目标的策略，课程 TA 缺口也未关闭。


### 六条 budget_contract 试验（已完成，停止，不晋级）

用户随后批准“这轮目标能够完成都可以批准”，范围按此前问题限定为单候选接入、6 条轨迹、30 个有效评分槽、至多 2 次预检、独立 US$1 上限；不是承诺结果必为正或无限扩展。批准记录在 `results/evidence/budget-contract-proposal-20261031/approval.json`，原提案快照保留。

- **实现与核验：**源码冻结 `418ed2b`，协议 `experiments/budget-contract-v1.json`，配置 `configs/budget-contract-v1.json`。只替换原预算规则，133 Middle 5 处、283 Late 11 处、235 Middle 0 处，与批准预览完全一致。两组固定 DigitalOcean、禁止 fallback，使用不暴露方法名的 cell 路径；12 轮/4096 tokens 等实际预算不变。333 项离线测试通过；全部 57 项冻结输入在执行后仍匹配。
- **结果：**指定三对均完成，6/6 轨迹和30/30评分。对照 budget_feedback：完成3/3、变化任务2/2、保持1/1，TF **9.9333**、PE **9.7333**；候选 budget_contract：相同完成数，TF **9.8667**、PE **8.9333**。无 Early，不计算 ECS。不将当前成功与旧失败拼成修复效果。
- **费用：**61 请求＝29 agent +30 judge +2 preflight，全部实际响应为 DigitalOcean。总计 **$0.089010216**，未知项0；约3.83分钟 API 执行窗口。对照 agent/judge $0.033376212/$0.010540008；候选 $0.033273108/$0.011807928；共享预检 $0.00001296。确定性更新无模型调用。费用来自响应，未另核账户账单。
- **质量：**283 Late 候选的35=6+29任务及204h汇总准确；对照M3写67h但落盘79h，并虚构一次参数失败。候选133却误把不支持 `**` 推断为没有指数，把解析与求值混淆，其示例MAX_DEPTH检查不递增深度。保持任务两组数据与单位均保留，但渲染图未存档。候选改名已拆分父节点后警告清零，仅能说明分析器对文本敏感，不能据此认定根因解决或已确认over-update。20属性为12 pass/4 fail/4 unknown，未合成分数；judge错误独立记录，原评分不改。
- **判定：**本轮未证明完成率与任务质量同时提高，不晋级，停止新增调用。单次已暴露任务、后端内部版本未知、规则内多句无法独立归因；不能泛化。仍没有达到双重改善研究目标。
- **审阅：**`reports/budget-contract-results.html`；完整证据 `results/evidence/budget-contract-20261031/` 含原始包（262文件）、哈希、源码包、独立复算、产物事实、质量审阅、judge审计、执行环境及命令。原始包 SHA-256 `b82b34719e304d3037ab465ecfe1bc46c7d1ff9be0712b1123623a39600c115a`。本轮只在 `codex/completion-quality-study` 本地提交；未合并/推送main，未改课程PDF/Slides，未部署。
- **下一步和边界：**可独立审阅本报告；本轮没有剩余实验。后续重复、候选或扩展均未获批，不运行既提到的9/21条或旧R2/R3。课程原有TA接受受控under-update、无关知识over-update因果证据、Full Rewrite解释与工具删除/重命名覆盖缺口均未关闭；问题草稿仍在既有交付中，不发送。

离线复算（零模型调用）：

```bash
python3 results/evidence/budget-contract-20261031/verify_trial.py
```


### 最新：取消总额度后的补充对照（已完成，质量仍未过关）

本节取代上文历史“未获批9条/后续每轮必须另批”的当前授权表述。用户明确要求“请不要设置上限和额度限制，以完成任务为优先目标”；后续证据驱动的必要研究不再申请每批费用额度。单条12轮/4096 tokens等公平执行条件固定；部署、给TA/他人发消息不在授权内。无总费用/总轨迹硬上限，不等于无假说地自动展开矩阵。

- **已执行：**既有budget_feedback vs原Selective Patch，补9条、45评分，复用前一六条试验中的候选133Middle、235Middle、283Late；无新候选、探测或updater模型调用。全部新调用DigitalOcean，正常端点，103请求（含2预检）。新费用 **$0.151974408**，未知项0；465.04秒。前三轮新增研究合计已知$0.398201071，不含更早课程/历史研究。
- **合并12格独立复算：**候选完成 **6/6**、变化任务 **4/4**、保持 **2/2**、TF **9.8**、PE **9.2667**；原Patch完成 **2/6**、变化任务 **0/4**、保持 **2/2**、TF **9.4**、PE **8.3667**。两阶段不算ECS。没有Early/NU/FR新全矩阵，不替换课程主表。
- **证据支持的收益：**同批次283Middle候选的36=4+32记录、356h及73/69/104/110h分项均准确，并真实拆分两项工作、新增四个任务；原Patch在M3耗尽轮数，M4–M8只有空里程碑。
- **仍未过质量检查：**候选133Late完成但示例字典语法错误，字符过滤拒绝其合法sqrt测试，AST括号深度建议错误。候选235Late的年度合计及江苏服装数字错误；原Patch图表总结也错误。复用283Late的67vs79h及虚构失败、133Middle的安全完整性未知仍保留。故**不晋级，双重改善完整目标尚未完成**，不因TF/完成率较高启动81/108条确认。
- **公平性限制：**三条来自已看过结果的前一批次，且本轮移除总费用/单价准入上限、改变账本路径；完整执行协议哈希因此不同。模型、解码、judge实现/规则、工具版本与知识不变。不能称为纯同时随机对照或全部配置相同，旧12条两组4/6的负结果仍有效。新旧批次各一份完整协议哈希已独立重算。
- **工具/评分异常：**上游Middle的file-storage.js第53/56行console.log迁移信息触发JSONRPC警告；执行继续，未证实影响耗尽。原Patch一次create_subtask虚构父ID导致拒绝。所选judge理由错误已单列，旧分数未修正。完整控制台流未单独存档；调用、观察、产物与费用均在原始包。
- **审阅与复现：**`reports/matched-existing-results.html`；`results/evidence/matched-existing-20261031/`含382文件原始包、源码包、逐文件哈希、独立verify_trial.py、check_artifacts.py、trial-verification.json、quality-review.json、judge-audit.json、runtime-observations.json、reproduction.json。原始包SHA256：`6f1d6a5bbcf78f076793faf74f466d3050f133491793e8154a86a3936800e837`。执行源码 **f896388**，339项离线测试通过；本轮无运行中的实验。
- **接手下一步：**先读报告与最终quality-review.json；设计一个针对变化工具证据边界的修正，避免把工具语言验证当成已验证的Python实现或安全保证，明确何时仅需建议而非生成完整实现。先冻结具体diff和质量检查，再做针对性配对验证；不修改相同K0来“修复”保持任务的随机错误，不重新包装旧成功为新验证。不设资金/轨迹总帽，也不盲目重复直到赢。候选全阶段验证、under/over案例适用性与TA问题仍未完成，原草稿未发送。

本研究仍在`codex/completion-quality-study`本地分支；课程main、PDF与共享Slides不因探索结果自动改写。


### 当前研究：evidence_scope 局部证据规则（执行前冻结）

沿用最新无总额度授权。只在budget_feedback的变化/新增记录中追加一条固定证据边界usage rule，防止将工具观察扩展为未经验证的实现、可选汇总或虚构执行历史；保留原任务全部交付，不改模型/预算/评分。三个Late条件133/235/283 × 原budget_feedback/候选，各1次，6条同批次配对、30个原评分槽；预计$0.10–0.30、5–12分钟，均为估算。此阶段检查质量修复并保持完成率，不要求击败已经满完成率的budget_feedback；最终目标仍须对原Patch和课程基线完成三阶段验证。

协议`experiments/evidence-scope-v1.json`，配置`configs/evidence-scope-v1.json`；精确规则和九个task-stage知识差异在`results/evidence/evidence-scope-pilot-20261031/offline-knowledge-checks.json`。五个Early/retention条件均为精确K0。Late133追加10条、283追加11条、235为0；其余字段逐项与budget_feedback一致。340项离线测试通过，尚未据此宣称行为改善。结果归档后以新结果节为准，不启动自动网格或108条确认。


### evidence_scope 六条配对（完成，不晋级）

- 冻结源码 `422178236198454f673748a782550a4438e81d44`；`experiments/evidence-scope-v1.json` 与同名 configs。3 tasks × Late × budget_feedback/evidence_scope，每格一次；没有复用旧agent轨迹、增加探测、部署或改评分。
- 新候选1/3正常完成（变化0/2），对照2/3（变化1/2）；TF9.6/9.8，PE9.0667/9.4667。候选133截断，两组283耗尽12轮；235均完成且知识精确K0。不能推广之前6/6成功，更不能把judge高分当正常结束。
- 64请求=32 agent+30 judge+2预检，全为DigitalOcean；已知$0.107351724、未知0，269.35秒。总费用/轨迹额度仍为null；单轨迹公平预算保持。更新0模型tokens/调用/$0，合计1.0873秒。
- 归档265文件含console：`results/evidence/evidence-scope-pilot-20261031/raw-trial.tar.gz`，SHA-256 `ecf66965bbdb672cba6a4a3192491bb951edb49ca85329ffa2e86afb4b85a130`。同目录含独立verify_trial.py、trial-verification.json、quality-review.json、artifact-checks.json、judge-audit.json、reproduction.json及冻结源码包。57个输入和知识锁复核无漂移。
- 可读报告：`reports/evidence-scope-results.html`。候选仍扩写未请求的数学实现；283十次缺workingDirectory，但字段已在知识中。两组283有真实拆分和有效引用，但无最终回答。保留工具实现缺陷、judge描述不存在最终答复等反证，不称已确认under/over-update。
- **后续先查原因：**规则重复/长度、参数契约落实、输出与轮次预算；不继续叠加同类泛化提示。课程27条/PDF/Slides仍冻结。TA问题及研究目标尚未解决；本轮阴性，不可写成已找到稳健策略。最新授权允许必要研究继续，无需按旧额度逐轮询问，仍不部署。

离线复核：`python3 results/evidence/evidence-scope-pilot-20261031/verify_trial.py`。

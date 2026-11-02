# selective V6-r1 源码只读审查

日期：2026-11-03（Asia/Singapore）。仓库 `/Users/q/Desktop/tool-selective_patch/V6`；分支 `selective-V6-r1`；修订标签 `v6-r1-protocol-and-delivery`。审查当前四个 tracked diff、两个新增模块与三个新增测试文件。没有修改仓库、切分支、调用模型/API或运行实验；本 worker 未重复主窗口正在运行的离线回归，也未把阅读测试代码说成测试已通过。只写本报告。

**结论：当前 diff 中未发现跳过候选、放宽最终 snapshot 验收、暗改无 flag 基线、或把被撤回提案伪装成已解决行为的阻断性问题。** 重复候选合并是有验证的规范化；publication 是新方法中明确的规则级弃权，不是让原不合格规则直接通过。最终 `validate_adaptation`、既有 Docker 产物验收及 judge 未变。下面列出仍需在冻结方案/归档中落实的边界与建议。

## 1. 具体发现与建议

### [P2] 交付 flag 未绑定 r1 修订标签，容易误用旧 V6 知识产物

位置：[runner.py:478](/Users/q/Desktop/tool-selective_patch/V6/src/pe6203/runner.py:478)。目前只检查 `strategy=selective_patch`、`pipeline_version=hybrid_v6`，后续确认 adaptation validated；不要求 `implementation_revision=v6-r1-protocol-and-delivery`。所以旧版已验收 V6 adaptation 加上新 flag，也可得到新交付协议。

这是防误用/归因边界，不是默认基线已被改变：没有 flag 的旧结果不会自动启用。建议在新 r1 批次准备/验收器中强制检查每个 adaptation 的修订标签及冻结源码；如果该 flag 被定义为只适用于 r1，也可在入口增加该一致性检查。否则报告只能按“旧知识+新交付”混合配置命名，不能把它算作完整 r1 更新方法。

### [P2] `validated` 代表结构与证据范围通过，不能把弃权统计成“迁移语义全部恢复”

位置：[publication_v6.py:29](/Users/q/Desktop/tool-selective_patch/V6/src/pe6203/publication_v6.py:29)、[selective_v6.py:475](/Users/q/Desktop/tool-selective_patch/V6/src/pe6203/selective_v6.py:475)。被撤回的规则留在 `withdrawn_proposed_rules`，替代规则类型为 unknown，`unresolved_items` 会收集包含 unknown/conflict 的 patch，artifact 又保存该列表。这条链条当前是诚实的。

建议最终表并列列出：snapshot validated、被撤回提案数、unknown/conflict 的工具数、正常最终答复、产物测试。一个条件即使全部新拟议规则都被撤回，也仍可能在结构上 validated；不能只报“更新成功率上升”而不展示未决项，或称其已经建立正确替代行为。建议加一个端到端离线 fixture：全部新规则撤回后明确 unresolved，原提案仍在 audit，最终校验完整运行。

### 规则级撤回的约束保留上限须准确表述

位置：[publication_v6.py:22](/Users/q/Desktop/tool-selective_patch/V6/src/pe6203/publication_v6.py:22)。retained 前缀逐字保留；被过滤的是新拟议的整条渲染规则。如果某一条新规则同时写“不要调用 retired”和一个有用的独立约束，两者会一起撤回，actor 只看到通用 unknown，具体文字只在审计中保留。

这符合当前“宁可弃权、不发布带删除引用的新规则”的设计，不是静默截断；但不能据此声称新提案的所有可用约束都被保留。代码也没有证明 LLM 的 retain/withdraw 决策保住了所有语义上不受影响的旧约束，这是既有语义检查上限。建议新增混合内容规则的 fixture 并在方法说明中写清“整条新规则弃权”；不要用程序未经证据的文本切分去猜测安全子句。若强制要求保留其中的独立约束，需要另有有界、可审查的提案步骤，不能把当前实现描述成已解决。

### strict JSON + 工具调用的供应商可用性尚未由本次源码审查建立

位置：[execution_control_v6.py:68](/Users/q/Desktop/tool-selective_patch/V6/src/pe6203/execution_control_v6.py:68)。启用产物协议时每一生成轮都带 strict JSON，前 11 轮仍允许工具调用；第 12 轮加 `tool_choice=none`。新增测试覆盖“第一轮直接交付 JSON 后 repair”，但所读测试未覆盖“artifact 模式先工具调用、再最终 JSON、再一次原有 repair”的完整组合。

建议离线补齐该组合的请求形状/保留历史/预算断言。它只能验证适配器逻辑，不能证明实际服务商同时支持这些参数；真实执行若拒绝、截断或违反 tool_choice，应原样保留失败与费用，不能通过去掉参数后暗中另跑来形成好结果。本 worker 没有发探测请求。

### 归档必须包含新增模块

`runner.agent_loop` 无论 flag 是否存在都会导入 `execution_control_v6`；当前文件在工作树存在，但审查时它与 `publication_v6.py` 仍是 untracked。正式提交/源码归档必须包含二者及测试。若仅按 tracked diff 打包，基线也可能因缺少无条件导入模块而失败。这是打包完整性建议，不是当前工作树发生的失败。

## 2. 逐项安全性与完整性检查

| 改动 | 只读核查结果 | 证据位置 |
| --- | --- | --- |
| 重复候选合并 | 每一 occurrence 都检查 ID、category、reason、basis 和 evidence selector；basis/fields 取并集，reason 去重合并但不截断；有 uncertain 时保留 uncertain。非法第二条不会因重复而被跳过。 | `payload_v6.py:133–233`；`test_v6_revision_transport.py` |
| 必选与覆盖 | `covered_tool_ids` 仍需对 surviving catalog 精确且无重复；mandatory 候选与其 basis 强制补齐；所有 merged rows 进入 detail/batches，最后 selected ID 与 admitted ID 精确匹配。 | `payload_v6.py:174–247`；`selective_v6.py:367–442` |
| 证据作用域 | 新 schema 只枚举 packet 中 evidence/basis/selected IDs；真实 ID 不自动证明语义，原 admit_patches 仍校验 own/basis 引用、规则引用子集和每条 patch。extra evidence 仍由 detail_packet 检查 candidate/change scope。 | `output_v6.py:95–120`；`rules_v5.py`；`payload_v6.py:263` 起 |
| publication 顺序 | 先 `admit_patches`，后撤回带删除引用的新规则；未知规则用已验收的 patch evidence IDs 渲染，未捏造证据、未插入缺少的模型引用。规则数只会相同或减少，仍不超过原 8 条上限。 | `selective_v6.py:410–417`；`publication_v6.py:19–46` |
| retained 规则 | 不进入 withdrawal 过滤；若 retained 本身仍有删除引用，最终校验仍拒绝。新增单元 fixture 明确断言这种情况不能被 cleanup 洗过。 | `publication_v6.py:22–24,43`；`test_v6_revision_publication.py` |
| 原始提案 | `_call` 的原始 response 保留于 attempts；每条被撤回结构化 rule、渲染文本、tool ID、proposal index 和 resolution 均在 audit，patch 自身也保留 withdrawals。 | `selective_v6.py:_call`；`publication_v6.py:30–45` |
| 最终验收 | `validate_adaptation` 调用保留，metadata/routing/工具集合/未改记录/删除引用等检查不变；argument cases 仍运行。publication 不过滤最终 errors。 | `selective_v6.py:450–468`；`selective.py:472` 起 |
| 基线默认行为 | flag 缺失时 settings 返回 None、generation_options 返回空；不追加 system/reminder、不加 response_format/tool_choice、不写 V6 冻结文件。所读 baseline 请求形状测试直接断言原 system 文本及参数不变。 | `runner.py:171–224`；`execution_control_v6.py:22–36,68–78` |
| 交付预算 | 末轮占原 max_rounds，不增加轮数；早答复正常停止；length/content_filter 不额外补交付轮；模型在保留轮仍提工具时保存 response 与违规事件后失败，未执行该工具。 | `runner.py:213–256`；`test_v6_revision_execution.py` |
| 原产物测试 | extractor、Docker backend、测试函数及原 repair 循环无 diff；repair 新增 strict JSON 格式，仍 completion-only，无工具参数，结果仍重新经历原产物验收。设置并未强制新预算，因此正式 plan 仍须冻结原 max_repairs=1 等额度。 | `runner.py:294–367`；`artifact_validation.py` |

## 3. 评测解释与冻结事项

这次同时改变 updater 的传输/候选规范化/发布弃权，以及 actor 的交付协议。完整重测可以评估 **V6-r1 整体系统**；没有消融不能把 TF/PE 变化单独归因于知识更新或 publication。不能与旧 V6/旧基线混写成同一执行协议；对照即使保持历史行为，也必须在结果表明确说明 V6-r1 得到的附加交付约束。

“最终答复正常完成”仍不等于所有需求满足或代码安全；unknown 仍是未决，有限 Docker tests 仍不是安全证明。冻结时需要固定完整源码（含新模块）、implementation_revision、是否启用 delivery flag、相同任务/rubric/测试哈希、生成预算/repair 额度与新结果目录。原 V6 结果与失败保留；真实实验结果不属于本报告结论。

审查快照 SHA-256（父窗口后续修订若改变这些文件，需相应更新审查范围）：

```text
payload_v6.py            8fbb8a5f1fad7f9fad39b1c71d2704209bf073b2fc1e8982ad7886c8d23f97b2
output_v6.py             117ee98ec43d5ac5edfd4057e52cd32748642da75579304957bb39b3413e9d78
selective_v6.py          56764330831851dc30bd00b3467dc39b229baec85f31800891d74c73aaa35397
publication_v6.py        4562324cc61deb7e68ce25f7ff54f1267fc76380d8f6d755258d9cfdd1c577e2
runner.py                d98ed9c99592fbd11b0db789513ac44f467a93382db4c717f3f68213ba731baf
execution_control_v6.py db81c7ea34f02d22da15701f3127b0d08b2b20d6b0292e01443bc61d1d22e6f2
```

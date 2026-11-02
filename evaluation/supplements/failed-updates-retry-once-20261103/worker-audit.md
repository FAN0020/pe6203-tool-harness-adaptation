# PE6203 失败更新一次重试：只读方案审查

日期：2026-11-03（Asia/Singapore）。仓库 `/Users/q/Desktop/tool-selective_patch/V6`，分支 `evaluation-five-task-20261103`。worker 只读检查脚本、冻结计划、既有原始文件与当时生成的输出；没有模型/API调用、导入执行实验模块、重跑、修改方法/评分/原始文件或 Git 操作。本报告是协议与中途快照审查，不是最终实验验收。

**结论：目前方案落实了“固定全部失败条件，各额外一次更新，成功后固定三次 actor，所有有效分数均纳入”的探索性补充设计，没有发现按分数择优、覆盖原结果、重复到成功或把未知费用当成完整零费用的路径。它仍是观察失败后的恢复实验，不能美化成原来一次尝试就成功的主评测。**

## 1. 范围和原记录保护

- 独立比较 `evaluation/supplements/five-task-20261103/five-task-coverage.json` 中 V2/V3/V5/V6 的 TF 或 PE 缺失集合与新 plan：完全一致，无额外成功条件、无遗漏。
- 固定集合共 7 个：V2 283-Late/430-Late/90-Late；V3 283-Late；V5 133-Middle；V6 430-Late/90-Late。21 个唯一 actor ID，每条件恰有 r1/r2/r3 三条。
- 7 个 `original_record_hashes` 与磁盘文件全部相同，状态仍为 failed/adaptation_failed。189 个冻结源码文件、8 份目录输入及 1 份 V3 能力证据哈希全部匹配。冻结知识 11 份文件也全部匹配。
- 新脚本只往新批次目录 `results/raw/failed-updates-retry-once-20261103/` 写 adaptation、runs、summary、CSV、verification；没有向旧原表写分数的代码路径。`prepare` 拒绝已有目录；`execute` 看到已有 `api/` 即拒绝再次执行。
- 保护边界须精确：哈希防护覆盖的是 **7 个原失败锚点文件**，不是所有历史 trace/评分/主表的全量文件树；原文件检查位于执行前、finally 和显式 verify，不是每个请求前持续监控。因此可说“这 7 个原记录当前未变、脚本无覆盖旧表路径”，不宜扩大成“任何历史文件任意时刻变化都会立即停止请求”。
- 历史 V2 另有 `task133-middle-full_rewrite-r0.json` 更新失败。它属于 Full Rewrite 控制组，不在本次用户指定的四版本范围；未重试并非遗漏四版本条件，但不能声称本次重试了所有版本和所有对照的所有失败。

## 2. 重采样、核心更新器与纳入规则

读取 `scripts/retry_failed_updates_once.py`：`adapt_once` 对冻结的七行各调用一次 `write_adaptation`，模式显式为 `hybrid_v2/v3/v5/v6`；无外层 while/until-success，无过滤/修复无效候选，无 fallback 知识。方法自带有限内部阶段/修订可以产生多次 API 请求，“一次更新重试”不等于“一次 API 请求”。

把 plan 中所有 `src/`、`integration/` 源码哈希与上轮 V35 及 430/90 supplement 冻结计划逐项比较：均相同。未发现这次重试修改核心更新器或其内部额度。V6 仅将原有请求出口接入 `Guard.structured_updater` 保留计费和结构化响应；没有替换候选验收核心。

actor 使用既有 `common.actors`：只有 adaptation validated 才运行；失败则写 blocked-cells；每次执行有唯一新目录，遇中断目录拒绝自动重跑；一次更新知识冻结后给三条 actor 共用。judge 仍是每 actor 5 个槽、每槽最多两次、首个有效评分；其格式恢复不算第二条 actor。

`summarize` 遍历冻结 plan 的全部 21 条，缺结果写 not_run、TF/PE=null；有结果均保留。均值筛选仅要求 TF 与 PE 都非 null，没有阈值、比较原分或取 max，`retry_conditions` 保留全部七行状态，`primary_scores_replaced=false`。因此新批次自身不会只收高分。**主窗口稍后生成的 retry-aware 合并表尚未在本审查中验收，必须再次确认同样纳入所有有效重试，哪怕低分、max_rounds 或空最终答复，并保留仍失败的条件。**

## 3. 失败和费用的中途快照

审查时七份 adaptation 均已生成：

| 条件 | 重试更新状态 |
| --- | --- |
| V2 283-Late | failed：Unknown evidence source or field |
| V2 430-Late | validated |
| V2 90-Late | validated |
| V3 283-Late | validated |
| V5 133-Middle | validated |
| V6 430-Late | failed：Candidate snapshot contains dangling references to removed tools |
| V6 90-Late | failed：Unknown or duplicate candidate |

这些失败分别在新目录 `adaptations/<task>/<stage>/<arm>/adaptation.json` 和 `retry-error.json`；没有被新成功结果覆盖。此时 actor 尚在执行，blocked-cells 也在陆续生成，不能以中途 blocked 文件数验收最终分母。按冻结设计，应最终为 12 个 actor 可执行、9 个因重试更新失败而阻止；不预先保证 12 条都取得完整评分。

一次读取的 receipts 快照为 38 条：21 updater、14 agent、3 judge，未知费用 0。updater 请求归属为 V2 283/430/90 各 8/3/4 次，V3 283 为 1 次，V5 133 为 2 次，V6 430/90 为 2/1 次。它们是既有方法内部请求，不是七条件被外层重复抽样。未等待 actor 完成，也不把此快照冒充最终总账。

`ReceiptGuard` 对无 usage/未知费用记 `usd=null` 并停止新请求；没有将未知直接写成 usd=0。共享汇总同时保存 `unknown_charge_requests` 和 `known_actual_usd`，前者非零时后者只是已知下界；每组 update/deployment 数字也会跳过未知项，**不能脱离未知计数把这些小计当完整实际总成本**。最终 verify 要求所有 receipts 费用已知且模型/路由正确；已有在途请求可能继续回执，最终要全部计入。

## 4. 展示与最终验收意见

1. 原始主结果和失败率不改。补表标“失败后一次重试，事后探索性恢复”；同时给原条件状态、新更新状态、全部三次新 actor（如有）、最终答复状态和有效评分。成功更新但低分也全部纳入，更新仍失败保留 null 与阻止分母。
2. 成本累计原失败尝试与这次全部费用，包括内部修订、失败更新、judge 格式失败；不能只报最后成功那段。新批次 summary 只汇总新批费用，合并账单需主窗口额外做跨批去重和旧账累计。
3. 历史 V2 283 原路由未锁，而这次 DigitalOcean 固定；新 plan 已披露，不能说是严格复现旧供应商。旧 V2 原 actor 1 次、新重试 3 次也不能抹平；其余对照没有获得相同恢复机会，因此不能由 retry-aware 表宣布方法公平胜出。
4. 收尾还需核对 21 个 cell 全部有评分/失败阻止/明确未完成记录，不能静默漏掉中断与未评分执行。verify 对 validated 条件缺 result 会失败，对 unknown 费用也不会通过；不要仅以 summary 的成功子集均值代替完成验收。

主要证据：[重试脚本](/Users/q/Desktop/tool-selective_patch/V6/scripts/retry_failed_updates_once.py)、[冻结计划](/Users/q/Desktop/tool-selective_patch/V6/results/raw/failed-updates-retry-once-20261103/plan.json)、[原五题覆盖表](/Users/q/Desktop/tool-selective_patch/V6/evaluation/supplements/five-task-20261103/five-task-coverage.json)、[原有 actor 与计费包装](/Users/q/Desktop/tool-selective_patch/V6/scripts/eval_v3_formal.py)、[共享汇总代码](/Users/q/Desktop/tool-selective_patch/V6/scripts/eval_v35_three_tasks.py)。本 worker 未运行会写入原始目录的 verify/summarize 命令。

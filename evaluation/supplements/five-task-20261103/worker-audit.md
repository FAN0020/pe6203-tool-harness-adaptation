# PE6203 V3/V5 三任务补测独立只读审查

审查日期：2026-11-03（Asia/Singapore）。仓库：`/Users/q/Desktop/tool-selective_patch/V6`；读取时分支为 `evaluation-integration`，冻结实现提交 `ff326eea6b80b62c210841462312aa64e5a4e68a`。本 worker 没有调用模型/API，没有重跑实验，没有修改仓库文件、评分、方法、原始记录、分支或运行脚本；只在项目镜像的 `outputs/` 写本报告与独立复算 JSON。`sources/` 未改动。未读取私有凭证文件或环境变量值。

## 审查结论

1. **本轮数字与原始证据一致。** 独立从 48 份 EVAL、240 份有效 judge 原始 JSON 内容、507 份 API request/response/outcome 及 receipts 复算，得到与主窗口相同的均分、完成数和支出。187 个冻结源码文件、目录输入、能力证据和已冻结知识的哈希均匹配。
2. **两处更新失败是既有候选协议被模型回复违反。** V3 的 283-Late 把已处理的 `list_tasks` 再列为候选；V5 的 133-Middle 把已处理的 `validate-spec`、`design-assistant`、`speckit-generator` 再列为候选。它们均不在允许候选目录中。没有证据显示驱动器改坏了候选校验；核心更新器与发布归档一致。
3. **不能由这些成功子集均分直接宣布 V5 优于 V3。** 两组缺失的是不同条件；每组仅 8/9 个条件验收通过。同一条件的三次 actor 共享一次更新，不能当成三次独立更新成功或失败。
4. **No Update 高分本身不是异常，也不构成改分/删题理由。** Early 只意味着知识与该阶段一致，不保证模型完成、正确调用、简洁规划或交付。部分高 TF 有真实正确调用支撑；但本轮也有高 TF、空最终答复，以及 judge 理由与原始答复不符的具体案例。原分应保留，交付与产物验证另报。
5. **五任务补齐可以补足覆盖，但不能包装成同期、公平完整排行榜。** 历史/本轮来源、服务商、actor 重复次数、产物协议和 V6 的事后替换均须保留。V6 是研究主方法，V1 是历史基线；不能因为哪个旧版本当前均分最高就改换主方法定位。

## 1. 独立复算与计费

本节证据根目录：`/Users/q/Desktop/tool-selective_patch/V6/results/raw/v35-original-three-20261103/`。下表均为本 worker 自行读取原始文件计算，未运行会覆写 `verification.json` 的仓库验收脚本。

| 项目 | V3 | V5 |
| --- | ---: | ---: |
| 计划 actor 轨迹 | 27 | 27 |
| 得到完整五槽位评分 | 24 | 24 |
| 更新失败而未执行 | 3 | 3 |
| 验收通过的更新条件 | 8/9 | 8/9 |
| 正常结束并输出最终答复 | 21/27 | 20/27 |
| 在已评分子集内正常结束 | 21/24 | 20/24 |
| 已评分子集 TF | 9.683333333333334 | 9.816666666666666 |
| 已评分子集 PE | 8.616666666666667 | 8.791666666666666 |
| 工具 `isError` 返回总次数 | 6 | 12 |

总计 54 计划、48 评分、6 阻止执行；7 条已评分轨迹达到轮数上限、最终答复为空。工具错误有时是有意负面探测，不能直接等同于无效调用或方法错误。

| API 阶段 | 请求数 | 回执 `usage.cost` 合计，USD |
| --- | ---: | ---: |
| updater | 11 | 0.011664360 |
| actor/agent | 255 | 0.497726568 |
| judge | 241 | 0.181170468 |
| 合计 | 507 | **0.690561396** |

全部回执费用已知；请求编号唯一，507 个请求目录均有对应回执。逐份检查 response ID、provider、model、request body 路由、outcome 与账本一致；每条累计费用也与账本顺序累加吻合。计费依据是服务商返回的 `usage.cost`，没有按假定单价覆盖真实 usage；本审查未访问支付账户或外部发票，故这里确认的是原始 API 回执记账一致性。

241 次 judge 请求产生 240 份有效评分：`runs/133-late-v3-r3/judge-attempts/slot-4-attempt-1/outcome.json` 是一次 JSON 格式失败，第二次取得有效分数。失败请求的费用仍保留。这是冻结的两次上限、首个有效评分恢复规则，不是 actor 重跑挑分。

本轮 update 费用包含失败更新，且每个条件只计一次。V3 的 update+actor 为 USD 0.263124660，V5 为 USD 0.246266268；judge 不属于部署任务成本。由于两组执行条件缺失不同，这些总额也不能直接解释成同一完整任务负载上的成本胜负。

所有 48 条轨迹均核对：原任务问题未改；注入知识与冻结知识相同；运行时工具目录与预采集目录相同；结果中的 actor/judge 费用与按 cell 聚合的回执相同。240 份有效原始 judge 内容与保存的解析分数一致，重新按每条五次评分平均后与 result.json 一致。未发现额外 Python 产物验收配置。

机器可读的独立复算结果：[worker-audit-evidence.json](worker-audit-evidence.json)。逐轨迹复算、失败候选、分阶段费用和源码对照哈希均保留其中。

### 成功子集不相同的实际影响

V3 缺 283-Late，V5 缺 133-Middle。只取双方都执行成功的 7 个 task×stage、每条件 3 次，共各 21 条轨迹，描述性结果为：

| 共同有数据的子集 | V3 | V5 |
| --- | ---: | ---: |
| TF | 9.685714286 | 9.819047619 |
| PE | 8.914285714 | 8.857142857 |

PE 的相对顺序因此与各自 24 条均分相反，足以说明条件构成会改变表象。这个 21 条子集同样是在观察失败后筛出的成功条件，不能修复选择偏差，也不应替换预定主结果。应一起列出原计划分母、阻止条件、正常最终答复数和条件均分；不能把缺失官方分擅自填 0，也不能悄悄丢掉。

## 2. 更新失败：原始回复与已发布源码对照

### V3：283-Late

- 原始请求/回复：`results/raw/v35-original-three-20261103/api/request-00009/{request,response,outcome}.json`。
- 方法审计：`adaptations/283/late/v3/v2-audit.json`；失败记录：同目录 `evaluation-error.json`、`adaptation.json`。
- 请求中明确禁止重新分类 program-completed/program-semantic 条目。23 个允许目录 ID 的 coverage 回执完整且无重复。
- 回复的 candidates 却加入 `@pimzino/agentic-tools-mcp::list_tasks`。该 ID 已在 `program_completed_tool_ids`，不在 23 个允许目录 ID 中。其 basis 为 `c7,a3,a4`，不是缺少真实 change ID，而是候选身份越界。
- 触发既有 `screen_candidates` 的身份检查，失败费用 USD 0.002758860。三份 `blocked-cells/283-late-v3-r{1,2,3}.json` 均存在；没有这三份 actor 目录，也没有归属于这三条 actor 的 API 请求。

### V5：133-Middle

- 原始请求/回复：`api/request-00002/{request,response,outcome}.json`。
- 方法审计：`adaptations/133/middle/v5/updater-audit.json`；同目录有失败记录。
- 38 个允许目录 ID 的 coverage 回执完整且无重复。
- 回复重新提出 `mcp-ai-agent-guidelines::validate-spec`、`mcp-ai-agent-guidelines::design-assistant`、`mcp-ai-agent-guidelines::speckit-generator`。三者都已在 `program_completed_tool_ids`，都不在允许目录中。
- 失败费用 USD 0.000748128；三份 `blocked-cells/133-middle-v5-r{1,2,3}.json` 均存在，actor 没有执行。

所以错误消息中的 “Unknown, duplicate or already program-classified” 是一个合并报错；本例具体属于 **already program-classified / outside eligible directory**，没有证据表明是候选自身重复，或凭空发明了未知工具。准确表述应使用具体类别与 ID。

### 是否为驱动器改坏协议

已将当前源码与以下发布归档成员直接逐字节比较，不导入/执行归档代码：

- `/Users/q/Desktop/tool-selective_patch/V6/evaluation/v3/archives/runtime.tar.gz`：`src/pe6203/scope_v3.py`、`scoped_selective_v3.py`、`capability.py`、`hybrid_selective.py` 一致。
- `/Users/q/Desktop/tool-selective_patch/V6/evaluation/v5/archives/runtime.tar.gz`：`src/pe6203/scope_v5.py`、`selective_v5.py`、`rules_v5.py`、`evidence_v5.py`、`hybrid_selective.py` 一致。
- 共用 `selective.py` 仅模块说明文字不同；排除该 docstring 后 AST 相同。
- `src/pe6203/baselines.py` 与归档不是整个文件相同：当前增加其他版本显式路由、修改默认模式，并允许 spend guard/extra body。V3/V5 此次都显式指定 `hybrid_v3`/`hybrid_v5`，相关分派仍指向原核心；不能笼统声称整个运行库逐字相同。
- `integration/baselines.py` 增加 spend guard 与路由参数合并；本轮 `_request_completion` 被既有 ReceiptGuard 的请求包装接管。读取 `scripts/eval_v35_three_tasks.py`、`scripts/eval_v3_formal.py` 及实际 request body，没有发现候选内容/校验器被替换。

这支持“原核心协议被回复违反，原始证据下未见测试驱动器造成该失败”。它不等于证明协议设计最优，也不等于可以事后放宽校验后把同一实验说成原方案成功。潜在过滤/重试改进应作为新方法、新方案研究。

## 3. No Update 高分争议与交付边界

### 为什么 Early 仍不保证满分

Early 的知识起点与目标环境一致，只消除一类知识陈旧风险。模型仍可能选择多余调用、错误参数、无法在预算内结束、给出缺漏回答，judge 也有判断波动。此次 `send_model_seed=false`；101/102/103 是记录标签，没有作为模型 seed 发出。温度 0 也没有建立“每次请求内容必定相同”的保证。

已直接读取旧归档中的完整 raw_trace、result 与 EVAL：

- `/Users/q/Desktop/tool-selective_patch/V6/evaluation/v5/recorded-72/raw-measurements.tar.gz`，成员前缀 `v5-formal-20261103/`：`runs/133-early-no_update-r1/` 为 TF 9.4、PE 6.8。首份 judge 认可验证表达式与 OWASP 建议两个目标，但指出 16 次调用中约 6 次重复。知识不陈旧与规划效率高是不同命题。
- `/Users/q/Desktop/tool-selective_patch/V6/evaluation/v3/recorded-108/raw-measurements.tar.gz`，成员前缀 `v3-formal-20261103/`：`runs/133-early-no_update-r3/` 最终答复为空，原 TF 8、PE 4.2。首份 judge 认为工具侧两个目标有所实现，同时指出最终交付不足。该例应保留，不能用 Early 理应满分推翻观察结果。

### 有些 No Update 高分有正确调用支撑

上述两个旧归档的 `runs/235-early-no_update-r1/` 均为 TF 10、PE 10。完整 trace 中分别生成地图、面积图、分组柱图，三个调用与任务数据对应；返回的是 vis-chart spec/config，judge 以三项子目标正确完成、零冗余为由给高分。这是可以解释的高分，不能仅因 No Update 得分高而认为任务无效。

任务 235 的相关变化保留旧可用行为，旧 V5 本轮目录知识相同的条件仍能出现执行/评分波动；变动并不必然破坏旧工具调用。它适合观察“是否避免不必要更新”，对破坏性变更后的恢复能力区分较弱。旧 V3 的 `product-review.json` 另已记录 27/27 图表数据人工核对通过、网页渲染未验证；这里未新增浏览器渲染验证。

相反，两旧归档的 `runs/90-late-no_update-r1/` 均只有 TF 7：卡牌信息与图片有观察支撑，但每日题目标没有取得。这说明 No Update 不是无条件被判满分，任务变化/失败与实际缺失内容需要按 trace 解释。

### 高 TF 不等于完成最终交付；存在具体 judge 局限

本轮以下七条 `raw_trace.json` 的 `answer` 为空，execution 为 `max_rounds`，但仍得到评分：

| cell | TF | PE |
| --- | ---: | ---: |
| 283-middle-v3-r1 | 9.8 | 8.8 |
| 283-early-v3-r1 | 9.8 | 9.2 |
| 283-middle-v3-r3 | 9.6 | 7.0 |
| 283-early-v5-r1 | 10.0 | 8.2 |
| 283-late-v5-r1 | 9.4 | 7.6 |
| 283-middle-v5-r3 | 9.6 | 9.0 |
| 283-late-v5-r3 | 10.0 | 9.0 |

其中 `runs/283-middle-v3-r1/EVAL/283.json` 首份 judge 的 grounding 理由说 “Final answer cites milestones, 21 tasks…”，但同一个 EVAL 顶层 answer 和 raw_trace answer 都是空字符串。原始 judge prompt 的 `FINAL ANSWER` 区也是空的，之前仍保留工具轨迹。这是**具体的理由与输入不符**，不能以“分高”本身为依据否定，但可以以这项直接矛盾指出模型评审没有可靠区分轨迹与最终答复。

该轨迹最后完整复杂度报告还列出 5 个复杂条目，包括两个复杂度 7 的实现任务；首份 judge 却称 “verified ≤6 leaves”。因此对“所有任务均已足够细化”也不能仅沿用该句 judge 理由。无需改动原始分数即可指出其证据不足。原评分 prompt 的轨迹片段有截断；judge 能看到的上下文与完整 raw_trace 并不完全等同，这也是解释边界。

建议展示三层：官方 TF/PE；正常最终答复率（计划分母与已执行分母都写）；按任务交付的事实核对（工具侧项目/任务、图表配置、图片 bytes、Python 代码是否实际测试）。本报告不改分、不重评、不删除任务，也不把任何离线事实检查说成浏览器/部署/安全验证。

## 4. 五任务补齐方案可比性审查

冻结范围为 **133/235/283/430/90**，排除 V4。已读取另批方案 `/Users/q/Desktop/tool-selective_patch/V6/results/raw/five-task-supplement-20261103/plan.json` 及驱动器；本 worker 不接管执行。收尾时主窗口通知该批已结束且通过核验；其新增批次总数见下方收尾补记，未作为本 worker 已逐条复算的结论。

| 版本/对照 | 原三任务来源 | 430/90 来源 | 必须披露 |
| --- | --- | --- | --- |
| V1 | 既有历史基线；本次未独立追溯其原三题全部原始记录 | 另一批新补测，3 actor/条件 | 与 V6 主方法定位分开；原三题来源与缺失仍需逐项标明 |
| V2 | `evaluation/v2/recorded-results`，原计划 27、25 评分、19 正常；1 actor/条件 | 另一批新补测，3 actor/条件 | 旧 endpoint/provider variation、transport retry/未知费用；不能补成假想的 3 次历史重复 |
| V3 | 本轮 24/27 评分；另有旧四题批次中 133/235 可作历史旁证 | `evaluation/v3/recorded-108` 中 430/90，各 3 actor/条件 | 283-Late 三条阻止；新旧批次混合，即使均为 DigitalOcean 也非同批 |
| V5 | 本轮 24/27 评分；旧四题中 133/235 可作历史旁证 | `evaluation/v5/recorded-72` 中 430/90，各 3 actor/条件 | 133-Middle 三条阻止；与旧 V3/NoUpdate 不是同批配对 |
| V6 | `evaluation/v6/recorded-results/original-r4` 为原始三题，每条件 1 actor；带 Python 产物协议 | 另一批新补测，3 actor/条件，目录证据 | 原三题 relace/fp4，新增两题 DigitalOcean；协议与重复次数不同；当前展示含事后替换 |
| No Update / Full Rewrite | 各历史来源有自己的控制组，不能静默只挑一组拼接 | 另一批同批新控制，各 3 actor/条件 | 用来源标签区分；历史控制不能冒充本轮原三题同期控制 |

本轮 V3/V5 与旧 V3/V5 四题批次均固定 `deepseek/deepseek-v4.1-flash-1017`、DigitalOcean、温度 0、12 轮、4096 actor/judge 输出、5 次评分；这种一致减少部分差异，但无法消除时间、调用负载、缓存、任务90日期相关内容与批次差异。旧 V6 `frozen-plan.json` 明确固定 `relace/fp4`，且比较范围是带 Python 协议的 full-system；不能称所有历史五题结果都是相同 actor 机制下纯知识更新对比。

### V6 数学 Middle 的事后好重跑

`evaluation/v6/recorded-results/summary.json` 的 selection 明确记录：原 133-Middle TF 3.4、PE 1.6、`artifact_unaccepted`，后一次 TF 10、PE 10、completed；`policy=owner_requested_replacement_after_observing_repeat`，`balanced_single_attempt_comparison=false`。原 `original-r4/summary.json` 总 TF 9.155555556、PE 8.333333333；当前替换展示为 TF 9.888888889、PE 9.266666667。

原始数据与重复都保留是正确的；本报告不撤销用户要求的展示选择。但主实验应识别原始 r4，替换版只能标作事后选定展示/探索性补充，不能称预注册主结果或与未获等额重跑的基线公平比较。不能只收好重跑的费用而漏掉原失败执行支出；当前 summary 已另存 superseded 的 USD 0.005633930，应保留该口径。

### 五题汇总可以支持什么

可以形成带 `source_batch / task / stage / version / actor_repeats / provider / protocol / selection / status` 的五任务覆盖与证据表，逐任务保留 TF/PE、最终答复、验收失败和分阶段成本，并在同一批次、共同条件下做有限描述。

不能支持“V1–V6 在同期五任务上公平完整排名”，不能将 5 judge 当 5 actor，不能按现有所有行直接 pooled mean 使 3 次重复的新增任务权重高于 1 次重复的旧任务，也不能把可选参数增加一概算作对 No Update 的必然失败。即使使用 task×stage 等权平均，来源/协议混杂也不会自动消失。

## 5. 可直接用于主窗口的结论与剩余问题

**可支持：** 本轮冻结证据、评分保存和 API 回执记账一致；两种方法各有一处具体的候选协议失败；已评分成功子集的原均分可以如实报告；No Update 的部分高分有正确工具执行支撑；有必要并列报告最终答复与产物事实。五任务覆盖可通过补测与有来源标签的历史证据补齐。

**不能支持：** 某方法已整体胜出；高 TF 已证明安全代码/网页渲染/完整项目交付；Early 理应满分；观察高分后删任务或改分；拼合结果可当同期排行榜；V6 事后选好的数学 Middle 是预注册且无偏的主实验。

**主窗口收尾事项：** 430/90 的逐条核验已由主窗口报告完成；定位 V1 原三题 canonical 批次，明确原三题每版本缺失/重复次数，输出来源分层的五题表，并对上述 judge 理由不符保留审查标记。若以后改变候选过滤、judge 或重复方案，应作为新的明确方案，不能追写本轮成功。


## 收尾补记：主窗口完成通知与 task283 直接证据

主窗口收尾通知（本 worker 未独立复算新增批次）：430/90 批次 90 计划 = 78 评分 + 12 更新阻止；V2、V6 各自的 430-Late 与 90-Late 更新失败，每个条件阻止三个 actor。两批合计 126 条实际执行、630 份有效评分、1226 次 API 请求、USD 1.757586108。这与本报告独立复算的原三任务批次是不同证据层级；不得把新增 12 条未执行隐去。

最具体的 judge 理由不符案例：`283-middle-v3-r1`。

- [完整 raw_trace.json](/Users/q/Desktop/tool-selective_patch/V6/results/raw/v35-original-three-20261103/runs/283-middle-v3-r1/raw_trace.json)：`answer` 为 `""`。
- [result.json](/Users/q/Desktop/tool-selective_patch/V6/results/raw/v35-original-three-20261103/runs/283-middle-v3-r1/result.json)：`execution_status="max_rounds"`、TF 9.8、PE 8.8。
- [EVAL/283.json](/Users/q/Desktop/tool-selective_patch/V6/results/raw/v35-original-three-20261103/runs/283-middle-v3-r1/EVAL/283.json)：顶层 `answer` 也是空；`eval_result.runs[0].result.grounding_reasoning` 原话：**“Final answer cites milestones, 21 tasks, dependency wiring, complexity check, recommendations; all supported by tool outputs.”** 同份 TF 理由还称 **“verified ≤6 leaves”**。
- [第一槽位原始回复](/Users/q/Desktop/tool-selective_patch/V6/results/raw/v35-original-three-20261103/runs/283-middle-v3-r1/judge-attempts/slot-1-attempt-1/response.json)：保留上述 judge 原始内容，未改写评分。
- [原始 judge prompt](/Users/q/Desktop/tool-selective_patch/V6/results/raw/v35-original-three-20261103/runs/283-middle-v3-r1/judge-original-prompt-1.txt)：`FINAL ANSWER` 区为空，之前是工具轨迹；完整 trace 最后复杂度报告仍列出两个复杂度 7 的实现任务。该例说明高评分及其理由不足以代替最终交付与任务细化事实。

其余六个空最终答复 cell 及其分数已完整列于第 3 节；各自的 `runs/<cell>/raw_trace.json`、`result.json`、`EVAL/283.json` 均在同一证据根目录。无需改分或重跑即可保留这一局限。

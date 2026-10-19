# 正式实验协议

版本为 `plan-v1`，目前处于 `pending_validation`。本文件定义主实验；结构化参数见 [protocol.v1.json](../../experiments/protocol.v1.json)。执行前完成 [freeze record](../../experiments/templates/freeze-record.json)，所有未定模型和任务字段必须有事实依据。

## 实验单位与固定条件

单次运行的身份为 `(experiment_id, task_id, stage, strategy, repeat_id, attempt_id)`。固定 benchmark commit、服务 archive digest、fixture digest、模型及 provider、推理参数、prompt、judge、harness revision、最大轮数和超时。

任务使用官方指定 server set，不做跨服务器动态检索。每次任务从相同 fixture 创建独立 workspace；重置项目、图谱、文件及其他持久化状态。随机化策略执行顺序并记录 schedule seed，避免某一策略总在服务拥堵时运行。

开发任务用于确定模型兼容性、上下文预算和工具 catalog 大小。正式任务冻结后不再用其分数调 prompt。若修复缺陷或改变方法，建立新实验 revision，并对所有策略重跑受影响的比较单元；保留旧结果。

## 工具知识与阶段

记 Early 原始工具知识为 `K0`，当前阶段元数据为 `Mv`。K0 包含每个固定 server group 的完整工具 catalog；同一 server group 的任务共享同一知识产物。四工具的 task-139 smoke knowledge 只适用于基础验收，不能冒充正式完整知识范围。

K0 从 Early metadata 确定性转换；构造与采集开销单列，不计为某个策略的更新成本。字段和实际 agent 输入规则见 [接口约定](interfaces.md)。

| 环境 | No Update | Full Rewrite | Selective Patch |
| --- | --- | --- | --- |
| Early | K0 | K0，不调用 updater | K0，不调用 updater |
| Middle | K0 | rewrite(K0, Mmiddle) | patch(K0, Mmiddle) |
| Late | K0 | rewrite(K0, Mlate) | patch(K0, Mlate) |

主实验的 Middle、Late 都从 K0 独立更新，避免把 Middle 更新误差带入 Late。Early 三个标签执行相同知识条件，各自保存运行；它们不是三种不同更新方法。预算中按全部执行计数，不把同一条缓存轨迹当成独立重复。Early → Middle → Late 的顺序适应只作为另一个明确命名的可选实验。

每个 `server_group × target_stage × strategy × repeat_id` 生成一次更新产物，再由相关任务复用。记录 artifact ID；总更新成本按唯一产物计费，不能按复用任务重复相加。每次重复重新生成更新产物；No Update 固定复用 K0。报告清楚重复包含 updater 和 agent 的随机性。

Runner 只执行给定知识，不自动修复过期参数或映射已删除工具。当前环境 metadata 仅用于审计和 judge。正常工具错误会反馈给 agent，所有策略采用同一规则。No Update 的失效调用是实验现象，不能当成基础设施故障跳过。

## 配置与预算

主实验一个 agent 模型、一个 judge 配置、一个 updater 配置。Agent 和 updater 可用同一模型，但这是独立字段，不能从 key 名猜测。记录实际返回的 model ID；provider 支持时固定模型快照。API key 只来自明确指定的环境变量，不写入 Git。

待 pilot 验证的起始值：temperature 0、agent 每次最多 2048 completion tokens、judge 4096、最多 12 轮、请求 90 秒、工具调用 30 秒、整次运行 600 秒。Updater 起始 completion 上限为 4096，按 server 分块；超长 server 的固定分块方法在开发集确定。超预算或截断是失败状态，不能静默截掉工具。

repeat seeds 为 `[0,1,2]`，压缩版为 `[0]`。默认不向模型发送 seed；记录 repeat ID，并只在所有相关 provider 支持、配置统一时启用 model seed。temperature 0 不能保证确定性。Judge 对每条轨迹固定尝试 5 次，按记录的 seed 打乱 rubric 顺序；这不是 agent 重跑 5 次。

8 个任务 × 3 阶段 × 3 策略 × 3 次重复 = 216 次主实验 agent 执行；5 次 judge 对应最多 1080 次评分尝试。压缩版为 72 / 360。上述数量不包含开发、更新器、基础设施重试或消融。先测 pilot 的 tokens、耗时和价格，再填写预算，不编造美元金额。

## 任务标签与输入

A/D 使用 [task review](../../experiments/templates/task-review.json) 记录官方 ID、question hash、固定服务器、fixture 来源、每阶段 catalog hash、task family、split、期望产物、禁止行为和验证证据。

按 `early_to_middle` 与 `early_to_late` 分别标记 `changed / unaffected / uncertain`，并记录 TOOL/PARAM/DESC 多标签及受影响依赖。`uncertain` 可留在全任务汇总中，但不进入 recovery 或 retention 子组。对照能力未受影响需有检查依据，不能用“分数没变”作为定义。

Fixture 包含文件内容、数据库/图谱初始状态、必要的时间或外部服务条件。时间敏感输入无法控制时披露可比性限制。Task 内容和 benchmark 标签保持不变；期望属性只作为审计证据，不替代官方 judge rubric。

## 评分与聚合

使用已锁定的官方 judge rubric 和已记录的格式化逻辑。Paper 的 judge 与发布代码默认值不同，实际服务必须在冻结记录中明确；不宣称复现论文 leaderboard。

- TF 与 PE 取有效 judge 分数的未取整 mean。Grounding 也保留。
- 正式完整结果要求 5 次评分都有效；部分结果标为 `judge_incomplete`，不混入完整主表。
- 任务已真实执行但表现很差时，照常评分。基础设施失败、缺失或无效评分不填 0。
- 按任务先对重复取平均，再对任务取平均。报告每个任务、每个阶段、策略的结果及重复波动；8 个任务不变成 216 个独立任务。
- 同一比较使用所有策略均有完整结果的 matched set，列出计划数量、有效数量和排除 ID/原因；额外列出各策略失败率。缺失严重或与策略相关时，不能仅凭 matched set 宣称获胜。

令 `TF(t,v,s,r)` 为某任务、阶段、策略、重复的 TF：

| 输出 | 定义 | 解释 |
| --- | --- | --- |
| Recovery delta | changed 任务上 `mean(TF(s,v)-TF(no_update,v))` | 相同环境下更新带来的差异，单位为 TF 分数点 |
| Retention update delta | unaffected 对照上同样的配对差值 | 负值表明更新相对 No Update 有损失 |
| Retention vs Early | 对照上 `mean(TF(s,v)-TF(no_update,early))` | 跨环境保持情况，不能单独归因于更新 |
| ECS primary | 对同一 task、strategy、repeat 的三阶段 TF，先求 `mean - population_std`，再平均任务与重复 | 对齐发布代码口径 |
| ECS sensitivity | 将上式标准差替换为 sample_std | 单独展示论文附录口径 |

两个 ECS 口径的差异已列在 [environment audit](../environment.md)。主表使用 `upstream_population`，敏感性表使用 `paper_sample`；若课程另有说明，在正式冻结前统一变更并记录来源。ECS 需要完整三阶段配对，缺一阶段就缺该 triplet。

小样本结果定位为所选任务子集的证据。报告均值、重复差异和任务级变化，不仅汇报最佳轨迹，也不凭三次重复作总体显著性保证。

## 失败与重试

区分 `infrastructure / agent_execution / adaptation_validation / judge_format / under_update / over_update`。一个运行可有多个标签；under/over 是基于 patch 和轨迹的归因，需要证据，不由状态码自动决定。

| 案例类型 | 归因所需证据 |
| --- | --- |
| under-update | 应更新的接口/依赖未更新，实际轨迹因此失败；指出缺漏字段及调用 |
| over-update | 不必要或错误的知识改写导致原本可用能力回退；结合未改基线或独立诊断核对 |

Full Rewrite 的失败不自动等于 over-update；No Update 的低分也不自动证明 under-update。诊断重跑与主结果分别保存。

更新校验失败时不启动 agent、不换用其他策略；记录 `adaptation_validation`、已有成本和 `null` 分数。相关任务单元必须出现在计划执行数与失败率中，不能从总数中消失。

未来 batch runner 对明确的连接失败、HTTP 429/5xx 等基础设施问题最多追加 1 次 attempt，固定退避规则为 10 秒并遵守更长的 Retry-After。重跑使用新 workspace，保留全部成本和日志，采用第一份按规则产生的完整结果。语义错误、低分、工具参数错误和 max rounds 不触发这种重试。当前已实现保守 batch/resume，但仍未实现上述 HTTP 分类退避；正式冻结前补齐或明确修订协议，不能宣称当前实现已满足此项。

Judge 无效 JSON 不追加到“凑够高分/有效分”为止，固定五次尝试后报告完整性。当前 batch resume 保留身份与 result hashes 一致的完整或 incomplete/blocked 结果，不自动重试已落盘失败；身份或 hash 不符则拒绝恢复。中断且无 result 时最多另建一次 attempt；该机制不同于上述计划的分类重试。手工诊断重跑使用新 ID，不能替换主实验中较差的有效结果。

## 交接接口与产物

现有接口：`run(task_id, version, strategy, seed, config) -> (raw_trace, benchmark_result)`。已扩展通用 task/profile 与 batch sidecar ledger；当前能力见[全量交接](../full-benchmark.md)。

待实现接口：`adapt(old_knowledge, new_metadata, strategy, context) -> (new_knowledge, diff_log, update_cost)`。`context` 只含 server group、stage、重复 ID、配置与版本信息，不包含任务答案或评分。示例形状见 [adaptation record](../../experiments/templates/adaptation-record.json)。

| 产物 | 使用者 | 要求 |
| --- | --- | --- |
| metadata / knowledge | B/C/A | canonical JSON、来源、阶段和 hash；区分环境信息与模型实际输入 |
| patch / validation | C/D | 增删改条目、重命名证据、未改条目检查、失败原因 |
| raw trace / ANSWER / EVAL | A/D | 原始响应及实际评分输入，保留全部失败 |
| batch ledger | A/D | experiment、task、stage、strategy、repeat、attempt、hashes、状态、路径 |
| summary / failure cases | D | 可追溯回单次运行与知识产物 |

每个 ledger 记录至少含 `run_id, experiment_id, task_id, stage, strategy, repeat_id, seed, attempt_id, runner_commit, protocol_file_sha256, task_manifest_file_sha256, fixture_file_sha256, knowledge_file_sha256, adaptation_artifact_id, status, output_dir`。`*_file_sha256` 使用文件 bytes 哈希，与 runner 现有对象摘要区分。更新 artifact 和运行有不同生命周期，不能只依赖文件夹名配对。

## 正式冻结条件

A/D 完成任务和环境审查，B/C 固定 updater 实现与 prompt，D 核对模型、价格、judge 与指标。填写 freeze record 的版本、摘要、审查人和证据链接后，将其 `frozen` 设为 true。审查是正常的团队质量检查，不增加超出用户授权的操作审批流程。

未确定的任务、模型、费用或协议参数用 `null` 表示。不得仅为通过检查填写占位的真实形状值。正式冻结后的变更必须生成新的 experiment ID 和记录。

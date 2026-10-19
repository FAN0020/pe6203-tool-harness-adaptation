# 项目范围与方法设定

项目展示名称为 **MCP Agent Reliability under Tool Evolution**。课程名称仍为 PE6203 Project 4。研究对象是持续性工具变化后存储在 harness 中的知识如何更新，基础模型不做微调。

## 研究问题与证据

| 问题 | 对比与证据 | 允许的结论 |
| --- | --- | --- |
| RQ1 局部更新能否恢复表现 | changed tasks 上 Selective Patch 与 No Update 的 TF、PE 差值及轨迹 | 对所选任务子集的改善、无改善或退化 |
| RQ2 是否损伤无关能力 | retention controls 上三种策略的配对差值和状态检查 | 保留情况及观察到的回退 |
| RQ3 是否减少更新开销 | Selective Patch 与 Full Rewrite 的更新 tokens、耗时、已核定 API 费用 | 成本与质量之间的实际取舍 |

Selective Patch 更好是待检验假设。负结果仍应报告；不能把“代码只改少量字段”直接等同于“性能没有损失”。

## 课程要求与交付对应

来源：[S1 课程原文](sources.md)。

| 要求 | 本项目的验收对象 |
| --- | --- |
| MCPEvol-Bench 固定子集；相同任务 | manifest、task reviews、冻结记录 |
| Early / Middle / Late；TOOL / PARAM / DESC | 三阶段环境证据、任务级变化覆盖表 |
| No Update / Full Rewrite / 自研 Selective Patch | 三种方法实现、knowledge 与更新记录 |
| 固定模型、推理设置、judge；不微调、不改标签 | 配置、prompt、rubric、commit 与 hashes |
| TF / PE / ECS、recovery / retention、更新成本 | 配对结果表、usage 与费用来源 |
| 至少一个 under-update 和 over-update | 真实 patch + 失败轨迹 + 归因 |
| 代码、配置、命令、日志、报告、10 分钟展示 + 5 分钟问答 | README、evidence、报告、演示 |
| 3 次优先；有限资源可 1 次并披露 | 冻结 repeat IDs、运行记录、局限说明 |

## 业务范围与任务数量

优先筛选知识与项目管理、固定输入的数据与文件处理任务。它们应能提供可检查的持久化状态或输出文件。文档与图表作为补充方向，仅在覆盖不足且依赖可稳定运行时纳入。在线搜索、实时天气、交通等任务需要额外控制时间与服务状态，不列为首轮优先项。

目标为 4 个 development tasks 和 8 个 evaluation tasks。正式任务的覆盖目标为 TOOL 2 个、PARAM 2 个、DESC 2 个、retention controls 2 个。这是覆盖配额目标；一个任务可带多个变化标签，不能强称为单因素实验。数量或配额需要调整时，在冻结前写明原因，并保留全部课程要求。

8 个正式任务必须是 8 个不同 ID。变化配额按“至少一个目标阶段中相关且受影响的不同任务数”计；retention 目标为两个 transition 都未受影响的 2 个任务。正式分析仍逐 transition 分组；无法确认的任务标记 uncertain，不强行凑配额。

任务 139 已用于开发，固定归入 development set。候选 24、28、393 等只用于筛查，不能自动成为正式集合。近似任务改写应放在同一 split；按任务族检查泄漏。候选集还需要扩充，当前清单不是完整的 12 个任务。

## 纳入与排除

纳入时确认：官方任务 ID 与文本未变；官方固定 server set 可用；三阶段可运行；输入和初始状态有来源及校验摘要；任务目标有工具支持；输出可审查。这里的可完成性不要求某个模型先取得高分。

先根据 metadata、工具实现和任务依赖标记变化相关性，再看正式分数。仅新增可选参数不必然损害任务；相同工具名称不必然意味着能力未变。对于新增干扰工具等间接影响，应记录假设与证据。

保留被排除的任务与理由。缺少原始输入时先寻找发布资料；自行提供输入必须标明替代 fixture 及影响，不能冒充原始官方配置。对主结果是否纳入作出冻结前的统一决定，不根据结果挑选。

## 方法设计

本项目采用 **Diff-guided Selective Patch** 作为待实现方法。正式工具知识覆盖每个任务固定 server set 的完整 catalog；full rewrite 的“完整”以这份知识集合为边界。

1. 对旧、新 metadata 做 deterministic diff，检查工具增删、schema、描述及路由关联。
2. 标记受影响记录及明确的依赖记录；重命名映射要记录依据和不确定性。
3. 用固定的 updater 模型和 prompt 生成受影响记录的更新；结构化字段优先从真实 metadata 读取，说明和使用规则按证据更新。
4. 验证输出 JSON、schema、工具名称与 routing。未被选中的记录需通过 canonical JSON 相等检查。
5. 输出更新后的知识、patch、validation 结果、失败原因及成本；验证失败不静默退回 Full Rewrite。

| 实现细节 | 首版规则 |
| --- | --- |
| K0 构造 | 从 Early 完整 metadata 确定性转换；已有规则照录，无依据则 `[]`；不使用任务答案 |
| 比较单位 | `server_id::tool_name`；解析后比较 JSON，忽略对象键序，保留数组顺序与描述文本差异 |
| 变化检测 | 工具新增/删除、parameters、description、usage_rules、output_schema、routing；来源时间戳不单独触发更新 |
| 重命名 | 有公开明确证据才建映射；否则记录为 delete + add，不猜测隐藏映射 |
| 依赖扩展 | 仅扩展 metadata 中明确引用的 schema/工具依赖一跳；保存引用证据；同名参数不自动等于依赖 |
| 更新范围 | 新增/修改/依赖记录进入 updater；已删除记录移除；其余保留 |
| 结构字段 | 目标名称、schema、routing 以真实 metadata 为依据；LLM 不虚构接口 |
| 语义字段 | updater 根据 metadata 更新说明与规则，保留支持证据；不读测评问题 |
| 校验 | schema 合法、路由存在、选中范围正确、未选中记录 canonical-equal；失败显式返回 |
| 可选消融 | 去掉一跳依赖扩展，其他条件不变；单独 experiment ID |

以上 diff 类别是方法内部字段分类；D 的官方 TOOL/PARAM/DESC 标签需单独审查，不能自动等同。

Full Rewrite 使用相同的 updater 服务、模型和解码设置，重新生成范围内全部工具知识；Selective Patch 只重写选中的部分。二者使用同一预先定义的分块规则和单次响应限制，调用次数与总成本如实记录。No Update 直接复用 K0，更新成本为 0；公共 metadata 获取成本另列。

所有方法获得相同的合法信息边界：旧知识和目标阶段公开 metadata。更新器不读取正式任务问题、参考答案、参考轨迹、mutation ground truth 或评分结果。任务依赖标签仅用于 D 的评估分层，不作为 C 的答案提示。

## 优先级

| 级别 | 内容 |
| --- | --- |
| P0 必做 | 真实端到端运行、三阶段、三策略、覆盖审查、开发/评测隔离、完整日志、主指标、成本、失败案例、报告、干净检出复现 |
| P1 本项目目标 | 自动批处理与断点续跑、三次重复、完整个人贡献证据 |
| P2 有余力再做 | 一个消融、额外业务领域、第二个模型、可视化浏览器 |

首轮交付不扩展到完整 201 任务、不建立通用多 agent 产品或训练平台。原生 stdio 与容器部署分别声明，实际未验证的部署形式不写入简历。

## 完成标准

通过验收需要完整结果和来源，而不仅是计划文件或测试通过。A 能复现真实链路；B/C 有可检查的方法产物；D 能从同一批原始证据重建表格，并指出失败与缺失。组员能解释至少一个真实 under-update 和 over-update；若尚未观察到，记录该要求未满足，受控诊断单独标注，不能伪造自然失败。

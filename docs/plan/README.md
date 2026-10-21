# 项目执行设定 Project execution plan

**目标：两周完成可复现的课程实验，第三周增强证据。** 比较工具持续变化后，局部更新能否恢复 agent 表现、保留无关能力并节省更新成本。

| 决策 | 采用的设定 | 为什么 |
| --- | --- | --- |
| 业务方向 | 知识与项目管理；固定输入的数据与文件处理 | 输入可固定，状态或输出可检查 |
| 任务规模 | 目标 4 development + 8 evaluation；139 只作开发 | 控制工作量，隔离调试与正式测评 |
| 正式覆盖 | TOOL / PARAM / DESC 各目标 2 个；retention 目标 2 个 | 覆盖变化与无关能力；允许多标签 |
| 方法 | No Update / Full Rewrite / Diff-guided Selective Patch | 基线、全量更新、自己的局部更新 |
| 阶段 | Early / Middle / Late；后两者分别从 Early 更新 | 分离目标阶段难度与累积更新误差 |
| 模型 | 固定 agent、judge；两更新方法共用 updater 配置 | 减少比较中的混杂因素 |
| 执行量 | 3 repeats：216 agent / 最多 1080 judge；1 repeat：72 / 360 | 先完成一轮；算力不足时披露单轮限制 |
| 项目边界 | 单模型、固定任务子集、原生 stdio MCP | 将时间集中在适应方法与证据 |

业务方向、任务数和方法设计是**团队选择**；三阶段、三类变化及基线来自课程要求。数量不是 benchmark 规定或统计充分性保证。执行量不含开发、updater、重试和消融。

## 先读什么

| 读者的问题 | 文件 |
| --- | --- |
| 研究范围、方法和必做内容是什么 | [项目设定](project-spec.md) |
| 怎样保证公平比较、计算指标、处理失败 | [实验协议](evaluation-protocol.md) |
| 谁负责、依赖谁、两周怎样完成 | [工作分配与排期](workplan.md) |
| 输入输出具体交什么、现有接口差在哪里 | [交接接口](interfaces.md) |
| 依据是什么，哪些是我们自己的决定 | [来源与决策记录](sources.md) |
| agent 应读取哪些结构化字段 | [实验配置说明](../../experiments/README.md) |
| 报告和简历怎样引用证据 | [报告模板说明](../../reports/templates/README.md) |

## 状态含义

| 状态 | 含义 | 下一步 |
| --- | --- | --- |
| `adopted` | 本项目采用的设计选择 | 按计划实现和验证 |
| `pending_validation` | 目标已经提出，尚无充分运行证据 | 补任务或环境验证 |
| `unresolved` | 缺少服务地址、模型或其他必要信息 | 填写事实，不能猜测 |
| `frozen` | 数据、配置和方法已有可追溯版本，正式运行可以开始 | 变更时建立新实验版本 |
| `verified` | 有对应测试或运行证据 | 在声明旁链接证据 |

这些是计划状态，不是 runner 的 `status`。后者的 `evaluated/blocked/timeout/judge_incomplete` 见 [Group A handoff](../group-a-handoff.md)。

## 当前起点

截至 2026-10-19，已有 201-task 环境审计、三个阶段的完整 Node 发布包、8 个 reviewed profiles、完整 catalogs、通用 runner 和 batch/resume。真实 LLM agent → MCP → judge 验收、其余服务/fixture 审查、B/C 更新算法和正式评测仍未完成；详见[全量交接](../full-benchmark.md)与 [backlog](../../experiments/backlog.json)。

计划可以分享；正式实验尚未冻结。[protocol.v1.json](../../experiments/protocol.v1.json) 的 `readiness.frozen=false` 与尚未填写的模型字段表达这个区别。现有 `configs/smoke.json` 是 smoke runner 配置，不能把计划 JSON 直接传给 CLI。

## 开始工作

1. A 配置实际模型服务，完成一个真实任务的 agent、MCP、judge 和日志验收。
2. A/D 按任务审查模板筛选候选并记录全部纳入或排除理由；B/C 使用 metadata 开发方法。
3. A/B/C/D 合并接口，D 填写冻结记录，再运行同一份正式集合。
4. 先完成所有组合的一轮；时间允许再补到三轮。报告、成本和失败案例随运行积累。

```text
docs/plan/             人读：设定、协议、接口、排期、来源
experiments/           agent 读：protocol、候选 manifest、backlog
experiments/templates/ 冻结、任务审查、更新产物、批次记录模板
reports/templates/     结果表、失败案例、个人贡献与展示模板
results/raw/           本地原始运行；已被 Git 忽略
results/evidence/      已审查的可共享证据
```

下一项可开始的工作从 backlog 的依赖图判断。标为 `planned` 的条目表示本次设定没有验收证据，不推断其他成员是否已在自己的工作区开展了工作。

## 共同术语

| 术语 | 本项目含义 |
| --- | --- |
| Tool environment | 真正执行工具的版本化服务 |
| Metadata | 服务公布的工具名称、说明和 schema |
| Harness knowledge | 实际提供给 agent 的工具知识和路由 |
| Adaptation | 在运行任务前更新 harness knowledge |
| Development set | 允许调试方法的任务集合 |
| Evaluation set | 冻结后用于正式比较的任务集合 |
| Recovery | 在预先标记的受影响任务上，相对 No Update 的表现恢复 |
| Retention | 更新后无关能力的保持情况 |
| Trace | 实际模型响应、调用参数、工具返回和评分的执行证据 |
| Fixture | 可校验、可重置的固定输入和初始状态 |

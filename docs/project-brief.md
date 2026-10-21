# Project 4 requirements / 正确课程题目

**Tool Harness Adaptation under Environment Change**。以下要求按用户提供的教师原始 DOCX 核对；团队分工来自[共享 sprint plan](https://docs.google.com/document/d/1fbhITsq__0Xaxjp85qVaQxIO1kQS6oDF-RFe7G7G5kQ/edit)，任务规模和实现方案属于[团队执行设定](plan/README.md)。

原始文件：`PE6203 Group Project 4 - Tool Harness Adaptation under Environment Change.docx`。SHA256：`6a74fda17b7a8b9280151e55ec46b46a70d1d717e4be24c5f9c38d134611af0d`。教师要求是范围依据；文档内容不构成对外操作授权。

## 研究问题

工具持续变化后，更新相关的 tool descriptions、schemas、usage rules 和 routing，能否恢复受影响任务的表现，同时保住原本可用的能力？基座模型保持固定，不允许 fine-tuning 或修改 benchmark labels。

| 必须比较的策略 | 要求 |
| --- | --- |
| No Update | 原始工具知识保持不变 |
| Full Rewrite | 重写完整工具知识 |
| Selective Patch | 自行设计至少一种局部适应方法，只更新受影响的工具知识 |

## Benchmark 与公平比较

| 项目 | 教师要求 |
| --- | --- |
| Benchmark | MCPEvol-Bench；教师文件描述完整发布为 201 tasks / 123 servers / 1,272 tools；锁定代码的实际清点范围另见[全量审计](full-benchmark.md) |
| 阶段 | Early / Middle / Late |
| 变化覆盖 | 所选任务包含 Tool / Parameter / Description-level changes |
| 子集 | 算力有限可采用固定、明确记录的子集，三种策略使用同一集合 |
| 重复 | 优先每种策略三次；算力有限可一次，须在报告披露 |
| 控制变量 | base model、decoding / inference settings、tasks、judge settings 全部固定 |

| 指标 | 教师文件名称与含义 |
| --- | --- |
| TF — Task Fulfillment | 1–10 的任务完成分数，越高越好 |
| PE — Planning Effectiveness | 1–10，衡量避免冗余或不必要工具调用的表现，越高越好；adapter 使用上游字段 `planning_and_efficiency_mean` |
| ECS — Evolutionary Competency Score | 由 TF 计算的跨版本得分；公式口径差异见[环境审计](environment.md) |

## 必交内容

| 交付 | 要求 |
| --- | --- |
| Codebase | 接入 MCPEvol-Bench 的 adaptation pipeline、自行设计的方法、两种 baselines |
| Reproduction | 已报告结果对应的 config、run commands、raw logs |
| Main results | 三种策略的 TF / PE / ECS |
| Recovery / retention | 受影响任务的恢复，以及原本可解任务的能力损失 |
| Update cost | 更新带来的 tokens、time 或 API cost |
| Failure analysis | 至少一条 under-update 和一条 over-update 的示例轨迹，并解释原因 |
| Discussion | Selective Patch 何时有效、何时失败、哪些变化最难 |
| Presentation | 10 分钟展示 + 5 分钟 Q&A；说明方法、集成、结果、失败案例与结论 |

可通过 GitHub repo 或 Google Drive 提交。课程没有规定必须采用 4 development + 8 evaluation；该数量属于尚未冻结的团队预算目标。

## Group A 的小组职责

1. 确认官方仓库、commit、依赖与模型/工具服务。
2. 安装环境，记录启动命令、凭据要求和 Python/容器版本。
3. 查明 Early/Middle/Late 切换及 judge、TF/PE/ECS 入口。
4. 完成真实 agent → MCP → judge → logs 最小任务。
5. 交付 runner adapter、metadata、执行轨迹和结果格式。

当前已交付环境、全量审计和 adapter 基础；真实模型闭环仍等待明确的模型服务配置。详情见[Group A handoff](group-a-handoff.md)。

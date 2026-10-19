# 分工与两到三周排期

Day 1 为团队启动本计划当天；按角色分工，不推断 GitHub 用户名与姓名的对应。机器可读任务及依赖见 [backlog.json](../../experiments/backlog.json)。

## 各组交什么

| 组 | 负责什么 | 输入 → 输出 | 完成证据 |
| --- | --- | --- | --- |
| A 环境与运行 | 服务配置、三阶段环境、fixtures、完整工具知识、runner、运行记录 | 官方任务 + knowledge → trace / result / ledger | 真实模型调用 MCP 后由 judge 评分；独立 checkout 可复现 |
| B 基线 | No Update、Full Rewrite | K0 + 目标 metadata → knowledge / 更新记录 | No Update 不变；Full Rewrite 覆盖全部记录；调用和成本可审计 |
| C 自研方法 | deterministic diff、依赖扩展、Selective Patch | 与 B 相同输入 → knowledge / patch / validation | 未选中记录不变；变更有依据；失败显式输出 |
| D 评测与报告 | 与 A 筛选任务、冻结、聚合、失败归因 | 原始日志 + manifest → 表格 / 案例 / 报告 | 表中每个数能回溯 run ID；缺失与负结果保留 |

## A 组内部建议分工

三人可按下表拆分；这是工作建议，不替代现有成员安排。建议 A-Run 同时承担最终集成；这些子角色与 backlog 的任务 ID 分开命名。

| 子角色 | 工作 | 给队友的接口 | 对简历最有价值的证据 |
| --- | --- | --- | --- |
| A-Run 运行与集成 | agent → MCP → judge；批次调度、断点续跑、故障分类 | `run(...)`、run ledger | 个人 commit、真实轨迹、可复现执行量与失败处理 |
| A-Env 工具环境 | 服务安装、三阶段切换、fixture reset、完整 metadata | task review、catalog / fixture hashes | 跨版本环境、持久化验证、启动和重置命令 |
| A-Audit 来源与验收 | 源码/论文差异、judge 接口、配置与成本记录、干净复现 | source audit、freeze record、复现记录 | 上游兼容性问题与解决证据、复现结果 |

## 时间表

| 时间 | A | B / C | D | 退出条件 |
| --- | --- | --- | --- | --- |
| Day 1–2 | 明确 endpoint / model；跑通 task 139 真模型链路 | 用现有 metadata 开发；mock 仅测接口 | 核对课程与指标；开始候选审查 | 一份真实 trace + 5 次有效 judge；服务可用 |
| Day 3–4 | 扩展任务环境；审查 fixtures 与完整 catalogs | 基线、diff、patch 最小实现 | 扩充候选；按任务族分 development / evaluation | 候选覆盖与排除理由明确；没有伪造任务/输入 |
| Day 5–7 | 接口补齐；开发集 pilot；运行记录/恢复 | 真实 metadata 集成；固定 prompts / 分块 / 校验 | 核对成本与任务分层；冻结配置 | 开发集验收、任务清单、模型与配置均可追溯 |
| Day 8–10 | 执行第一轮全矩阵，保留失败 | 仅处理可证实的实现缺陷；变更须升实验版本 | 同步核对有效数量、配对和案例 | 目标 72 次 agent 尝试都有记录；失败不伪装成功 |
| Day 11–14 | 独立复现；整理运行证据 | 整理方法和实际限制 | TF / PE / ECS、recovery / retention、成本、报告和展示 | 可提交课程成果；未满足项逐条列出 |
| Day 15–18 | 按同一冻结配置补 repeats 1、2 | 若时间足，开发一个独立消融 | 汇总重复波动与消融结果 | 目标 216 次执行；重复/消融不得混表 |
| Day 19–21 | 最终复现与个人贡献清单 | 整理可解释案例 | 展示演练与简历证据核对 | 队友可按 README 复现；每项结论有证据 |

## 遇到阻碍怎么缩减

| 触发条件 | 调整 | 保留的约束 |
| --- | --- | --- |
| Day 2 模型仍不可用 | A 明确服务需求；B/C 继续 metadata 开发，D 继续审查 | 不以 mock 宣称真实验收 |
| Day 4 某任务依赖无法稳定运行 | 记排除理由；从官方 selected 集合补候选 | 不按策略得分挑任务；三类变化与对照覆盖仍须审查 |
| 8 个正式任务无法达成 | 冻结前调整数量并说明覆盖损失 | 所有策略同集合；重新计算预算；不得声称满足未达到的配额 |
| 预算不足 | 3 repeats 降为 1；取消第二模型、额外领域和消融 | 三阶段、三策略、原始日志与课程要求保留 |
| 更新产物无效 | 记录 adaptation failure 和成本，修复后新版本验证 | 不静默改用 Full Rewrite；不将缺失打成 0 分 |
| 未观察到 under / over-update 案例 | 标记课程要求仍未满足；保留真实负结果，另做明确标注的诊断 | 不制造主实验失败，不把受控诊断冒充自然案例 |

## 简历证据

| 可以写的贡献 | 必须先有的证据 | 暂时不能声称 |
| --- | --- | --- |
| 设计 MCP benchmark runner 与版本化环境 | 自己的 commits、接口、真实三阶段日志 | 完成整个团队的算法 |
| 实现可恢复的实验调度与成本追踪 | 中断恢复测试、完整 ledger、usage 数据 | 仅有计划时称“已实现” |
| 对比局部/全量更新的质量与成本 | 冻结协议、配对表、真实 tokens / latency / 费用来源 | 未测量的提升百分比、完整 201 任务复现 |
| 解决真实兼容性问题 | 问题、修复、验证的对应记录 | 未验证的容器部署或生产规模 |

英文句式（完成后填写）：`Built [personally implemented component] for MCP tool-evolution evaluation across [verified scope], with [measured reliability/cost result]; reproduced through [evidence].`

# 来源与决策依据

课程要求以 S1 为准；benchmark 事实按论文与锁定发布代码交叉核对；方法和预算是本团队设计。核查日期：2026-10-19。

| ID | 一手来源 | 支持什么 | 不支持什么 |
| --- | --- | --- | --- |
| S1 | 教师文件 `PE6203 Group Project 4 - Tool Harness Adaptation under Environment Change.docx`；[仓库摘要](../project-brief.md) | 三阶段、三种策略、变化覆盖、指标、失败案例、固定子集及交付要求 | 不规定我们必须选 4 + 8 个任务或特定业务领域 |
| S2 | [小组共享分工](https://docs.google.com/document/d/1fbhITsq__0Xaxjp85qVaQxIO1kQS6oDF-RFe7G7G5kQ/edit) | A 环境/runner；B/C 方法；D 评测；交接职责 | 不是学术效果证据 |
| S3 | Liu et al. [MCPEvol-Bench, arXiv:2607.14642v1](https://arxiv.org/html/2607.14642v1)，§4、§5.2、§6.1、Appendix D.1 | 固定服务器集合、TOOL/PARAM/DESC、Early/Middle/Late、TF/PE/ECS 与 judge 机制 | 目前引用为 preprint，不宣称已获期刊同行评审；不证明我们方法有效 |
| S4 | [MCPEvol-Bench 发布代码](https://github.com/Octobrist/MCPEvol-Bench/tree/888c779a0fe735f612ca62bdd1fdd7c9e6bf8701)、[server 数据版本](https://huggingface.co/datasets/anonymous2233/evol-servers/tree/162e3ffbea1717ac8a20fe9b26465e29117229e4) | 可执行任务、chosen IDs、rubric、服务快照与代码口径 | 不把所有候选任务视作 selected 集合；不忽略与论文的差异 |
| S5 | [MCP Tools specification 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) | `tools/list`、`tools/call`、input/output schema 与错误语义 | 不是课程实验配置，也不证明服务实现完全符合规范 |
| S6 | Guo et al., [StableToolBench](https://aclanthology.org/2024.findings-acl.664/), Findings of ACL 2024；DOI `10.18653/v1/2024.findings-acl.664` | 工具/API 不稳定会妨碍可靠评测，支持控制环境与输入 | 不规定本项目的任务数；不验证本项目方法 |
| S7 | Cawley & Talbot, [On Over-fitting in Model Selection and Subsequent Selection Bias in Performance Evaluation](https://jmlr.org/papers/v11/cawley10a.html), JMLR 11 (2010), 2079–2107 | 模型选择与测试复用会导致评估偏差，支持开发/正式测评分离 | 不说明 8 个任务已经统计充分 |

S1 原始文件由课程提供，未重新上传。SHA256：`6a74fda17b7a8b9280151e55ec46b46a70d1d717e4be24c5f9c38d134611af0d`。S4 是所采用的公开实现来源；本文不额外推断维护账号与论文作者的身份关系。

## 锁定及差异处理

| 项目 | 采用口径 | 追溯 |
| --- | --- | --- |
| benchmark / server pins | 使用已锁定 commit、dataset revision、三个 ZIP SHA256 | [benchmark.lock.json](../../configs/benchmark.lock.json) |
| 阶段 | Early = original；Middle = iter3；Late = iter5 | S3 §6.1 与 S4 release |
| 任务 | 官方 selected 201 中筛选；候选总表不是正式集合 | S4 `src/custom/data/test_cases/chosen_idx.json` |
| judge | 固定 rubric；实际 judge model 在 pilot 后冻结 | 论文 DeepSeek-Chat 与代码默认 gpt-4o 的差异见 [环境审计](../environment.md) |
| ECS | 主表 population std；附表 sample std | 发布代码与论文附录差异；不得混表 |
| 运行方式 | 本项目原生 stdio adapter；记录与上游执行方式的差异 | [环境审计](../environment.md)；不称论文 leaderboard 复现 |

## 团队决策

| 决策 | 理由 | 性质 |
| --- | --- | --- |
| 两个主要业务方向 | 状态可检查、输入可固定，适合两到三周 | 工程判断；具体任务仍需验证 |
| 4 开发 + 8 正式；覆盖配额 2/2/2/2 | 平衡课程覆盖、调试与调用成本 | 预算目标；可在冻结前有据调整 |
| Diff-guided Selective Patch | 将结构变化定位与局部语义更新结合 | 待检验研究方法 |
| Middle / Late 独立从 K0 更新 | 避免累积更新误差干扰主比较 | 主协议选择；非 benchmark 强制 |
| 单模型；3 repeats 优先、1 次降级 | 优先完成公平、可复现的全矩阵 | 课程允许单次披露；时间预算选择 |
| 保留低分、失败与 unknown | 防止选择性报告，支持真实贡献陈述 | 实验完整性要求 |

# MCP 工具变化适应实验报告

状态：待填写。本文是模板，所有 `—` 都不是实验结果。

## 实验身份与覆盖

| Experiment ID / commit | Freeze / manifest | Agent / updater / judge | 子集 / repeats | 运行方式 |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

| Domain | Development IDs | Evaluation IDs | TOOL / PARAM / DESC | Retention controls | Fixture 来源 / 替代 |
| --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | — |

## 主结果

每个 stage × strategy 一行；先平均重复再平均任务。完整配对集合与各策略缺失情况同时报告。

| Stage | Strategy | 计划 / 有效 runs | Matched tasks | TF mean / repeat spread | PE mean / repeat spread | 失败率 |
| --- | --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | — | — |

| Strategy | 完整 triplets / 计划 | ECS population | ECS sample sensitivity | 排除 IDs / 原因 |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

| Transition | Strategy | Changed n / recovery ΔTF | Unaffected n / retention update ΔTF | Retention vs Early ΔTF | Uncertain IDs |
| --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | — |

## 成本与质量取舍

| Strategy | 唯一更新 artifacts | Update input / output tokens | Update wall seconds | Update USD | Agent / judge USD | 缺失 usage / price |
| --- | --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | — | — |

价格来源、日期、缓存计价：—。基础设施重试与失败支出：—。相对 Full Rewrite 的成本差异必须和 TF/PE 差异一起解读；不只比较最佳运行。

## 真实失败案例

| 类型 | Task / stage / strategy / run ID | Metadata diff / patch | 实际错误与工具返回 | 归因依据 / 其他可能解释 | Trace 链接 |
| --- | --- | --- | --- | --- | --- |
| under-update | — | — | — | — | — |
| over-update | — | — | — | — | — |

未观察到的类型标记“未观察到，课程要求仍待满足”。受控诊断单列，不混入主结果。

## 结论边界与复现

| 项目 | 内容 |
| --- | --- |
| RQ1 recovery | — |
| RQ2 retention | — |
| RQ3 cost | — |
| 负结果 / 缺失是否影响比较 | — |
| 子集规模 / 任务族 / 随机性限制 | — |
| 与论文模型、judge、运行方式的差异 | — |
| 干净 checkout 命令 / 版本 / 复现证据 | — |

## 个人贡献

| 成员 | 本人负责的组件 / 决策 | Commit / 文件 | 验证证据 | 可陈述的测量结果 | 团队共同成果 |
| --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | — |

## 十分钟展示

| 分钟 | 内容 | 必须展示的证据 |
| --- | --- | --- |
| 0–1 | 问题与研究假设 | 真实工具变化示例 |
| 1–3 | Benchmark、子集与公平控制 | 冻结表、三策略输入边界 |
| 3–5 | Selective Patch | diff → patch → validation 实例 |
| 5–7 | 质量与成本 | TF/PE/ECS、recovery/retention、成本表 |
| 7–9 | 两类失败与复现 | 真实轨迹、run ID、README 命令 |
| 9–10 | 结论与限制 | 实际发现、未解决项、成员贡献 |

另预留 5 分钟 Q&A。

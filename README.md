# PE6203 · 工具变化下的 Harness 适应

**当前目标：完成可复现、可辩护的课程项目。** 采用「最小实验 → 验证与交付 → 获批后才扩展」。策略搜索已暂停；任何新增实验、API 探测或重跑都先获用户批准。

| 当前选择 | 说明 |
| --- | --- |
| 主实验 | MCPEvol-Bench 固定 **133 / 283** 变化任务、**235** 未变化任务；Early / Middle / Late × No Update / Full Rewrite / Selective Patch × **1 次**＝27 条。已完成，无需重跑。 |
| 覆盖 | PARAM、DESC 涉及任务所需工具；TOOL 是相关可选工具新增，不覆盖必需工具删除/重命名。235 用于 retention。 |
| 模型 | OpenRouter `deepseek/deepseek-v4.1-flash-1017`，agent / judge / updater 固定；temperature 0。 |
| 预算和评分 | agent 4096 输出 tokens、12 轮、900 秒；judge 4096、关闭 reasoning、JSON 输出，每轨迹 5 个首次有效评分槽。配置：`configs/course-benchmark-v1.3.json`。 |
| 完成标准 | 代码、三方法对照、TF/PE/ECS、recovery/retention、更新成本、可信失败分析、可复现材料与展示齐全；不要求 Patch 获胜。 |
| 可选演示 | 139 用于调试；223「论文检索→网页」/ Netlify 单列自定义环境演示，不阻塞课程主实验。 |

**三种方法均由 agent 自动选择工具、参数和下一步。** 原任务固定候选 MCP servers；No Update 保留 Early 知识，Full Rewrite 重建全部目标记录并用 LLM 重写全部描述，Selective Patch 用元数据差异与依赖规则更新受影响记录。模型相同，更新范围选择是确定性算法。范围与生成机制同时不同，不能声称纯范围消融。

当前主实验 **27/27 轨迹有评分、135/135 评分槽有效**，其中 **20 正常完成、5 轮数耗尽、2 输出截断**。一次执行符合 brief 的计算预算例外；5 个 judge 评分不等于5次执行。独立复算、终态恢复和归档离线复现已通过。报告、独立复算与共享演示已整理；主要缺口仍是严格的 patch under-update / over-update 例证，以及组内审阅/排练；6 条回退诊断未证实 over-update，负结果保留。

- **交付审阅入口**：[报告、复现包、案例与演示](submission/index.html)。九个 Selective Patch PE 合计82，平均9.1111；正常完成6/9。
- **冻结计划**：[课程完成计划](reports/course-completion-plan.html)，机器依据：`experiments/course-completion-plan.json`；最新交付状态以审阅入口及 `submission/.context/delivery-status.json` 为准。
- **主实验**：[27 条结果、指标与案例](reports/course-v1.3-experiment.html)。
- **历史研究**：[全部成功与失败记录](reports/selective-strategy-search.html)；108 条 R1 已完成，其中原三方法81条各有3次重复，可独立作附录。R2/R3 因连接失败停止，不再自动恢复。PE +0.5 等阈值仅为历史研究标准。
- **旧课程试验**：[A/B 的 54 条记录](reports/experiment-readiness.html)，与 v1.3 分开，不回填或混算。

## 使用

当前仅做离线检查，不调用模型：

```bash
python3 results/evidence/course-completion-20261031/audit_reuse.py
```

复现时先用 `uv sync --frozen` 安装依赖。`./experiment` 是中文交互入口，自动加载本机 `.env`；勿提交密钥。**以下是真实实验的参考命令，需批准后使用，不要对已完成主实验再次执行：**

```bash
./experiment prepare --suite experiments/benchmark-v1.3.json --repeats 1 --output results/raw/approved-new-run
./experiment run --output results/raw/approved-new-run
./experiment report --output results/raw/approved-new-run
```

框架仍可配置；现有 CLI 省略 `--repeats` 默认3次，当前课程方案必须显式写1。冻结源码/配置变化后应使用新实验ID，不恢复旧冻结运行。历史数据的离线复算使用归档内源码，命令见 `results/evidence/course-v1.3-20261031/reproduction.json`。

执行记录与 judge 分数分开。低分、截断和失败不能被重跑覆盖；缺失评分仅在原次数预算内恢复，连接失败费用未知不能填零。`analysis/` 保存 TF/PE/ECS、恢复/保持、成本和缺失表。已确认的发布包缺陷与连接故障单列，不自动算成补丁错误。

## 可选 Netlify 流程

如以后批准网页演示，使用 `./experiment papers`。CLI 在准备/冻结前显示账号、引导用户浏览器登录和选择专用站点；agent 在运行时决定是否调用部署工具。只发布 draft。223 三阶段目录相同，不能独自证明恢复能力，结果不与原发布环境混算。具体流程在 `docs/.context/experiment-cli.json`。

## 文件放在哪里

| Folder | 用途 |
| --- | --- |
| `src/pe6203/`、`integration/` | CLI、三种方法、MCP/agent/judge、统计与外部集成。 |
| `configs/` | 固定模型、服务与预算；`.context/` 是机器说明。 |
| `experiments/` | 当前完成计划、冻结子集/协议、历史研究计划和评估模板。 |
| `examples/catalogs/`、`fixtures/` | 开发工具目录和输入。 |
| `results/raw/` | 本机冻结计划、知识、原始轨迹、评分、费用；不提交。 |
| `results/evidence/`、`results/evaluation/` | 可分享归档、hash、离线审计和整理结果。 |
| `tests/`、`scripts/` | 测试、核验与报告工具；先核对命令是否调用真实服务。 |
| `submission/` | 离线复算脚本、最终报告审阅稿、原始证据包、讲稿与共享演示链接。大型归档仅本机打包。 |
| `reports/` | 可读计划、主结果与完整成功/失败案例；历史结果不覆盖。 |
| `docs/`、`contributions/` | 机器说明、来源与成员贡献记录。 |
| `tools/netlify/` | 可选 Netlify CLI 的版本与依赖锁。 |
| `.cache/`、`.venv/`、`.netlify/` | 本机依赖、环境、登录关联，不提交。 |

# PE6203 · 工具变化下的 Harness 适应

**课程主实验与交付已冻结；后续研究另行归档。** 用户现已授权以完成任务为先，不设研究总费用或轨迹额度；仍固定公平比较设置，记录费用和失败，不覆盖旧结果，不自动部署。

| 当前选择 | 说明 |
| --- | --- |
| 主实验 | MCPEvol-Bench 固定 **133 / 283** 变化任务、**235** 未变化任务；Early / Middle / Late × No Update / Full Rewrite / Selective Patch × **1 次**＝27 条。已完成，无需重跑。 |
| 覆盖 | PARAM、DESC 涉及任务所需工具；TOOL 是相关可选工具新增，不覆盖必需工具删除/重命名。235 用于 retention。 |
| 模型 | OpenRouter `deepseek/deepseek-v4.1-flash-1017`，agent / judge / updater 固定；temperature 0。 |
| 预算和评分 | agent 4096 输出 tokens、12 轮、900 秒；judge 4096、关闭 reasoning、JSON 输出，每轨迹 5 个首次有效评分槽。配置：`configs/course-benchmark-v1.3.json`。 |
| 完成标准 | 代码、三方法对照、TF/PE/ECS、recovery/retention、更新成本、可信失败分析、可复现材料与展示齐全；不要求 Patch 获胜。 |
| 可选演示 | 139 用于调试；223「论文检索→网页」/ Netlify 单列自定义环境演示，不阻塞课程主实验。 |

**三种方法均由 agent 自动选择工具、参数和下一步。** 原任务固定候选 MCP servers；No Update 保留 Early 知识，Full Rewrite 重建全部目标记录并用 LLM 重写全部描述，Selective Patch 用元数据差异与依赖规则更新受影响记录。模型相同，更新范围选择是确定性算法。范围与生成机制同时不同，不能声称纯范围消融。

当前主实验 **27/27 轨迹有评分、135/135 评分槽有效**，其中 **20 正常完成、5 轮数耗尽、2 输出截断**。一次执行符合 brief 的计算预算例外；5 个 judge 评分不等于5次执行。独立复算、终态恢复和归档离线复现已通过。报告、独立复算与共享演示已整理；受控缺参及新增无关路由误改的局部损害机制已确认，课程是否接受此类注入案例待 TA 判断；自然 updater 失误未证实。brief 未要求失败必须自然发生。新增路由附录尚未合入冻结 PDF/Slides。6 条旧回退负结果保留；组内审阅/排练待完成。

- **最新观测契约研究**：[6条开发对照](reports/observed-contract-pilot.html)：定位并实测新校验控制未落实及非报错响应语义丢失；候选完成/TF提高，但必需产物仍有代码错误。已冻结36条独立重复，尚无可复现双重改善结论。状态见 HANDOVER。
- **最新交付**：[审阅入口](submission/handover-20261031/index.html)、[整合报告](submission/report-final.html)、[PDF](submission/PE6203-final-report.pdf)、[HANDOVER](HANDOVER.md)。核查结论、未发送的 TA 问题及下一步以此为准。
- **获批诊断历史附录**：[4条受控诊断与复算](submission/diagnostics-20261031/index.html)：20个评分，$0.046002，已停止扩展；缺参机制已确认，额外规则影响仍为提示性证据。原报告和复现包保持冻结；课程适用性以最新整合报告 Appendix E 为准。
- **历史交付快照**：[报告、复现包、案例与演示](submission/index.html)。九个 Selective Patch PE 合计82，平均9.1111；正常完成6/9。
- **冻结计划**：[课程完成计划](reports/course-completion-plan.html)，机器依据：`experiments/course-completion-plan.json`；这是原冻结计划；最新状态见 `HANDOVER.md` 与 `submission/handover-20261031/findings.json`。
- **主实验**：[27 条结果、指标与案例](reports/course-v1.3-experiment.html)。
- **历史研究**：[全部成功与失败记录](reports/selective-strategy-search.html)；108 条 R1 已完成，其中原三方法81条各有3次重复，可独立作附录。R2/R3 因连接失败停止，不再自动恢复。PE +0.5 等阈值仅为历史研究标准。
- **完成率 / 质量后续试验**：[获批 12 条结果](reports/completion-quality-results.html)：两组均完成 4/6，候选未晋级；总费用 $0.157216447，无未知项。与课程主矩阵分开。 [六条预算规则试验](reports/budget-contract-results.html)也已获批完成：两组均完成3/3，新候选 TF/PE 更低，不晋级；费用 $0.089010216；以上均为历史轮次。
- **最新补充对照**：[9条新增＋3条复用](reports/matched-existing-results.html)：候选完成6/6、TF9.8；原Patch完成2/6、TF9.4。新费用 $0.151974408；两批次且候选仍有代码/总结错误，未通过质量检查，不晋级。当前授权与下一步见 HANDOVER。
- **最新规则试验**：[6条证据边界对照](reports/evidence-scope-results.html)：新候选完成1/3，对照2/3；TF9.6对9.8，不晋级。费用$0.107351724，历史结果保留。
- **工具删除补充验证**：[task430 的12条三阶段对照](reports/tool-migration-results.html)：原Patch/budget_feedback均正常完成3/3，NU/FR各1/3，平均TF均9.9333。旧工具失败7次对0次；候选仍有附加代码错误，不能称全面提高质量。费用$0.128198580，未知0；独立复算和原始证据已归档，与27条主实验分开。
- **无关知识故障补充**：[两条路由受控诊断](reports/routing-fault-results.html)：仅改错未变化的Wikipedia路由，直接重放与agent均证实读取损害；两组仍完成任务。正常验证器能拒绝该故障，不能称自然方法失败。$0.021366768、未知0，课程是否接受仍待TA确认。
- **实时信息恢复补充**：[task90 的12条三阶段对照](reports/daily-migration-results.html)：四方法均正常结束3/3；原Patch/预算反馈TF均10，No Update为8.9333（Late漏取每日题），全部图片抓取成功。$0.202212588、未知0；未证明预算反馈胜过原Patch。新增审计区分官方1000字符截断与judge误判，原评分不变。
- **旧课程试验**：[A/B 的 54 条记录](reports/experiment-readiness.html)，与 v1.3 分开，不回填或混算。

## 使用

离线检查（不调用模型）：

```bash
python3 submission/handover-20261031/verify.py
```

复现时先用 `uv sync --frozen` 安装依赖。`./experiment` 是中文交互入口，自动加载本机 `.env`；勿提交密钥。**以下是真实实验的参考命令；不要对已完成主实验再次执行：**

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
| `submission/` | 离线复算脚本、最终报告审阅稿、原始证据包、讲稿与共享演示链接。冻结原始包可离线复算；大型 ZIP 保留本机。 |
| `reports/` | 可读计划、主结果与完整成功/失败案例；历史结果不覆盖。 |
| `docs/`、`contributions/` | 机器说明、来源与成员贡献记录。 |
| `tools/netlify/` | 可选 Netlify CLI 的版本与依赖锁。 |
| `.cache/`、`.venv/`、`.netlify/` | 本机依赖、环境、登录关联，不提交。 |

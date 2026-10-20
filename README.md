# PE6203 · 工具变化下的 Harness 适应

研究工具名称、参数或说明改变后，怎样更新 agent 的工具知识，恢复任务表现，同时保留其它能力并减少更新成本。

| 当前选择 | 说明 |
| --- | --- |
| 主优化案例 | **task 223：抓取最新 5 篇具身智能论文 → 生成并发布网页**。对应 fetcher-mcp + edgeone-pages-mcp，运行配置尚待接入。 |
| 其它测试 | **139** 作开发 smoke；24/28 日志处理、393 项目管理、226 图表、450 数据可视化作回归候选。正式测试集尚未冻结；用于调优的 223/139 不算独立测试。 |
| 通用模型 | **DeepSeek v4.1 Flash**，OpenRouter ID：`deepseek/deepseek-v4.1-flash-1017`。Agent/judge 已使用；updater 计划同模型，**Selective 的确定性补丁已实现；LLM 规则更新为可选、默认关闭**。 |
| 基础设置 | temperature 0；agent 上限 2048 tokens、12 轮；judge 上限 4096 tokens、关闭 reasoning，每条轨迹评分 5 次。 |
| 对比方案 | Early / Middle / Late × No Update / Full Rewrite / Selective Patch；比较 TF、PE、ECS、能力保持与更新成本。 |
| 当前进度 | 两基线 + **Selective Patch（Diff-guided）已接入**；**Full Rewrite 仍是确定性全量重建**，LLM 重写待做。139 曾通过真实闭环（TF 9.8、PE 8.6）；现 **75 项离线测试通过**。Selective 已在 task139 真实目录上生成补丁（10 改 + 4 增、30 保留、0 token），但尚未跑真实 agent 任务；完整 benchmark 未完成。 |

| Folder | 放什么、做什么 |
| --- | --- |
| `src/pe6203/` | 实现：环境安装、MCP 调用、baseline 更新、agent 执行、judge 评分、批量运行。 |
| `tests/`、`scripts/` | 自动测试与服务探测脚本；fake model 测试只验证程序接线。 |
| `configs/` | 可执行配置、版本锁和服务启动配置；`.context/project.json` 记录项目选择。 |
| `examples/catalogs/` | 三阶段完整工具目录，供 baseline/updater 使用。 |
| `fixtures/` | 固定测试输入的来源与文件 hashes；大文件实际放 `.cache/`。 |
| `experiments/` | 实验协议、候选任务、分工待办、记录模板；不是可执行 runner config。 |
| `results/` | `raw/` 放本机原始日志；`evidence/` 放已审查证据，包括失败记录。 |
| `docs/` | `.context/` 保存精简后的课程要求、来源及论文/代码差异。 |
| `contributions/`、`reports/` | 组员贡献来源、报告与展示所需字段；详细资料在各自 `.context/`。 |
| `.github/` | CI 自动检查。 |
| `.cache/`、`.venv/` | 下载的 benchmark/Node 与 Python 环境；不提交 Git。 |

只需日常阅读这份 README；其余说明已按用途收进各目录的 **`.context/`**。`AGENTS.md` 是机器读取入口。
模型 key/endpoint 留在本机 `.env`；当前可用配置是 `configs/local.smoke-no-reasoning.json`，两者不提交 Git。
安装和运行命令见 [机器运行说明](configs/.context/runtime.json)，实际验证见 [证据](results/evidence/baseline-integration/verification.json)。

```bash
uv sync --frozen
uv run pytest -q tests/test_baselines.py tests/test_pipeline.py
```

真实 MCP 测试需要先按运行说明 bootstrap；缺少发布包时会 skip，不能当作验证通过。

## Selective Patch：一条知识怎样更新（task 139，Early → Late）

1. **哪条知识过时**：Early 知识里的 `create_project` 工具，其 `parameters` 在 Late 环境改变；同时 Late 多了 `review_project_status` 等 4 个新工具。
2. **如何发现**：`diff_catalogs` 用普通代码按 `server_id::name` 比较新旧目录（对象键排序规范化、数组顺序与正文保留），记录 10 条 `changed`、4 条 `added`、0 条 `removed`。改名若无证据则按“旧项消失 + 新项出现”处理，不靠名字相近猜。
3. **改了哪里**：只重写受影响的 14 条记录——结构化字段（名称/参数/输出说明/路由）直接取自目标环境，其余 30 条记录保持与 Early **逐字（canonical）相同**；不凭空编造字段或规则。
4. **怎样检查**：`validate_adaptation` 校验 schema 结构、路由与身份、受改记录是否都有目标依据、未选记录是否被误改、以及是否留有指向已删除工具的悬空引用。
5. **怎样进入 ChatModel**：校验通过后保存完整快照（不是只返回 patch），共用 `runner.prepare_tools` 把该组工具定义与规则编译进模型请求；工具调用仍走共用执行器，三组完全一致。

```bash
# 生成补丁（确定性、不调用 LLM）
uv run pe6203 adapt --strategy selective_patch \
  --old-knowledge examples/catalogs/task139/early.json \
  --new-metadata examples/catalogs/task139/late.json \
  --output results/raw/NEW_ID/adaptation
# 随后让执行器使用该补丁（需先 bootstrap + 配置 key）
uv run --env-file .env pe6203 run --task-id 139 --version late \
  --strategy selective_patch --config configs/local.smoke-no-reasoning.json \
  --adaptation results/raw/NEW_ID/adaptation/adaptation.json --output results/raw/NEW_ID/run
```

可读样例见
[task139-early-to-late.sample.json](contributions/haoqi/examples/task139-early-to-late.sample.json)；
共用底座改动见 [COMMON_AGENT_CHANGES.md](COMMON_AGENT_CHANGES.md)；初步结果见
[preliminary-report.md](contributions/haoqi/sprint1/preliminary-report.md)。
真实 agent 任务与 TF/PE/ECS 尚未运行（缺 bootstrap 与 key），不得当作成绩。

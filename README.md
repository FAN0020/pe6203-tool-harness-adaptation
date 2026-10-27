# PE6203 · 工具变化下的 Harness 适应

研究工具名称、参数或说明改变后，怎样更新 agent 的工具知识，恢复任务表现，同时保留其它能力并减少更新成本。

| 当前选择 | 说明 |
| --- | --- |
| 主优化案例 | **task 223：抓取最新 5 篇具身智能论文 → 生成并发布网页**。对应 fetcher-mcp + edgeone-pages-mcp，运行配置尚待接入。 |
| 其它测试 | **139** 作开发 smoke；24/28 日志处理、393 项目管理、226 图表、450 数据可视化作回归候选。正式测试集尚未冻结；用于调优的 223/139 不算独立测试。 |
| 通用模型 | **DeepSeek v4.1 Flash**，OpenRouter ID：`deepseek/deepseek-v4.1-flash-1017`。Agent/judge 已使用；Full Rewrite updater 已接入，设置见 `configs/full-rewrite-updater.template.json`。 |
| 基础设置 | temperature 0；agent 上限 2048 tokens、12 轮；judge 上限 4096 tokens、关闭 reasoning，每条轨迹评分 5 次。 |
| 对比方案 | Early / Middle / Late × No Update / Full Rewrite / Selective Patch；比较 TF、PE、ECS、能力保持与更新成本。 |
| 当前进度 | 通用 `adapt` 入口已接入 **LLM Full Rewrite**，No Update 保持 Early 知识；新入口用模拟 updater 测试，不代表已完成真实实验。Selective Patch 尚待从 C 组分支整合；正式协议和测试集尚未冻结。 |

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

Full Rewrite 通用入口及其后续 `run --adaptation` 用法见 [LLM 基线接入说明](docs/common-llm-baselines.md)。真实更新需要显式 `--allow-metadata-api`，会产生模型费用；未授权或重写失败时不会退回确定性重建。

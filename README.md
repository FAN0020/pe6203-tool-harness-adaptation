# PE6203 · 工具变化下的 Harness 适应

固定模型，比较 **No Update / Full Rewrite / Selective Patch** 在 Early、Middle、Late 的表现。
使用锁定的 MCPEvol-Bench 发布包和原始任务/评分 rubric；课程子集实验，不宣称复现论文 leaderboard。

| 当前选择 | 说明 |
| --- | --- |
| 固定 benchmark | **133** 数学表达式与安全建议、**283** 项目拆解（变化案例）；**235** 销售图表（保持能力对照）。详见 `experiments/benchmark-v1.json`。 |
| 开发案例 | **139** 最小调试；**223** 检索最新 5 篇具身智能论文 → 网页，单列 Netlify 环境替代实验。 |
| 模型 | OpenRouter `deepseek/deepseek-v4.1-flash-1017`，agent/judge/updater 固定。 |
| benchmark 设置 | temperature 0；agent 输出 4096 tokens、最多 12 轮；judge 输出 4096、关闭 reasoning、JSON 模式，每条轨迹评分 5 次。 |
| 重复次数 | 默认 3 次＝81 条轨迹 / 405 次 judge；预算版 1 次＝27 条 / 135 次 judge。 |
| 范围限制 | TOOL 是相关工具的新增；PARAM/DESC 涉及任务所需工具。无必需工具重命名/删除；283 与开发案例共享服务，不能宣称独立任务族泛化。 |

**三种方法都由 agent 自动选择工具、参数和下一步。** 没有预写工具调用顺序。
候选 MCP servers 由原始 benchmark 任务固定；agent 在提供的工具目录中选择，不会自行接入任意外部服务。
区别只在供 agent 使用的知识：No Update 保留 Early；Full Rewrite 重建全部目标记录并用 LLM 重写全部描述；Selective Patch 自动用元数据差异和依赖规则选择需要更新的记录，其余保留。Selective Patch 的更新范围选择是确定性算法，不是另一个 LLM。三者的运行 agent 相同。

## 直接跑 benchmark

`.env` 自动加载，只保存本机 key/endpoint，不提交。

```bash
uv sync --frozen
./experiment                              # 中文菜单：7 准备 benchmark，4 运行，5 结果
./experiment check --api                   # 最小真实 API 检查，会计费
./experiment prepare --suite experiments/benchmark-v1.json --repeats 1
./experiment run                          # 调用真实模型
./experiment report
```

省略 `--repeats 1` 即按建议重复 3 次。新机器先运行 `uv run pe6203 bootstrap --scope all`，固定 Node 安装见 `configs/.context/runtime.json`。

- 只先执行一条：`./experiment run --limit 1`；继续：`./experiment run --resume`。
- 指定历史实验：run/report 加 `--output results/raw/目录名`。
- 临时调试：`./experiment prepare --tasks 139`；不计入固定子集结果。
- run 自动做真实 API 预检，费用单列在 `preflight/`；连续两条连接失败即停止，后续单元保持未运行。
- 模型临时连接错误、429/5xx：同一请求最多自动重试 1 次，保留失败记录和未知费用。工具调用、低分、无效输出不自动重跑。
- 代码/配置变更后新建实验；不覆盖旧轨迹。正式子集配置修改需要新 suite。

`analysis/` 自动输出三策略匹配的 TF/PE/ECS、recovery/retention、费用、失败和缺失记录。五次有效 judge 才计分；ECS 要三阶段三策略齐全。`summary.json` / `runs.csv` 保留逐条结果；截断、超时、轮数耗尽与完成分开显示。

2026-10-31 复核：27 条均已尝试，24 条完整评分；17 条执行完成、7 条轮数耗尽、2 条生成额度耗尽、1 条连接失败。judge 截断及连接故障使本轮 **没有完整匹配的 ECS 组**。282 项测试通过；断网复算、知识快照和 resume 已验证。逐项验收与原始记录见 [`results/evidence/finalized-trial-20261031/verification.json`](results/evidence/finalized-trial-20261031/verification.json)。实验可运行，完整主结果、因果失败案例和最终报告/展示仍未就绪；历史试跑不用于补齐本轮缺失。

可读入口：[`剩余计划与历史成功/失败案例`](reports/experiment-readiness.html)（含全部 54 条课程试跑记录）。下一版评分恢复与 Netlify 账号核对仍是待实施计划，不改变当前协议；机器说明在 `reports/.context/`。

已确认的发布包缺陷保留在所有方法中：Late `batch_evaluate` / `sequentialthinking` / `review_workspace_health` 缺失内部方法，以及新增 `parallel-thinking` 的输出 schema 不匹配。不能把这些直接归因为 under/over-update。**课程报告仍需基于真实轨迹完成两类错误的因果分析**；低分不自动证明原因。

## 论文网页与 Netlify

```bash
./experiment papers                       # 或菜单 3：检查/安装→登录→关联站点→来源→运行
./experiment papers --prepare-only        # 完成准备后，用 run 启动
```

向导打开 Netlify 登录，由你在浏览器完成，并在终端选择已有专用站点；已有有效登录和关联会复用。仅上传生成的单个 HTML 到 draft URL，不覆盖生产站点。可用 `--source-url 'HTTPS论文列表地址'` 指定来源。

所有方法共用带时间/hash 的来源快照；agent 自动抓取、按发布日期选择相关的最新 5 篇并发布。检索结果前五条不一定最新，不能用旧论文掩盖抓取失败。快照回放禁用脚本/子资源，只允许固定来源。223 三阶段工具目录相同，用于网页流程与保持能力验证，不能独自证明恢复能力；结果不与原发布环境混算。真实发布需你完成登录后验证。

## 文件放在哪里

| Folder | 用途 |
| --- | --- |
| `src/pe6203/` | CLI、Selective Patch、MCP/agent/judge、重试、统计、Netlify 适配。 |
| `integration/` | LLM Full Rewrite、模型接口及描述约束检查。 |
| `configs/` | 固定模型、服务配置；`.context/` 是简短机器说明。 |
| `experiments/` | 固定子集、覆盖标签、选择依据、协议和评估模板。 |
| `examples/catalogs/`、`fixtures/` | 开发工具目录、已有输入；固定子集无需外部文件 fixture。 |
| `results/raw/` | 本机 plan、知识、完整轨迹、评分、分析结果；不提交。 |
| `results/evidence/`、`results/evaluation/` | 可审计验证证据和已整理结果。 |
| `tests/`、`scripts/` | 自动测试与真实 MCP 探测；`verify_benchmark.py` 不调用模型。 |
| `tools/netlify/` | Netlify CLI 版本和依赖锁。 |
| `contributions/`、`docs/`、`reports/` | 贡献、机器说明、历史与报告材料；当前说明以此 README 为准。 |
| `.cache/`、`.venv/`、`.netlify/` | 本机发布包、环境和站点关联，不提交。 |

机器入口：`docs/.context/experiment-cli.json`。历史证据代表当时版本，不覆盖当前协议。

# PE6203 · 工具变化下的 Harness 适应

固定模型，比较 **No Update / Full Rewrite / Selective Patch** 在 Early、Middle、Late 的表现。
基于锁定版本的 MCPEvol-Bench；这是课程开发实验工具，不宣称复现论文 leaderboard。

| 当前选择 | 说明 |
| --- | --- |
| 主案例 | **223：检索最新 5 篇具身智能论文 → 发布网页**。按用户要求改用 Netlify，用户自己登录；明确记录为环境替代实验。 |
| 最小可运行子集 | **139：项目、任务与知识图谱**，原发布服务，有工具变化。默认 3 阶段 × 3 策略 × 1 次 = **9 条轨迹、45 次 judge**。 |
| 模型 | OpenRouter `deepseek/deepseek-v4.1-flash-1017`；agent/judge/updater 的实际设置写进每次实验的 plan。 |
| 基础设置 | temperature 0；agent 最多 12 轮、输出 2048 tokens；judge 输出 4096、关闭 reasoning、评分 5 次。 |
| 三种方法 | No Update 保留 Early；Full Rewrite 用 LLM 重写全部目标描述；Selective Patch 确定性更新受影响记录，其余保持不变。 |
| 实验边界 | 139/223 是开发案例；独立测试集、恢复/保持标签及 under/over-update 因果案例仍须审查。1 次允许但需披露，推荐 3 次。 |

## 直接使用

在仓库目录运行；`.env` 自动加载。模型 key/endpoint 只放本机 `.env`，不要提交。

```bash
uv sync --frozen
./experiment                         # 中文交互菜单
./experiment check                   # 检查环境，不调用模型
./experiment check --api             # 最小真实 API 检查，会计费
./experiment prepare --tasks 139      # 固定配置/目录/代码，无模型调用
./experiment run                     # 运行最近准备的实验，会计费
./experiment report                  # TF/PE/ECS、费用与每条执行状态
```

新机器先按 `configs/.context/runtime.json` 安装固定 Node 与服务：
`uv run pe6203 bootstrap --scope smoke` 可用于 139；网页案例需要 `--scope all`。

- 只试 1 条：`./experiment prepare --tasks 139 --stages late --strategies selective_patch`，然后 `./experiment run`。
- 重复 3 次：`./experiment prepare --tasks 139 --repeats 3`。
- 控制本次工作量：`./experiment run --limit 1`；继续：`./experiment run --resume`。
- 指定实验：上述 run/report 增加 `--output results/raw/实验目录`。
- 更换模型/轮数：先修改忽略的 `configs/local.smoke-no-reasoning.json`，再 prepare。

**失败、超时和低分都保留，不自动重跑。** 源码、配置或输入变化后须新建实验。
完整五次 judge 才纳入分数；三阶段不齐时 ECS 为 null。`max_rounds` 仍显示，评分完成不等于任务完成。

## 论文网页与 Netlify

```bash
./experiment netlify install          # 固定版本 CLI + Chromium
./experiment netlify login            # 你在浏览器完成登录
./experiment netlify link             # 选择你创建的专用实验站点
./experiment prepare --tasks 223 --netlify --source-url '研究论文列表的HTTPS地址'
./experiment run
```

也可用本机 `NETLIFY_SITE_ID` 指定专用站点。只发布生成的 HTML 到 **draft URL**，不覆盖生产版本；发布后检查匿名访问。

当前锁定发布包中，223 两个服务的工具目录三阶段相同；它用于网页流程/保持能力候选，不能独自证明更新策略的恢复能力。

CLI 保存来源网页、抓取时间和 hash；所有比较读取同一快照，通过原发布版本的 fetcher 抓取。
“最新”指快照时该来源的最新列表：开始实验前确认主题，并按发布日期选择最新 5 篇，不能直接把检索前 5 条当作最新；不能以旧论文替代抓取失败。
来源可能限流，可显式选择其它研究网站，例如 Hugging Face Papers 的主题检索页；不会静默换源。
Netlify 替代发布服务、固定来源提示、禁用网页脚本/资源回放，以及仅支持单 HTML 的限制均记录为 variant；不能混入原版环境的分数。

## 文件放在哪里

| Folder | 用途 |
| --- | --- |
| `src/pe6203/` | CLI、三策略统一入口、Selective Patch、MCP/agent/judge、统计和 Netlify 适配。 |
| `integration/` | LLM Full Rewrite、模型接口及描述约束检查。 |
| `configs/` | 模型与服务配置；`.context/` 保存项目选择和运行细节。 |
| `examples/catalogs/`、`fixtures/` | 工具目录、测试输入来源；CLI 会另存本次实际目录。 |
| `experiments/` | 课程协议、候选任务、正式评估所需模板。 |
| `results/raw/` | 本机 plan、目录、适配产物、轨迹、评分、summary.json、runs.csv；不提交。 |
| `results/evidence/`、`results/evaluation/` | 经审查的运行证据和评估结果。 |
| `tests/`、`scripts/` | 自动验证和环境探测；模拟模型测试不算实验分数。 |
| `tools/netlify/` | 固定 Netlify CLI 版本及依赖锁。 |
| `contributions/`、`docs/`、`reports/` | 贡献来源、历史说明、课程/论文差异与报告；先看当前 README。 |
| `.cache/`、`.venv/`、`.netlify/` | 本机环境和站点关联，不提交。 |

机器协议与资源说明：`docs/.context/experiment-cli.json`。历史报告反映当时状态，不覆盖当前实现。

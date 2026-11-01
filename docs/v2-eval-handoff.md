# QI-V2 对照评估接手说明

当前状态：评估流程已准备并通过离线测试，真实 V2 benchmark 尚未运行。
本次环境没有 AGENT_API_KEY/JUDGE_API_KEY，也没有上游 checkout 和三阶段 MCP 安装。
`results/evaluation/v2-eval/readiness.json` 记录实际检查；模型调用 0 次，无新增费用。

## 比较对象

- QI-V2 固定到 `bdf0ccc5c3466517725c84e7f715234733cde4a8`，公共入口默认 hybrid_v2。
- main 基线固定到 `d32e44bb73a75bb84dec81e597e8832a63373950`。
- QI-V2 从该 main 继承。去掉 selective_patch 分派后，baselines.py 的 AST 与 main 完全相同。agent、judge、实验运行器、两种基线的 integration 实现和课程配置的 Git blob 身份相同，见协议与 baseline-parity.json。
- 新批次：133/235/283 × Early/Middle/Late × No Update/Full Rewrite/QI-V2 × 1 次 = 27 条执行、135 个评分槽。旧 V1 的 27 条结果不混入。
- 使用 main 的课程 updater 配置：相同模型、温度 0、16384 输出 tokens、120 秒请求超时。QI-V2 的 4096-token 合成 smoke 模板不是本轮配置。V2 内部保留每次更新最多 16 次请求、300 秒、每批 6 条记录的限制。
- updater 不接收原题、参考答案或分数。此矩阵未提供额外 argument regression cases；不得写成已运行这些测试。

## 在已有运行环境中执行

在仓库根目录切到 `V2-eval`，保留可用的 `.cache` 和本机 `.env`，不要提交密钥。
`.env` 需要四个变量：AGENT_API_KEY、AGENT_BASE_URL、JUDGE_API_KEY、JUDGE_BASE_URL。
沿用团队已经使用的 OpenRouter 账号时，两个 BASE_URL 均为 `https://openrouter.ai/api/v1`。
不要把真实 key 写入聊天、脚本或 Git。

```bash
uv sync --frozen
# 只有尚未安装上游及三阶段 MCP 环境时才需要这一步；会下载较大的归档。
uv run pe6203 bootstrap --scope all

uv run --env-file .env python scripts/evaluate_v2.py check
uv run --env-file .env python scripts/evaluate_v2.py prepare --output results/raw/v2-eval-20261101
uv run --env-file .env python scripts/evaluate_v2.py run --output results/raw/v2-eval-20261101
```

prepare 冻结目录、任务与源码，不调用模型；run 调用 updater、agent、judge，会产生费用。
使用新目录，不恢复旧 V1 实验。新增套件按固定一次重复运行，不采用原 CLI 的默认三次。
如果队友已经开始这批，先对接目录，避免再次运行 27 条。

原运行器遇到连续连接故障会暂停。解决连接问题后：

```bash
uv run --env-file .env python scripts/evaluate_v2.py run --output results/raw/v2-eval-20261101 --resume
```

resume 保留已有失败/低分执行，按既有协议仅恢复可恢复的评分槽或未启动单元。
源码变化需要新实验，不将两次不同 strategy 混为一次结果。

## 交给 report 组的内容

```bash
# 仅重新解析已有记录，不调用模型
python scripts/evaluate_v2.py report --output results/raw/v2-eval-20261101
```

输出目录中的：

| 路径 | 内容 |
|---|---|
| `v2-eval/runs.csv` | 原题一致性、完成状态、TF、PE、调用/错误数、产物索引 |
| `v2-eval/summary.json` | 各方法完成率、已评分数量、共同完整单元比较、ECS、分阶段成本 |
| `v2-eval/cases/*.json` | 每条原题、完整最终答案、工具返回、工作目录文件 hash、失败信息 |
| `v2-eval/README.md` | 快速结果表，明确 complete/incomplete |
| `analysis/` | 原项目评估模块的 recovery/retention、配对结果和完整评估记录 |
| `plan.json`、`plan.sha256`、`experiment.json`、`catalogs/`、`cells/`、`preflight/` | 可追溯原始证据，必须一起保留 |

完成率以每方法计划的 9 条为分母；同时报告 started 和 scored。TF/PE 缺失保持 null，不填 0。
有评分但截断仍计执行未完成；正常结束不等于产物正确，案例的人工核验状态初始为 not_manually_reviewed。
报告解析五个原始 judge 评分并核对聚合。评分不完整时另列已评分均值和共同完整单元均值，避免不同分母直接排名。
成本分 update/agent/judge；API 预检单列。已知部分和完整费用分开，未知费用保持 null。
task 235 的 chart specification 是工具产物，不等于已经上线的网页。

真实运行结束后，将完整运行目录归档放到共享文件夹，并将整理结果与证据索引提交本分支。
当前提交仅包含准备和离线验收，不能用来填写 V2 的 TF、PE、完成率或声称评估已完成。

## 离线检查

```bash
uv run pytest -q tests/test_hybrid_selective.py tests/test_v2_eval_handoff.py
```

合计 41 项通过：31 项原 QI-V2 测试、10 项新评估检查。真实模型响应回放仍是离线测试，不计新执行。

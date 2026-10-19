# PE6203 Tool Harness Adaptation under Environment Change

**Project 4 · MCPEvol-Bench · Group A environment and runner handoff**

Compare No Update, Full Rewrite, and Selective Patch when MCP tools evolve, with the same model, decoding settings, tasks, and judge. The repository keeps its existing GitHub name; Project 4 supersedes the initial Project 2 scaffold.

当前 `baselines/xiaohua-integration` 已接入可读 CLI：task 139、Middle、No Update + LLM Full Rewrite，三个角色使用同一 DeepSeek Flash。配置好的本机 `.env` 通过下面命令加载：

```bash
uv run --env-file .env python -m integration.test_real_baselines --version middle --allow-metadata-api
uv run pe6203 report results/raw/<上面输出的运行目录> --details
```

运行后显示摘要并保存 `report.txt`；`--details` 展开逐次评分、工具调用和最终回答。`report` 只读日志，不调用模型；`--format json` 保留机器格式。每次真实运行使用新目录，所有失败保留。

本轮已跑结果：`uv run pe6203 report results/raw/xiaohua-cli-middle-20261019`。可共享证据：[No Update](results/evidence/xiaohua-cli-middle-20261019/no_update.json)、[Full Rewrite](results/evidence/xiaohua-cli-middle-20261019/full_rewrite.json)、[核查记录](results/evidence/xiaohua-cli-middle-20261019/verification.json)。

## 团队入口 Team execution plan

**先读 [一页执行设定](docs/plan/README.md)**：两类业务场景；目标 4 个开发任务 + 8 个正式任务；3 阶段 × 3 策略；2 周交付，第三周补重复与复现。任务数量是团队预算选择，正式集合尚未冻结。

| 读者 | 从这里开始 | 交接产物 |
| --- | --- | --- |
| A 环境与 runner | [排期与验收](docs/plan/workplan.md)、[接口](docs/plan/interfaces.md) | 真实链路、任务环境、日志与批次记录 |
| B 基线 / C 局部更新 | [方法设定](docs/plan/project-spec.md)、[接口](docs/plan/interfaces.md) | knowledge、patch、validation、更新成本 |
| D 评测与报告 | [实验协议](docs/plan/evaluation-protocol.md)、[报告模板](reports/templates/README.md) | 冻结任务、配对指标、失败分析 |
| Coding agent | [AGENTS.md](AGENTS.md)、[结构化计划](experiments/README.md) | 按依赖执行 backlog，以证据验收 |

计划文件可供协作；它们不代表正式实验已经完成。来源及课程要求与团队选择的区别见 [来源表](docs/plan/sources.md)。

## Current status

本分支已经验证真实 DeepSeek → MCP → judge 的开发闭环：task 139 / Middle / seed 0，No Update TF 8.2、PE 7.0；LLM Full Rewrite TF 9.0、PE 7.2，各有 5 次有效评分。两组 agent 均触及 12 轮上限，Full Rewrite 有一次缺少 projectId 的工具错误。它们是可追溯的开发结果，不是完整 benchmark 或策略优越性的证明；ECS、USD 仍未获得。

| Group A deliverable | Status |
| --- | --- |
| Upstream source, commit, server releases, dependencies | Pinned and checked |
| Python and Node environment | Installed and exercised on macOS arm64 |
| Stage switching and judge/metric entry points | Documented, including release discrepancies |
| Real MCP calls and persistent state across restart | Verified on all three stages |
| Runner, metadata, trace and result interfaces | Implemented with tests and examples |
| Real model agent and model judge | Verified on task 139 / Middle; judge complete, agent max_rounds |

Read [Group A handoff](docs/group-a-handoff.md), [environment audit](docs/environment.md), and [project requirements](docs/project-brief.md).

当前本地验证：**89 tests passed**，lint/format 通过，另有上述真实模型记录。历史环境验证为独立 clean checkout 的 22 项测试，[证据](results/evidence/clean-checkout.json)保留当时版本。GitHub Actions 不下载大型服务快照，相关测试可能 skip；fake model 测试只证明程序接线。

## Reproduce the environment

Prerequisites: Git, [uv](https://docs.astral.sh/uv/), and npm. Run from the repository root.

```bash
git clone https://github.com/FAN0020/pe6203-agent-harness-safety.git
cd pe6203-agent-harness-safety
uv sync --frozen
npm install --prefix .cache/node-runtime --no-save --package-lock=false node@24.13.0
export MCPEVOL_NODE="$PWD/.cache/node-runtime/node_modules/node/bin/node"
uv run pe6203 bootstrap
uv run pe6203 doctor
uv run pytest -q
```

The first bootstrap downloads approximately **3.40 GB** of release ZIPs and verifies their SHA256 digests. It extracts the two smoke servers and their bundled dependency closures without resolving current npm versions. Runtime files stay under ignored `.cache/`. Docker and 1mcp are not required by this adapter; its MCP SDK connects directly to the released servers over stdio.

```bash
uv run pe6203 probe --version early --output results/raw/probe-early
uv run pe6203 probe --version middle --output results/raw/probe-middle
uv run pe6203 probe --version late --output results/raw/probe-late
uv run pe6203 metadata --version late --output results/raw/late-metadata.json
```

Each probe creates local project/task and knowledge-graph data, restarts both services, then reads it back. Use a new output directory for each run; existing runs are never overwritten.

## Run the real model pipeline

Set the four variables in [.env.example](.env.example). Credentials are never embedded in configs or inherited by MCP servers. `.env` is not automatically loaded. Configure models in a copy of [configs/smoke.json](configs/smoke.json); `gpt-4o` is an upstream example, not confirmed account access. The paper reports DeepSeek-Chat as judge while the released evaluator defaults to `gpt-4o`; select and freeze one protocol before comparing strategies.

```bash
cp configs/smoke.json configs/local.json
# Edit configs/local.json and export the API variables in your shell.
uv run pe6203 run --task-id 139 --version early \
  --strategy current_metadata_smoke --seed 0 \
  --config configs/local.json \
  --knowledge examples/knowledge/early-task139.json \
  --output results/raw/task139-early-seed0
```

For Middle/Late smoke runs, change `--version` and use the matching `examples/knowledge/<version>-task139.json`. These are current-metadata smoke runs, not implementations of the team's adaptation strategies.

For No Update on an evolved server, supply Early knowledge and `--strategy no_update`. For Full Rewrite or Selective Patch, B/C supply the knowledge generated by their method. A strategy label records the source of knowledge; it does not implement that method.

Interface: `run(task_id, version, strategy, seed, config) → (raw_trace, benchmark_result)`. The validated scope is official task **139** and two local servers. New task/server definitions must be reviewed before expansion; unsupported tasks are rejected rather than replaced with mocks.

## Files for teammates

- `src/pe6203/`: bootstrap, task loading, MCP transport, model runner, judge bridge, CLI.
- `configs/benchmark.lock.json`, `uv.lock`: immutable upstream and dependency pins.
- `examples/metadata/`: complete real catalogs for Early/Middle/Late.
- `examples/knowledge/`: four task-139 tools selected from each catalog.
- `schemas/`: ToolRecord and result JSON contracts.
- `results/evidence/`: reviewed real transport evidence and environment report.
- `tests/`: leakage, routing, score validation, round-limit, persistence, and output checks.

完整 benchmark、Selective Patch 和正式分析仍待完成。旧计划与 Group A handoff 记录初始交接状态；本分支当前运行入口和验证状态以上述 baseline 说明与证据为准。

## Primary sources

Based on the [MCPEvol-Bench public source release](https://github.com/Octobrist/MCPEvol-Bench/tree/888c779a0fe735f612ca62bdd1fdd7c9e6bf8701), its [server dataset](https://huggingface.co/datasets/anonymous2233/evol-servers/tree/162e3ffbea1717ac8a20fe9b26465e29117229e4), and [Liu et al., arXiv:2607.14642v1](https://arxiv.org/abs/2607.14642v1). The paper is a preprint; no journal peer-review status is claimed. See the source audit for differences between paper and code.

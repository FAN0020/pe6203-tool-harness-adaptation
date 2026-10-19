# PE6203 Tool Harness Adaptation under Environment Change

**Project 4 · MCPEvol-Bench · Group A environment and runner**

比较 No Update、Full Rewrite、Selective Patch 在工具变化后的表现，固定模型、任务、judge 与执行环境。课程要求以 [Project 4 brief](docs/project-brief.md) 为准。

## 当前交付 / Status

**201 个官方任务已完成全量环境审计；真实 LLM agent → MCP → judge 尚未验收。** 需要明确的 API base URL 与 agent/judge model IDs。现有真实工具日志和 fake-model 协议测试都不算模型 benchmark 分数。

| 已验证内容 | 范围 | 入口 |
| --- | --- | --- |
| 来源与安装 | 锁定 commit/revision、三阶段完整 Node 发布包、Python/Node dependencies | [环境与官方评分入口](docs/environment.md) |
| 全量 inventory | 201 tasks，128 个任务 server names；163 个任务所需 Node 入口齐备 | [全量交接与缺口](docs/full-benchmark.md) |
| MCP catalogs | 8 reviewed services × 3 stages，24/24 启动与目录检查 | [完整 catalogs](examples/catalogs/README.md) |
| 实际工具执行 | 原两服务三阶段持久化通过；新增六服务 17/18 检查通过 | [证据](results/evidence/full-benchmark/README.md)；Late thinking 有上游错误 |
| Runner | 任意 selected task ID + reviewed profiles、隔离工作目录、fixture hashes、完整知识输入 | [A/B/C/D 交接](docs/group-a-handoff.md) |
| Batch | 显式运行计划、ledger、恢复、哈希检查；保留低分与失败 | [三阶段开发样例](configs/batch-task139.example.json) |

当前 profile 覆盖任务 **103、105、139、283、393** 的固定服务器集合；只有 139 已完成空状态 development smoke 审查，其它 fixture 尚未全部核定。其余任务的缺口逐项记录；不能将完整发布包安装等同于全部服务运行成功。

## 团队入口

| 读者 | 内容 |
| --- | --- |
| 全组 | [一页执行设定](docs/plan/README.md)：2–3 周；目标 4 development + 8 evaluation，正式集合尚未冻结 |
| A | [全量 benchmark 交接](docs/full-benchmark.md)、[环境安装](docs/environment.md) |
| B/C | [完整 metadata](examples/catalogs/README.md)、[方法设定](docs/plan/project-spec.md)、[接口](docs/plan/interfaces.md) |
| D | [实验协议](docs/plan/evaluation-protocol.md)、[readiness](results/evidence/full-benchmark/task-readiness.json)、[报告模板](reports/templates/README.md) |
| Coding agent | [AGENTS.md](AGENTS.md)、[结构化计划](experiments/README.md)、[backlog](experiments/backlog.json) |

## 安装与真实 MCP 验证

需要 Git、[uv](https://docs.astral.sh/uv/) 和 npm；仓库根目录运行：

```bash
git clone https://github.com/FAN0020/pe6203-tool-harness-adaptation.git
cd pe6203-tool-harness-adaptation
uv sync --frozen
npm install --prefix .cache/node-runtime --no-save --package-lock=false node@24.13.0
export MCPEVOL_NODE="$PWD/.cache/node-runtime/node_modules/node/bin/node"
uv run pe6203 bootstrap --scope all
uv run pe6203 doctor
uv run pe6203 inventory --output results/raw/inventory.json
uv run pe6203 probe-servers --output results/raw/catalog-check
uv run pytest -q
```

ZIP 下载约 3.40 GB，完整展开约 12 GB；先校验 SHA256，直接运行发布包，不重新解析最新 npm 依赖。仅复现原两服务 smoke 可用 `bootstrap --scope smoke`。Docker/1mcp 不是此 native-stdio adapter 的依赖；未声称完成容器验证。

```bash
uv run pe6203 probe --version early --output results/raw/probe-early
uv run pe6203 probe --version middle --output results/raw/probe-middle
uv run pe6203 probe --version late --output results/raw/probe-late
uv run python scripts/probe_reviewed_services.py --output results/raw/functional-check
```

每次输出目录必须是新的。最后一条当前保留 Late `sequentialthinking` 的官方运行错误，退出 2；其它 17 项检查通过。详见 [证据与复现边界](results/evidence/full-benchmark/README.md)。

## 真实模型运行

将 [full-catalog config](configs/full-catalog-smoke.json) 复制到 ignored 的 `configs/local.json`，填写两个实际 model IDs，并 export [.env.example](.env.example) 中四个变量；`.env` 不会自动载入。不能凭现有 key 的变量名猜测 provider。MCP 子进程不继承模型 key。

```bash
cp configs/full-catalog-smoke.json configs/local.json
# Edit agent.model / judge.model; export explicit endpoint/key variables.
uv run pe6203 run --task-id 139 --version early \
  --strategy current_metadata_smoke --seed 0 \
  --config configs/local.json \
  --knowledge examples/catalogs/task139/early.json \
  --output results/raw/task139-early-seed0

uv run pe6203 batch --plan configs/batch-task139.example.json \
  --output results/raw/task139-three-stages
# Resume only the identical plan/config/artifacts:
uv run pe6203 batch --plan configs/batch-task139.example.json \
  --output results/raw/task139-three-stages --resume
```

完整 task139 catalogs 分别有 40/40/44 tools；旧四工具样例只用于历史 smoke。No Update 在 Middle/Late 仍提供 Early knowledge。Full Rewrite / Selective Patch 要由 B/C 交更新后的 knowledge；strategy 标签本身不实现算法。

接口保持 `run(task_id, version, strategy, seed, config) → (raw_trace, benchmark_result)`。真模型验收需实际 tool call、最终回答和五次有效官方 judge 结果；blocked / incomplete 分数保持 `null`，不填 0。ECS 需三阶段配对后计算。

## 验证与来源

本次本地检查与独立 checkout 结果见[验证回执](results/evidence/full-benchmark/README.md)。CI 运行 lint 与不依赖发布包的测试；bootstrap 后的本地测试包含真实 MCP。Fake model HTTP fixture 只验证协议接线。

以 [官方代码固定 commit](https://github.com/Octobrist/MCPEvol-Bench/tree/888c779a0fe735f612ca62bdd1fdd7c9e6bf8701)、[服务器数据固定 revision](https://huggingface.co/datasets/anonymous2233/evol-servers/tree/162e3ffbea1717ac8a20fe9b26465e29117229e4) 和 [Liu et al., arXiv:2607.14642v1](https://arxiv.org/abs/2607.14642v1) 为依据。论文是 preprint，不声称已通过期刊同行评审；发布代码与论文的差异见[来源审计](docs/environment.md)。

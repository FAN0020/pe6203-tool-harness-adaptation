# Group A：全量 benchmark 环境交接

**2026-10-19｜201 个官方选中任务全部审计；真实 LLM 评测尚未运行。** 这里的“全量”指任务与发布环境的覆盖审计，不能写成“完成 201 个任务测评”。正式实验仍按[团队协议](plan/evaluation-protocol.md)选取与冻结子集。

## 五项交付与证据

| A 的责任 | 已完成 | 还缺什么 | 证据 / 入口 |
| --- | --- | --- | --- |
| 1. 官方来源与依赖 | commit、dataset revision、三个 ZIP SHA256、201 tasks / 174 server names 清点 | 外部服务账户及未发布配置不能凭空补齐 | [来源与 judge 入口](environment.md)、[全量 inventory](../results/evidence/benchmark-inventory.json) |
| 2. 环境安装 | Python 3.12.12、Node 24.13.0；完整三阶段 Node 发布包及 bundled dependencies | 13 个非 Node 配置；外部服务；容器未验收 | [安装回执](../results/evidence/full-benchmark/installation.json)、[runtime](../results/evidence/full-benchmark/runtime.json) |
| 3. 切换与评分 | Early=original，Middle=iter3，Late=iter5；官方 rubric、TF/PE、两种 ECS 口径 | 冻结实际 agent/judge 服务 | [environment](environment.md)、`src/pe6203/judge.py` |
| 4. 最小真实任务 | 真实 MCP 三阶段读写与重启；新增服务 functional probes 17/18 通过 | **真实 agent → MCP → 五次有效 judge**，当前 0 次 | [旧两服务持久化](../results/evidence/README.md)、[新服务调用日志](../results/evidence/full-benchmark/functional-probes.json) |
| 5. Runner 与交接 | 通用任务入口、8 reviewed profiles、15 完整 task catalogs、fixture copy/hash、batch/resume、trace/result | 未审查服务不能直接执行；B/C 方法仍由对应组实现 | [接口](group-a-handoff.md)、[catalogs](../examples/catalogs/README.md)、[batch 样例](../configs/batch-task139.example.json) |

## 全量审计：数字分别说明什么

| Population / check | 结果 | 正确解释 |
| --- | ---: | --- |
| `chosen_idx.json` 官方选择 | 201 tasks | 不是原始候选文件的 393 条，也不是 ID 0–200 |
| 选中任务引用的 server names | 128 | 按任务里的精确字符串计数 |
| 每阶段 `mcp.json` | 167 names | 三阶段相同数量；不等于均可运行 |
| 配置与任务名并集 | 174 names | 全量 inventory 的 server 行数 |
| `status_dict.json` | 163 servers / 1,685 tools | 发布索引统计；与论文 123 / 1,272 不是同一清点范围，不混用 |
| 所需 Node 入口都在 ZIP 的任务 | 163 / 201，各阶段相同 | **静态文件齐备，不代表启动或任务成功** |
| 三阶段 entry 状态（每阶段） | 149 available；1 ambiguous bin；1 missing entry；3 missing package；13 non-Node；7 missing config | 以 inventory 明细为准；不拉取最新版来替换缺失快照 |
| 审查后启用的服务 | 8 | 其余环境仍需逐个检查凭据、路径与外部副作用 |
| 真实 initialize + tools/list | 24 / 24 | 8 servers × 3 stages |
| 新增 6 服务的真实 functional probes | 17 / 18 | Late thinking 有发布包错误；完整日志保留 |
| 固定 server set 均有 profile 的任务 | 103、105、139、283、393 | 仅表示启动配置覆盖，fixture 与业务正确性另行验收 |
| 完整模型任务评测 | **0** | 不提供虚构 TF / PE / ECS |

7 个缺少同名配置的任务 server：`fixparser-plugin-mcp`、`google-cloud/storage-mcp`、`mcp-sequential-thinking`、`mcp-server-time`、`pollinations/model-context-protocol`、`server-memory`、`server-sequential-thinking`。不能静默映射为相似名称；需要上游依据与显式实验变更。

[逐任务 readiness](../results/evidence/full-benchmark/task-readiness.json) 对全部 201 个任务记录 archive blocker、missing profile、fixture 状态与已知运行错误。Inventory 是可重复生成的静态事实，readiness 是本次检查后的交接快照。

## 当前服务与任务边界

| Reviewed service | Early / Middle / Late 工具数 | 运行检查与隔离 |
| --- | --- | --- |
| `@pimzino/agentic-tools-mcp` | 29 / 29 / 31 | 项目、任务创建与重启读取；workingDirectory 固定 |
| `@itseasy21/mcp-knowledge-graph` | 11 / 11 / 13 | 实体、关系、重启读取；独立 MEMORY_FILE_PATH |
| `@modelcontextprotocol/server-memory` | 9 / 9 / 10 | 实体写入、重启读取；独立 MEMORY_FILE_PATH |
| `@modelcontextprotocol/server-filesystem` | 14 / 14 / 13 | 写文件、重启读取；仅允许本次 workspace |
| `@modelcontextprotocol/server-sequential-thinking` | 1 / 2 / 3 | Early/Middle 调用通过；Late 失败 |
| `mcp-tasks` | 5 / 5 / 5 | setup、add、重启 search；source registry 留在 workspace |
| `mcp-calculator` | 101 / 101 / 103 | `add(2,5)` 返回 7 |
| `math-mcp` | 6 / 6 / 7 | `evaluate("2+5")` 返回 7 |

Late thinking 的 `dist/index.js:113` 调用 `thinkingServer.getThoughtHistory()`，同发布包 `dist/lib.js` 没有该方法，真实返回 `isError=true`。保留官方代码；这是工具执行错误，不是 model endpoint 故障，不自动重试或排除低分。103、283 以及其他使用该 server 的任务需记录影响；若另做修复版，只能作为独立诊断条件。

| Task | Fixture / state 审查 | 下一步 |
| --- | --- | --- |
| 139 | 要求新建项目与知识关系；空 workspace 适合 development smoke | 优先真实模型验收，固定为 development |
| 103 | 引用 requirements document，未定位其精确来源；Late thinking 有错误 | 确认 fixture，保留错误条件 |
| 105 | 官方有 `anotation_path/code/`；题目所指 `logs/` 尚未核定 | 不把其它日志擅自改名代替 |
| 283 | 有官方 CSV 输入，但题目相关初始数据尚未完整核对；Late thinking 有错误 | 逐项 review，不能直接标记 ready |
| 393 | 题目引用既有 Horizon 项目；其初始状态未证实 | 不编造 Horizon fixture |

模型仅获原始 task question 与方法指定的 knowledge；updater 只获 metadata。完整工具 catalog 不按题目“可能用到”提前裁剪。官方输入目录已单独复制并记录[逐文件 hashes](../fixtures/published-files.manifest.json)，详见 [fixtures](../fixtures/README.md)。

## 可复现命令

仓库根目录运行；每次使用新 output 目录。安装命令见 [README](../README.md)。首次下载约 3.40 GB，完整展开约 12 GB；Node 包路径计数包含依赖副本，不是服务数。

```bash
export MCPEVOL_NODE="$PWD/.cache/node-runtime/node_modules/node/bin/node"
uv run pe6203 bootstrap --scope all
uv run pe6203 inventory --output results/raw/inventory.json
uv run pe6203 probe-servers --output results/raw/catalog-check
uv run python scripts/probe_reviewed_services.py --output results/raw/functional-check
uv run pe6203 metadata --task-id 393 --version early --output results/raw/task393-early.json
```

`probe-servers` 只检查目录；functional script 实际调用工具，当前预期保留 Late thinking 的失败并退出 2。它们都不用 LLM；成功也不是 benchmark score。原先两服务的 `pe6203 probe --version ...` 继续可用。

```bash
cp configs/full-catalog-smoke.json configs/local.json
# 填写真实 agent.model / judge.model，并 export 四个 API 环境变量。
# 同一 provider 可用同一 key，但 base URL 必须由账户配置明确给出。
uv run pe6203 batch --plan configs/batch-task139.example.json --output results/raw/task139-model-pilot
uv run pe6203 batch --plan configs/batch-task139.example.json --output results/raw/task139-model-pilot --resume
```

该示例是 139 × 3 阶段的 current-metadata development pilot，默认每次五个 judge calls；不是三策略正式实验。若尚无凭据，runner 留下 blocked result 并退出 2。补好配置后使用新目录，不能将不同配置混入原 batch。

## Batch / resume 规则

| 项目 | 实现 |
| --- | --- |
| Cell identity | task ID × version × strategy × seed；重复 cell 在执行前拒绝 |
| Batch fingerprint | plan、config、runtime Python 源码、lock/profile、uv.lock、knowledge 文件与 fixture bytes、明确 endpoint；不含 key 值 |
| Artifact check | 每份已保存 result 的 bytes SHA256；改动则拒绝 resume |
| Interrupted process | 若 result 已落盘，恢复 ledger 不再调用模型；否则最多另建一次 attempt，保留旧目录 |
| 低分、blocked、judge incomplete | 原样保留，不靠 resume 自动重跑“改善结果”；诊断用新 experiment/output |
| 当前限制 | 单进程写一个 batch；尚未实现计划中的 HTTP 429/5xx 分类退避；未冻结 Node binary/完整环境 fingerprint；正式 A4 验收仍未关闭 |
| Cost | 保存 provider usage，缺失为 null；中断到 provider 返回前的费用需结合账户账单核对 |

## 真模型验收标准

需要明确的 `AGENT_BASE_URL`、`JUDGE_BASE_URL` 和两个可用 model IDs；keys 留在本机环境变量，不上传 Git/Drive。当前检测到的 key 变量名不能用于推断其供应商或 endpoint。

验收读取实际日志：有真实 model response → 至少一个真实 MCP call/result → 最终 answer → 五次有效官方 rubric 分数；`ANSWER/<id>.json`、`EVAL/<id>.json`、`result.json` 相符。之后才能报告完成 A 的最小真实任务；其他任务仍按 readiness 逐项推进。

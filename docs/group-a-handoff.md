# Group A handoff / 组员直接接入

**可用：全量任务审计、通用 runner、8 个 reviewed profiles、完整 catalogs、batch/resume、Sprint 1 确定性基线和 task 139 最小真实模型闭环。** 范围、fixture 缺口、上游 Late thinking 错误见[全量交接](full-benchmark.md)。

## 给 B/C：固定完整知识

| 输入 | 位置 / 规则 |
| --- | --- |
| 完整 server catalogs | [examples/catalogs/index.json](../examples/catalogs/index.json)，24 份真实 `tools/list`，附 hashes |
| 完整固定 server group | `examples/catalogs/task{103,105,139,283,393}/{early,middle,late}.json` |
| Development K0 | [task139/early.json](../examples/catalogs/task139/early.json)，40 tools；不是旧四工具 smoke |
| ToolRecord | [schema](../schemas/tool-record.schema.json)：`tool_id/server_id/version/name/parameters/description/usage_rules/output_schema/routing` |
| Updater 输入 | K0 + 目标 metadata + 固定配置；不读题目、参考答案、历史评分、mutation labels |
| Updater 输出 | knowledge、diff/patch、validation、update cost；见[接口](plan/interfaces.md) |

`tool_id=server_id::name`；重命名由 C 做有证据的匹配。No Update 保持 Early records 与路由，runtime 不自动刷新。官方没有 usage rules 则为 `[]`，没有 output schema 则为 `null`。

Runner 把 usage rules 与 output schema（若有）附加到模型可见 description。配置 `tool_name_policy=namespaced` 时，alias = 安全字符化 name 前 50 字符 + `__` + SHA256(`server_id::name`) 前 12 位；最长 64 字符，跨服务器/长名称保持稳定，碰撞时拒绝执行。真实 MCP 路由仍来自 frozen knowledge，保存在 result；所有策略必须统一 policy。原 `native_unique` 保持兼容并拒绝重名。

## 给 A：Runner / batch

```python
import json
from pe6203.runner import run

config = json.load(open("configs/local.json"))
config.update(root="/absolute/path/to/checkout",
              knowledge_path="examples/catalogs/task139/early.json",
              output_dir="/absolute/path/to/a/new/run")
raw_trace, result = run(139, "late", "no_update", 0, config)
```

任意官方 selected ID 都经过原题加载；只有其完整 server set 在 [profiles](../configs/server-profiles.json) 中才允许运行。当前五个 task IDs 具有配置覆盖，不能据此跳过 fixture review。可选 `fixture_dir` 复制固定输入并保存 hash，拒绝 symlink。所有调用使用独立 workspace/private HOME；这是 application-level containment，不是 OS sandbox。

单传策略标签不触发更新。Sprint 1 的 No Update / deterministic Full Rewrite 可先用 `pe6203 adapt` 生成产物，再交 `run --adaptation` 校验、执行和记录成本；见 [baseline smoke](baseline-smoke.md)。正式 LLM updater 仍待 B/C 实现。模板 [batch-task139.example.json](../configs/batch-task139.example.json) 可由 `pe6203 batch --plan ... --output ...` 执行，字段为 `experiment_id/config_path/runs`，cell 为 `task_id/version/strategy/seed/knowledge_path`，可附 `fixture_dir/update_cost`。Batch 继续按显式 knowledge/cost 接口接收每个 cell 的产物。详情和恢复限制见[batch 规则](full-benchmark.md#batch--resume-规则)。

| Artifact | 内容 |
| --- | --- |
| `knowledge.json` | 模型实际使用的 frozen metadata |
| `environment-metadata.json` | 当前环境 metadata，仅审计/judge |
| `fixture-manifest.json` | 指定 fixture 时的文件 hashes 与 manifest digest |
| `events.jsonl` | 即时保存 model response、tool call/result、judge response |
| `ANSWER/<task_id>.json` | 官方兼容 task / answer / trajectory |
| `EVAL/<task_id>.json` | 官方兼容 `eval_result.runs/aggregate` |
| `judge-prompt-N.txt` | 实际评分输入 |
| `raw_trace.json`、`result.json` | 原始轨迹、状态、nullable 分数、usage、配置/hash；blocked 也保存 |
| `mcp.stderr.log`、`workspace/` | 服务日志与独立任务状态 |
| `batch.json` | cell identity、attempt paths、结果 hashes、状态；低分和失败保留 |

退出码：完整评分 0，blocked/timeout/incomplete 2。`execution_status` 与 `judge_status` 区分未启动和已尝试失败；不要仅看总 status。一次进程只写一个 batch；不同配置/知识/代码用新目录。

## 给 D：分数与可信边界

| 内容 | 读取 / 判定 |
| --- | --- |
| TF / PE | `task_fulfillment_mean` / `planning_and_efficiency_mean` 的未取整 mean |
| 完整 judge | `successful_runs=5` 且 `complete=true`；partial mean 不冒充完整评分 |
| ECS | 三阶段同 task/strategy/model/config/repetition 配对；[公式差异](environment.md)；缺一阶段则缺该 triplet |
| Cost | `cost.agent/judge` 为 provider usage；B/C 提供 `cost.update`；未知为 null，USD 不猜价格 |
| Seed | 默认不发送 model seed；用于 judge 顺序，不能声称模型严格确定 |
| 模型验收 | 139 Early / No Update 已完成：5/5 judge，TF 9.8 / PE 8.6；[证据](../results/evidence/baseline-integration/verification.json)。其余 MCP probe / fake-model 测试仍无模型分数 |
| 正式实验 | [协议](plan/evaluation-protocol.md)尚未冻结；任务族/split、changed/unaffected、provider limits 和 B/C 产物仍需验证 |

完整 logs 默认留 ignored 的 `results/raw/`。可分享副本先检查秘密与用户数据，再放 `results/evidence/`；保留原始 hash 和路径替换规则。不要上传 keys 或 raw .env。

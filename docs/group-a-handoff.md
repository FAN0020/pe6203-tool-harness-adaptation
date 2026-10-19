# Group A handoff

后续协作：[团队执行设定](plan/README.md) · [A/B/C/D 接口](plan/interfaces.md) · [两周排期](plan/workplan.md)。本文件记录现有实现；新计划中的扩展需分别验收。

## 当前可交接内容

已完成环境安装、官方源及快照锁定、三版本真实 MCP 启动与持久化检查、元数据导出、runner 和结果接口。**真实 LLM agent → MCP → LLM judge 验收尚未完成**：需要明确模型 API 地址、凭据变量和模型名称。Transport probe 不调用 LLM、不产生 benchmark 分数。

## B/C 接入

`examples/metadata/{early,middle,late}.json` 来自真实服务器 `tools/list`。`examples/knowledge/*-task139.json` 是按官方 task 139 所需工具选出的四条记录，不是 Full Rewrite 或 Selective Patch 算法结果。

ToolRecord 字段为 `tool_id/server_id/version/name/parameters/description/usage_rules/routing`，另保留 `output_schema`。`tool_id=server_id::name`；重命名不会自动维持旧 ID，匹配由 C 的 diff 层处理。官方没有独立 usage-rules 字段时使用空数组，不凭空推断。见 [JSON schema](../schemas/tool-record.schema.json)。

继续使用团队的 `adapt(old_knowledge, new_metadata, strategy, context) → new_knowledge, diff_log, update_cost`。把 `new_knowledge` 写成样例 envelope（`schema_version/benchmark_commit/version/tools`），将路径传给 runner。更新成本写入配置 `update_cost`，单位 tokens/seconds/USD，未测量为 `null`。

No Update 在 Middle/Late 仍传 Early knowledge。执行循环只把 supplied frozen tools 发给模型。当前元数据仅供审计和 judge，不替换模型 schema，不自动修复名称和参数。工具返回的正常错误信息仍会进入 agent 轨迹；保持该反馈规则一致。

`routing` 必须指向固定 task 的服务器，模型侧名字不能重复。当前支持 task 139；新 task/server 要先扩充受审查的 manifest。C 可在方法生成的 knowledge 中加入选择的新工具，不能直接把所有新工具暴露给 No Update。

## Runner

```python
import json
from pe6203.runner import run

config = json.load(open("configs/local.json"))
config.update(root="/absolute/path/to/checkout",
              knowledge_path="examples/knowledge/early-task139.json",
              output_dir="/absolute/path/to/a/new/run/directory")
raw_trace, benchmark_result = run(139, "late", "no_update", 0, config)
```

策略名称只记录 knowledge 来自哪种方法，runner 不代写 B/C 算法。`current_metadata_smoke` 专供环境检查，不是正式 baseline。

| 产物 | 内容 |
| --- | --- |
| `knowledge.json` | 模型实际使用的 frozen metadata |
| `environment-metadata.json` | 当前环境元数据，供审计/judge |
| `events.jsonl` | 即时保存的 agent response、工具调用/返回、judge response；故障前事件也保留 |
| `ANSWER/139.json` | 官方兼容 question/answer/trajectory envelope |
| `EVAL/139.json` | 官方兼容 `eval_result.runs/aggregate` |
| `judge-prompt-N.txt` | 实际评分输入 |
| `raw_trace.json` | 完整轨迹及事件，阻塞时也保存 |
| `result.json` | 状态、nullable 分数、tokens、时间、配置与哈希 |
| `mcp.stderr.log`、`workspace/` | 服务日志和任务生成状态 |

输出目录必须不存在，避免混入旧状态。CLI 评分完成返回 0，blocked/timeout/incomplete 返回 2。批量调度和断点续跑属于后续集成工作，当前未实现。

`execution_status` / `judge_status` 区分 `not_started` 与 `failed`：例如模型服务不可用会留下执行失败和已有事件，不会被误记为没有尝试。

## D 的评分接口

使用真实 ID 139，不是候选数组下标。读取 `EVAL` 的未取整 mean，核对 `successful_runs/complete`。缺失不记为 0，`judge_incomplete` 不当作完整评估。单版本没有 ECS；三版本配对后再算，注明总体/样本标准差口径。

`cost.agent` 和 `cost.judge` 分别记录 provider 返回的 token usage；未返回则为 `null`。`cost.update` 由 B/C 提供。没有核定供应商价格时不估造 USD。种子控制 judge 顺序；默认 `send_model_seed=false`，不声称模型严格确定。若服务支持 seed，统一启用并保持策略间一致。

Smoke case 不替代正式 manifest。D/C 仍需核对任务 changed/unaffected 分类与三类变化覆盖；mutation 标注必须结合真实 metadata 和轨迹分析。

## 下一步验收

配置真实服务后执行 README 单任务命令。检查非 mock 的 agent response、真实 MCP 调用/输出、五次有效 judge 结果，以及 ANSWER/EVAL/result 一致性，保存实际配置和日志。完成后才能标记真实任务 pipeline 验收通过，再由 B/C 接入方法比较。

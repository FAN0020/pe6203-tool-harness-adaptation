# 交接接口与字段约定

**现有接口保持兼容；正式实验扩展在冻结前验收。** Runtime schema 以 [ToolRecord](../../schemas/tool-record.schema.json)、[result](../../schemas/result.schema.json) 为准；`experiments/templates/` 是计划记录模板，不是 runnable config；当前 batch CLI 使用 [configs 样例](../../configs/batch-task139.example.json)，其实现边界见[全量交接](../full-benchmark.md)。

## 输入输出

| 交接 | 输入 | 输出 | 规则 |
| --- | --- | --- | --- |
| A → B/C | K0、Middle / Late 完整 metadata、固定 server group | JSON envelope + hashes | updater 不拿任务题目、答案、评分或 mutation ground truth |
| B/C → A/D | `adapt(old_knowledge, new_metadata, strategy, context)` | knowledge、[adaptation record](../../experiments/templates/adaptation-record.json) | 记录 diff、依赖、校验、全部调用和成本；失败可审计 |
| A → D | `run(task_id, version, strategy, seed, config)` | raw trace、result、[run record](../../experiments/templates/run-record.json) | `version` 映射 ledger 的 `stage`；保留独立 attempt |
| A/D → 全组 | [task review](../../experiments/templates/task-review.json)、[freeze record](../../experiments/templates/freeze-record.json) | 固定任务、配置、来源、fixture 和 hashes | 只有所有必要项有证据后才能 frozen |

## Knowledge

| 字段 | 语义 / 校验 |
| --- | --- |
| envelope | 现有 `schema_version / benchmark_commit / version / tools`；正式 K0 覆盖固定服务器的全部工具 |
| `tool_id` | `server_id::name`；重命名后旧、新 ID 分别保留在 patch，不猜测等价关系 |
| `server_id` / `routing` | 真实服务器与 `tool_name`；只能路由到官方固定 server set |
| `name` | 模型可调用名称；必须唯一。跨服务器重名时 A 定义并冻结统一 alias 规则，不丢弃工具 |
| `parameters` | MCP `inputSchema`；保留 required、类型、枚举和约束 |
| `description` / `usage_rules` | 有 metadata 依据的说明与规则；没有规则时 `[]`，不凭空补业务事实 |
| `output_schema` | metadata 提供则保留，否则 `null`；不是参考答案 |
| record `version` | 该记录的知识来源阶段；Selective Patch 的未改记录保留原值 |
| envelope `version` | 方法产物目标阶段；No Update 继续保留 Early envelope |

未选中记录做 canonical JSON 相等检查，包括来源字段；不能为了统一 `version` 重写它们。新增/删除/重命名、描述或 schema 更新必须在 patch 中可定位。

## 当前缺口与验收

| 能力 | 当前状态 | 冻结前要求 / owner |
| --- | --- | --- |
| Task / server 范围 | 201-task inventory；8 profiles 覆盖五个 task server sets，fixture 未全验收 | A：按 manifest 扩展与验证，不能仅换 ID |
| 工具覆盖 | 已有 24 份完整 server catalogs、15 份完整 task catalogs；旧 smoke 仍是四工具 | A：生成正式完整 K0；B/C 基于同一 K0 |
| Agent 实际输入 | usage rules / output schema 已序列化；routing 与 alias 保存到 result | A：将 usage rules 和可用 output schema 显式序列化给 agent，记录输入；所有策略同一序列化器 |
| tool alias / context limits | 稳定 namespaced alias 已测试；provider 上限仍待真模型 pilot | A：开发集验证唯一映射、provider tool/context 上限；不静默截断 |
| 更新方法 | strategy 是标签，未实现 B/C 算法 | B/C：交真实更新产物、成本、校验和失败状态 |
| 批次恢复 | 已实现 fingerprint / result hash / batch resume；分类退避未实现 | A：增加 sidecar ledger，按身份及 hashes 判断恢复 |
| 接口演示 | transport probe 与 fake model 测试可用 | A：补真实 agent → MCP → judge 证据 |

## 运行状态与成本

| 内容 | 约定 |
| --- | --- |
| runner `status` | `evaluated / judge_incomplete / blocked / timeout`；`evaluated` 只表示评分完整，不表示任务成功 |
| 批次 `status` | `planned / running / complete / incomplete / blocked / failed`；单列 `runner_status`，不要混用 |
| 更新校验失败 | batch `failed`、failure category `adaptation_validation`；不启动 agent，分数 `null`，记录 updater 成本 |
| TF / PE | 官方 1–10 分，越高越好；缺失 `null`；ECS 由三阶段聚合，单次 run 不自产 ECS |
| 成本单位 | token 数、墙钟 seconds、USD；保留 prompt / completion / total tokens、调用次数及 provider usage |
| 价格 | provider / model / 查询日期 / 输入输出单价 / 缓存计价；未核定 USD 为 `null` |
| 更新成本归属 | `server_group × target_stage × strategy × repeat_id` 唯一产物计一次；不按任务复用次数重复相加 |
| 信息边界 | agent 读任务与该策略 knowledge；updater 只读 K0 与目标 metadata；D 的分层标签不进入二者输入 |

## 哈希与存放

| 记录 | 规则 |
| --- | --- |
| `*_file_sha256` / freeze 的 artifact hashes | 文件原始 bytes 的 SHA256；文件变动后重算 |
| fixture / knowledge 包含多文件时 | 先生成逐文件摘要 manifest，再对该 manifest 文件求 bytes hash；不将目录路径当摘要 |
| task `question_sha256` | 官方 question 字符串 UTF-8 bytes 的 SHA256，不改写、不标准化空白 |
| runner `config_sha256` 等现有摘要 | 保留当前 `benchmark.digest()` 的 JSON 序列化口径；不是文件 bytes hash，禁止混比 |
| canonical record 比较 | 解析后的 JSON 对象递归比较；对象键序不影响，数组顺序影响 |
| 原始证据 | `results/raw/<experiment_id>/<run_id>/`（ignored）；run ID 不含凭据 |
| 可分享证据 | 审查并脱敏后放 `results/evidence/<experiment_id>/`，报告链接到具体文件 |

不得将 token 缺失视作零、将传输验证当作模型结果，或靠日志文件名推断实验身份。结构化记录必须明确引用知识、更新产物与实际运行目录。

# DeepSeek baseline 接入验证

2026-10-27：通用 `pe6203 adapt` 已接入同一 LLM 重写实现，见
[通用入口说明](common-llm-baselines.md)。本文保留 task139 上游 agent 桥接 pilot 的运行方式；
它与通用 runner 的执行循环不同，不能将两种入口的分数混作同一 harness 的对比。

兼容团队目录重组：优先读取 examples/catalogs/task139/{stage}.json 与 configs/full-catalog-smoke.json，旧 checkout 回退到 examples/metadata/{stage}.json 与 configs/smoke.json。此 task-139 pilot 固定 native_unique 工具名称，保留已验证的上游循环路由规则；通用多任务仍使用 A 组 runner 的命名政策。

入口为 `integration/test_real_baselines.py`。仅开发任务 139，比较 Early 知识分别面对 Middle 或 Late 环境时的 No Update 和 Full Rewrite。`integration/baselines.py` 已从确定性复制更新为 LLM Full Rewrite：使用 deepseek-flash 对目标完整 catalog 中每个工具重新生成描述，包括未变化工具；名称、IDs、参数 schema、routing、output schema、来源版本及已有 usage rules 保留权威 metadata 原值。所有知识块完整重建。

## 执行方式

在仓库根目录先做免费检查：

```bash
uv run python -m integration.test_real_baselines --version middle --dry-run
```

它检查 metadata、agent 和路由，生成运行计划 summary；不生成 LLM knowledge、不调用模型、不产生 benchmark 分数。

真实运行需设置四个环境变量；以下地址仅用于 DeepSeek 官方账号。第三方服务必须使用实际服务地址和对应凭据。不要把密钥写入代码、提交 Git 或发到群里。

```bash
export AGENT_BASE_URL="https://api.deepseek.com"
export JUDGE_BASE_URL="$AGENT_BASE_URL"
read -s 'AGENT_API_KEY?请输入 DeepSeek API key（输入隐藏）: '
export AGENT_API_KEY
export JUDGE_API_KEY="$AGENT_API_KEY"
```

若使用 OpenRouter key，将两个地址改为 `https://openrouter.ai/api/v1`。入口会将三个角色的 `deepseek-flash` 自动映射为 `deepseek/deepseek-v4.1-flash-1017`，使用 OpenRouter 的 `reasoning.enabled=false` 参数。API key 必须由该平台签发。原先发给 DeepSeek 官方接口的 OpenRouter key 会报 401。费用以 OpenRouter 实际路由供应商的账单为准，不套用 DeepSeek 官方价格。

默认 updater、agent 和 judge 都是 `deepseek-flash`，non-thinking 模式、temperature 0，judge 按现有官方 rubric 调用 5 次。updater 每个目标版本一次完整 catalog 调用，max_tokens=16384。`--allow-metadata-api` 明确允许将公开工具 metadata 发送到配置的模型 API；只有手动运行时才会产生费用。若更换 judge，统一使用 `--judge-model` 并先确认服务可用性。

```bash
uv run --env-file .env python -m integration.test_real_baselines --version middle --allow-metadata-api
uv run --env-file .env python -m integration.test_real_baselines --version late --allow-metadata-api
```

只验证一种策略可加 `--strategy no_update` 或 `--strategy full_rewrite`。每次自动创建新目录，保留失败；不要挑最佳重跑当正式结果。检查脚本退出码，非完整评分返回 2。

默认显示 CLI 摘要，并保存总目录和每个 `execution/` 下的 `report.txt`。`uv run pe6203 report results/raw/<run>` 可离线重看整批结果；`--details` 展开评分/调用/回答，`--output NEW.txt` 保存，`--format json` 输出结构化数据。报告兼容上游桥接日志和更新成本 `tokens`，明确标出 `max_rounds`、缺失分数及更新失败。

## 代码复用与差异

从锁定的 upstream `SimpleOpenAIAgent.py` 中 AST 加载原样 ChatModel 类，实际调用其 `run_with_server`。绕过构造函数和自动重试，使用桥接的模型请求与 MCP 调用；不修改 upstream，不引入 FastChat 或上游 import 时的其他依赖。

保留上游工具调用循环、500 字符观测截断、FINISH 和无工具回答的结束规则。适配层使用现有 stdio 会话、冻结 routing、workspace 系统提示、统一请求上限、无自动重试和 DeepSeek `max_tokens` 参数。usage rules 和 output schema 也从冻结知识序列化到描述。以上是显式 harness 差异，不声称原样复现论文 leaderboard。

上游同步循环在线程执行；模型/MCP 请求转交主事件循环，不跨 loop 使用 MCP 会话。现有 runner 的 agent_loop 和客户端只在本 CLI 进程内临时替换，finally 恢复；不要在同一进程并发运行不同 runner。

不通过 live metadata 更新 No Update。两策略共用相同模型、judge、提示词、完整服务器 catalog 和路由规则；分别在新 workspace 中执行。Live metadata 仅供审计和 judge。工具正常返回的信息按同一反馈规则进入轨迹。

## 输出与验收

`results/raw/baseline-pilot-<timestamp>/summary.json` 汇总两策略状态。策略子目录中有 `knowledge.json`、`adaptation.json`、`config.json`；`execution/` 内有 `events.jsonl`、ANSWER、EVAL、result、raw_trace 与 MCP 日志。

`evaluated` 表示 judge 完整，不表示任务成功或知识更新正确。No Update 知识应等于 Early 完整 catalog；Full Rewrite 完整覆盖目标 catalog，描述由 LLM 重写，其余字段保持 metadata 原值。JSON/schema 验证不能证明语义等价，需要人工复核限制与参数含义。单阶段 ECS 为 null。updater/agent/judge token 分开取真实 provider usage，缺失保留 null，USD 未核定价格时为 null。

`update-audit.json` 保存 updater 实际提示、响应、调用设置、状态及成本，失败也保留；不包含 API key。输出截断、缺少工具、增加工具、结构字段修改或规则虚构会拒绝产物，summary 标记 adaptation_failed，不启动该策略 agent，不回退到确定性复制。

同一个模型担任 agent 与 judge 可以用于本次 pilot；二者使用独立请求、独立上下文和官方评分提示。报告注明模型和可能的评分偏差，代表性轨迹由人复核。本入口未运行真实模型前不能声明 baseline 效果已验证。

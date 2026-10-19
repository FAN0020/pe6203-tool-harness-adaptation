# Sprint 1 baseline integration and smoke test

Muchu Wu 的 Sprint 1 原型来自 `baselines/wu-muchu-sprint1`，原始提交 `24adbf5`。
实现现已迁入 [pe6203.baselines](../src/pe6203/baselines.py)，直接消费完整 ToolRecord catalog。
此处的 Full Rewrite 是 **deterministic full rebuild**，不调用 LLM；它不是
[团队正式设计](plan/project-spec.md)中的 LLM semantic rewrite。产物明确记录
`formal_llm_rewrite=false` 和 `cost.method`，不得用它证明正式三策略比较已经完成。

## 修复内容

- 原型的 `{name, metadata, text}` 包装与 runner 不兼容；改为保留完整 envelope 和 ToolRecord。
- 按 `server_id::name` 检查重复，允许不同 server 有同名工具，由统一 serializer 生成 alias。
- 校验 stage、benchmark pin、固定 server set、routing、参数 JSON Schema 和输出 schema。
- No Update 深复制 Early K0，不读取目标 metadata；成本为零。Early 的 Full Rewrite 也复用 K0。
- Middle/Late Full Rewrite 重建完整目标 catalog，包括未变工具；不伪装成语义重写。
- `adaptation.json` 保存来源文件 hashes、patch 和成本；runner 验证 strategy、stage、pin 和知识文件 hash。
- Agent/judge 配置的 `extra_body` 现在会传入 SDK 请求，测试检查实际 HTTP body 中的 provider 参数。
- 删除旧四工具知识、重复 metadata、旧 smoke config 和不可执行的 synthetic PASS dump。
  原始提交仍在 Git 历史；现有历史运行证据保留。所有当前测试使用完整 catalog。

## 最小离线 smoke

先按 [环境说明](../README.md) bootstrap，下面无需 API key：

```bash
uv run pytest -q tests/test_baselines.py tests/test_pipeline.py
```

单元测试覆盖 rename/add/remove/parameter/description/rules、输入隔离、来源校验和非法产物。
集成测试覆盖 139 × Early/Middle/Late × No Update/Full Rewrite，共 6 个组合：
真实 MCP 工具调用与持久化、完整 catalog、frozen Early knowledge、成本传递、ANSWER/EVAL。
另测 HTTP 503 保留 blocked/null。模型和 judge 是明确的 HTTP fixture；分数只是协议常量，
**不是真实模型表现，也不是 benchmark 得分**。未 bootstrap 时 integration tests 会 skip。

## 最小真实模型 smoke

使用 development task 139、单个策略、单阶段和一个 seed；judge 保持当前配置中的 5 次。
`.env` 中填写 endpoint 与对应 key，`configs/local.json` 中填写该服务实际支持的 model IDs。
不要凭 key 或 model 名猜 provider。`uv run --env-file .env` 显式载入本地凭据；它们不会传给 MCP。

```bash
export MCPEVOL_NODE="$PWD/.cache/node-runtime/node_modules/node/bin/node"
uv run pe6203 adapt --strategy no_update \
  --old-knowledge examples/catalogs/task139/early.json \
  --new-metadata examples/catalogs/task139/early.json \
  --output results/raw/my-smoke/early-no-update

uv run --env-file .env pe6203 run --task-id 139 --version early \
  --strategy no_update --seed 0 --config configs/local.json \
  --adaptation results/raw/my-smoke/early-no-update/adaptation.json \
  --output results/raw/my-smoke/real-early-no-update
```

每次使用新的输出目录，失败也保留。`--adaptation` 自动载入已校验的 knowledge 和更新成本；
不能与 `--knowledge` 同时传入。原有直接 `--knowledge` 接口保持兼容。

本机已验证的配置为 ignored 的 `configs/local.smoke-no-reasoning.json`，agent 与 judge 均为
OpenRouter 的 `deepseek/deepseek-v4.1-flash-1017`，endpoint 为 `https://openrouter.ai/api/v1`。
它基于原 `configs/local.json`，仅给 judge 增加以下字段；上面的命令改用此 config 即可复现。
原 local config 和 `.env` 保留，不提交密钥。

```json
"extra_body": {"reasoning": {"enabled": false}}
```

首次真实运行中，5 次 judge 均在 4096 completion-token 预算耗尽后返回空 content，
`finish_reason=length`。OpenRouter 文档说明推理和可见输出共享该预算，模型目录也确认
该模型默认推理开启且可关闭；参见[官方 reasoning 参数说明](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens)。
修复 runner 的参数转发后，用新配置、新目录完成一次开发诊断重跑。正式比较必须固定此设置；
这两次运行的 protocol hashes 不同，不将它们当作同协议重复或挑最高分。

要检查演化后的 deterministic Full Rewrite，可将 adapt 的 new-metadata 改为
`examples/catalogs/task139/late.json`，strategy 改为 `full_rewrite`，run 的 version 改为 `late`，
并使用全新的 adaptation/run 目录。No Update 在 Late 仍使用 Early K0。

真实验收需 model response、实际 MCP call/result、最终回答和 5 次有效 judge；
仅 `evaluated` 不代表任务成功。HTTP 401 是认证配置失败，TF/PE/ECS 必须保持 null。

## 当前验证证据

本轮结果见 [verification.json](../results/evidence/baseline-integration/verification.json)。

| 检查 | 实际结果 |
| --- | --- |
| 自动化 | Ruff / format 通过；68 tests passed，0 skipped，包含真实 MCP |
| 旧配置真实尝试 | Agent 完成，18 次 MCP 调用（1 次工具错误）；0/5 有效 judge，TF / PE / ECS 为 null；[保留记录](../results/evidence/baseline-integration/real-early-no-update.json) |
| 修复配置后的真实 smoke | 139 × Early × No Update × seed 0；23 次 MCP 调用，无工具错误；5/5 有效 judge；[完整审查证据](../results/evidence/baseline-integration/real-early-no-update-v2.json) |
| Judge 均值 | TF 9.8、PE 8.6、Grounding 9.6；单阶段 ECS 为 null |
| 实际持久化 | Ableton Analysis 项目、9 个任务、12 个实体、37 个关系；两类指定知识主题存在，关系端点均存在 |

原始文件留在 `results/raw/sprint1-integration-20261019/`，证据副本保存 hashes、配置、真实调用、
五次评分与持久化状态，只替换 checkout 绝对路径。模型回答把关系数写成 36，部分 judge 理由把
调用数写成 24；现场状态为 37、轨迹为 23，原样保留差异。评分是模型判断，不能代替状态检查。

认证在用户更新为 OpenRouter endpoint 后已恢复；此前 DeepSeek endpoint 的 401 不再是当前 blocker。
未执行完整 201 任务、正式三策略比较或 LLM updater；Selective Patch 不在本次修改范围。

# 通用入口的 LLM Full Rewrite

2026-10-27：团队选择 LLM Full Rewrite。通用 `pe6203 adapt` 保留
`src/pe6203/baselines.py` 的 ToolRecord envelope 和文件协议，内部调用
`integration/baselines.py` 的已有 LLM 实现。安装包包含 integration，以便安装后也能导入。
C 组的 Selective 独立分支未在此次修改中合并；尚不能据此宣称三策略正式实验已就绪。

## 行为与边界

- No Update 直接保留 Early 知识，不读取新版 metadata、不调用 updater，更新成本为零。
- Full Rewrite 在 Middle/Late 用完整目标目录执行一次 LLM 描述重写，包括未变化工具。
  参数、名称、tool_id、server_id、版本、路由、output_schema 和 usage_rules 均由目标
  metadata 保留。此实现重写的是描述，不让 LLM 发明或改写 usage_rules。
- Early Full Rewrite 继续复用相同 K0，不进行更新；这不代表 Middle/Late 使用确定性重建。
- 为支持不同 server 同名工具，传入 LLM 的临时 name 使用唯一 tool_id，并附上 native_name；
  保存时恢复原始名称，仅取回验证过的描述。不会更改执行时的实际工具名称和路由。
- updater 仅收到完整工具目录，不包含旧知识、task、答案、评分或演化标签。模型生成文字的
  语义是否忠实仍需人工复查；结构校验通过不代表语义正确。
- 失败不重试、不回退确定性重建；保存 adaptation.json 和 updater-audit.json，
  不产生可运行 knowledge.json。输出目录不可覆盖，重跑要使用新目录。

## 运行方式

以下示例以 task139 开发目录为例，不是正式冻结测试集。每次输出目录需要尚不存在。
先在本机配置环境变量 AGENT_API_KEY 和 AGENT_BASE_URL；OpenRouter 地址为
`https://openrouter.ai/api/v1`。凭据只保留在本机环境或 .env，不写入 JSON 配置。

```bash
uv run --env-file .env pe6203 adapt \
  --strategy full_rewrite \
  --old-knowledge examples/catalogs/task139/early.json \
  --new-metadata examples/catalogs/task139/middle.json \
  --updater-config configs/full-rewrite-updater.template.json \
  --allow-metadata-api \
  --output results/raw/full-rewrite-middle-update-01

uv run --env-file .env pe6203 run \
  --task-id 139 --version middle --strategy full_rewrite --seed 0 \
  --config configs/local.smoke-no-reasoning.json \
  --adaptation results/raw/full-rewrite-middle-update-01/adaptation.json \
  --output results/raw/full-rewrite-middle-run-01
```

模型配置路径需换成全组确认的 runner 配置；本机 local 配置可能不存在。
No Update 同样调用 adapt，但使用 `--strategy no_update`，无需 updater-config 或
allow-metadata-api；run 阶段选择相同策略并传入它对应的 adaptation.json。
run 不会替你执行 adapt；必须传入已经成功生成的 adaptation 文件。

Python 接口仍为 `adapt(old_knowledge, new_metadata, strategy, context=None)`。
Full Rewrite 的 context 仅采用 updater 设置和可选 audit_path；任务等其他 context 不发送。
updater 配置支持 model、temperature、max_tokens、timeout、api_key_env、base_url_env；
CLI 的 allow-metadata-api 是独立运行时开关，不能靠配置文件默认开启。

## 日志与成本

成功产物：knowledge.json、adaptation.json、updater-audit.json。
adaptation 标记 `formal_llm_rewrite=true` 表示采用 LLM 方法，不代表正式实验已验收。
公共成本映射如下，仅统计更新过程；执行和 judge 由 runner 分开统计。

| 原始 updater 字段 | 公共 artifact 字段 |
| --- | --- |
| model_calls | calls |
| input_tokens | prompt_tokens |
| output_tokens | completion_tokens |
| 输入+输出（两者已知时） | total_tokens |
| api_cost_usd | usd |
| elapsed_seconds | seconds |
| update_operations | update_operations |

provider 未返回的 token/USD 保留 null；失败调用已经返回的 usage 也会保留。
audit 记录请求、响应和非敏感模型设置，发布前仍应检查 metadata 是否允许分享。

## 测试

```bash
uv run pytest -q tests/test_common_llm_baseline.py tests/test_baselines.py tests/test_llm_full_rewrite.py
```

新增测试覆盖 CLI 配置透传、同名工具、完整目录与结构保留、失败不回退、失败成本和 audit、
缺失 usage 保留 null、没有授权不创建模型客户端、No Update 不触碰 LLM。
旧 baseline 测试同步改为明确模拟 updater；模拟分数和输出不得作为实验结果。

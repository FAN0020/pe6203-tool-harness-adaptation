# 项目 4 Baseline 本地接入记录

2026-10-27：通用入口也已接入 LLM Full Rewrite，当前使用方式见
[通用入口说明](common-llm-baselines.md)。以下为原接入过程的历史记录。

更新于 2026-10-19：Full Rewrite 已改为 deepseek-flash LLM 全目录重写，原文下面的确定性原型记录仅为历史。当前命令与行为以 [DeepSeek 接入说明](deepseek-baseline-pilot.md) 为准。pytest 使用显式 mock updater，不调用外部模型。旧 synthetic 日志入口和 knowledge 导出入口均需要 --allow-metadata-api，运行会产生更新费用。No Update 保持不变。LLM 描述不再要求与 metadata 逐字相等，工具覆盖与结构字段必须一致，未知成本保留 null。

队友的实现位于 `integration/baselines.py`。本次将其接入现有 wrapper，使用六组合成数据验证两种策略。A 组的 MCPEvol-Bench runner 尚未接入。

## 调用方式

```python
from integration.baselines import adapt, build_knowledge
from integration.baseline_wrapper import run_baseline_once

old_knowledge = build_knowledge(old_metadata)
record = run_baseline_once(
    adapt_fn=adapt,
    old_knowledge=old_knowledge,
    raw_new_metadata=new_metadata,
    strategy="full_rewrite",  # 或 no_update
)
```

metadata 包含 `tools` 列表；knowledge 的每个工具块包含 `name`、`metadata` 和 `text`。旧知识只根据旧 metadata 构建，两种策略从相同的旧知识开始。

## 运行验证

在项目根目录运行：

```bash
.venv/bin/python -m pytest tests -q
.venv/bin/python -m integration.run_baseline_validation
```

- `test_wrapper_smoke.py`：原有 fake_adapt 冒烟测试，12 项。
- `test_baseline_contract.py`：真实 adapt 接口测试，6 项。
- `test_baseline_integration.py`：六组数据乘两种真实策略，12 项；检查完整 metadata、知识文本、输入隔离和更新操作数。

日志输出到 `outputs/baseline_integration_validation.json`，记录输入、输出、更新日志、更新成本及 baseline 代码哈希。日志生成和行为验证是两个步骤；行为是否通过以 pytest 结果为准。outputs 已由仓库忽略规则排除。

## 等待对接的部分

C 组 fixtures 到位后对齐数据格式。A 组 adapter 到位后确认真实 metadata、旧知识注入和 runner 调用，执行 1–2 个真实任务，核查运行时新知识泄漏并保存 raw trace 和评分。

当前 Full Rewrite 是不调用 LLM 的完整确定性重建；最终知识表示及重建方式需全组确认。TF、PE、ECS 尚未评估，日志中记为 null。

## 导出 A 组 runner 所需 knowledge 文件

```bash
.venv/bin/python -m integration.export_baseline_knowledge --target-version middle
.venv/bin/python -m integration.export_baseline_knowledge --target-version late
```

每次输出到独立的 `outputs/knowledge/<时间>-<目标阶段>/`，拒绝覆盖已有目录。默认读取 `examples/metadata/early.json` 和目标阶段完整 metadata，覆盖当前已审查的两个服务器全部工具，不使用四工具 smoke 子集。Middle 和 Late 分别从 Early 更新。

导出器调用队友真实 adapt，将工具块中的 metadata 提取为直接 ToolRecord，并保留 envelope 的 schema_version、benchmark_commit、version 及来源字段。No Update 的 knowledge 与 Early metadata 解析后完全相同；Full Rewrite 原型与目标 metadata 完全相同。导出前检查必需字段、版本、固定服务器集合、名称唯一性及 routing。

每份产物包含：

- `knowledge.json`：A 组 runner 读取的文件。
- `adapt-output.json`：原始 new_knowledge、diff_log、update_cost。
- `runner-config-fragment.json`：knowledge_path 和 runner 的 tokens/seconds/usd 更新成本。
- `export-record.json`：输入输出代码及文件哈希、工具数量、阶段与原型状态。

导出根目录另存 `K0-early.json`。配置片段需合并到经全组确认的完整模型配置中；它本身不是完整可运行配置。No Update 在 runner 中更新成本计零，原始复制耗时留在日志；公共 K0 构造和文件序列化不计策略更新成本。

新团队计划要求正式 Full Rewrite 与 Selective Patch 共用 updater 模型、分块和解码设置。本次导出仅验证队友确定性重建原型的文件接入，产物标记 formal_method_ready=false。没有执行真实模型、MCP 或 judge，也没有修改正式协议或宣称 baseline 已正式验收。

# Full Rewrite 真实运行补充证据

本目录整理既有运行 `baseline-pilot-20261019T125817848890Z` 的证据。2026-10-27 做离线核对，没有重新调用模型或执行 benchmark。

## 文件

| 文件 | 内容 |
| --- | --- |
| `knowledge.json` | 原样保留的真实 LLM Full Rewrite 输出。与原执行目录中的知识文件字节一致，canonical digest 与保存的 result 一致。 |
| `update-audit.json` | 原样保留的 updater 设置、请求、响应、成本和结构验证记录。环境变量名不是密钥值。 |
| `target-metadata.json` | 从 `examples/catalogs/task139/middle.json` 复制。工具身份集合和每个实际发送字段均与 audit 请求一致；比较按 tool_id 配对，不要求数组顺序一致。 |
| `coverage-check.json` | 离线集合、字段、请求/输出一致性及来源哈希检查结果。 |

## QA-09 结论

**通过，范围限于该次真实运行的完整新版工具覆盖。**

- task139，Early K0 → Middle，Full Rewrite。
- 目标 catalog 和输出均为 40 个工具，无遗漏、无多余工具、无重复 tool_id。
- Early → Middle 未发现新增、删除或工具名称/身份变化；发现 2 个工具参数变化、1 个工具原始描述变化，具体 ID 见 `coverage-check.json`。
- 40 个工具描述经 LLM 重写；参数、routing、usage_rules 等非描述字段与目标 metadata 一致。
- Audit 中的模型响应描述与实际 knowledge 一致。

这一次没有真实发生新增/删除/重命名，不能据此宣称已覆盖这些真实变化。六类模拟变化可另参考团队已有 `tests/test_baseline_integration.py`。

## 运行与来源

- 官方 benchmark commit：`888c779a0fe735f612ca62bdd1fdd7c9e6bf8701`。
- 数据集 revision：`162e3ffbea1717ac8a20fe9b26465e29117229e4`。
- 既有公开摘要：[baseline-pilot-middle.json](../baseline-pilot-middle.json)。
- 原始执行目录：`results/raw/baseline-pilot-20261019T125817848890Z/full_rewrite/execution/`（本地忽略目录）。
- Early metadata：[固定提交的 Early catalog](https://github.com/FAN0020/pe6203-tool-harness-adaptation/blob/20f3a0c8c07135ac6308deeabf6b129ed225751a/examples/catalogs/task139/early.json)。来源文件哈希见检查记录。
- 本次上传包只复制目标 metadata、保留已有知识与 audit，并新增离线检查和说明；没有更改实验输出。

## 适用边界

这批证据与 `xiaohua-cli-middle-20261019` 是不同运行，不能混用。该次 Full Rewrite 的 TF/PE 为 8.4/7，执行状态为 `max_rounds`，judge 状态为 `complete`。judge 有评分不等于 agent 正常结束任务。

本检查不验收描述语义正确性（QA-12），不证明当前 main 已完成真实回归（QA-19），也不代替团队最终冻结。QA-10/11 可使用本目录作为补充材料，但需单独记录复核范围。

## 提交

提交本目录及 execution 子目录的全部交付文件即可，不需要强制添加整个 `results/raw`。当前整理后共19个文件。常见密钥字段及 token 格式扫描未发现命中；不应将 `.env` 或真实凭据加入提交。

## 执行与评分材料补充（2026-10-27）

本次新增 `config.json`、`adaptation.json` 与 `execution/`，对应同一个既有运行，原始目录未修改。新增 `consistency-check.json` 保存逐项核对结果、原始/交付文件 SHA-256 及路径脱敏记录。

### 文件结构

```text
full-rewrite-20261019/
  README.md
  knowledge.json
  target-metadata.json
  update-audit.json
  coverage-check.json
  consistency-check.json
  config.json
  adaptation.json
  execution/
    result.json
    raw_trace.json
    events.jsonl
    environment-metadata.json
    ANSWER/139.json
    EVAL/139.json
    judge-prompt-1.txt ... judge-prompt-5.txt
```

### QA-26

**通过，限本次历史 Full Rewrite 的日志完整性及一致性。** 已核对配置与原始摘要哈希、实际执行知识、适配输入输出、完整事件、ANSWER/EVAL 轨迹、12轮请求/响应、5份官方 judge prompt 及5次原始评分。TF=8.4、PE=7.0 与原始评分均值一致。28次工具调用没有工具错误，但 `max_rounds` 执行失败原样保留，不能写成正常结束任务。

### QA-25 的本次尝试核对

12次 agent、5次 judge、1次 updater 的逐次 usage 均完整。重新求和得到 agent 250812 tokens、judge 69653 tokens、updater 18831 tokens，与原始记录一致。该次尝试的调用/token账可验收；这不等于已核对整个项目、其他失败尝试或其他策略的费用。

原响应还保留了 provider `usage.cost`，各角色的观测加总另列在检查文件。历史结果中的未知美元成本保持 null，没有用新计算覆盖原始实验结果，也不据此宣布团队价格政策已冻结。

### 路径脱敏和哈希

新增交付文件将本机仓库绝对路径替换为 `<REPO>`，不修改模型文字或评分。原始文件不变，原始与交付字节哈希均列在 `consistency-check.json`。原 `config_sha256`、`protocol_sha256` 是运行时历史值，已在脱敏前核验；不能直接对路径替换后的配置重算并期待得到原值。

所有交付 JSON/JSONL 已解析并检查常见密钥字段与凭据格式，未发现命中。现有 knowledge、target metadata、updater audit 与 coverage 记录未改动。本次仍未提交或推送 GitHub。

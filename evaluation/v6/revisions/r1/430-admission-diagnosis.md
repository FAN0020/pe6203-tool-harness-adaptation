# V6-r1 / 430 Late：只读准入失败诊断

本次仅读取已冻结实验并在内存中重放确定性校验，没有调用 API、没有重跑 actor、没有修改源码、配置、原始响应、评分或当前实验。以下后续修复建议只能进入新的明确修订，不可追写为本轮成功。

## 已确认的直接原因

证据根目录：`results/raw/v6-r1-full-five-20261103/`。

核心证据：`adaptations/430/late/v6/updater-audit.json`，SHA256：`50bc3fcf4683d3ed378593accded34a8885960cdbb7d9d47832c68b0f40114eb`。

1. `attempts[0] / global_screen` 已通过，审查了六个 Swiftipedia 候选。此次不是覆盖缺失、重复候选或虚构证据 ID 造成的初始失败。
2. `attempts[1] / local_patch` 中六条补丁全部写了 `retain_rule_indices: [0]`，但该次请求 `selected` 中六个记录的 `rules` 全为 `[]`。每条记录的合法保留索引集合均为空，唯一合法保留数组是 `[]`。
3. `revision_errors[0]` 精确记录 **`Invalid retained rule indices`**。独立按同一目录、同一选定候选重建局部证据表，registry ID 集合与原请求完全一致；把原回复交给未改动的 `rules_v5.patches`，复现同一错误。
4. 最后一次 `attempts[2] / local_revision` 收到该错误后，没有修正保留索引，而是要求读取：

```json
{"tool_id":"swiftipedia-mcp-server::browse_module","side":"old","field":"usage_rules","pointer":"/selected/rules"}
```

`pointer` 应相对于指定工具字段的值求值，不是相对于整个请求包。这里字段值是数组 `[]`；第一段 `selected` 不是数组数字索引，未改动的 `payload_v6._pointer([], "/selected/rules")` 因而报 **`Invalid array pointer`**。根 pointer `""` 才表示读取该整个空数组。
5. `revision_errors[1]` 因此记录 `Invalid array pointer`，并触发冻结的一次修订上限。最终错误 **`Candidate admission failed within frozen revision budget: Invalid array pointer`** 是第二层错误，最初触发修订的原因是不存在的规则索引0。

这一条件的三次更新请求已计费 USD **0.002081004**；更新未发布。不能将三次 API 请求或后续受阻 actor 数当作三次独立更新实验。

## 诊断性内存重放

只在单独的 Python 对象副本中将六个 `retain_rule_indices` 从 `[0]` 改成 `[]`，保持原补丁文本、basis、证据 ID 与候选集合全部不变，再调用未改动的 `rules_v5.patches`，该局部补丁集合通过。

这说明此次最初错误可定位到机械索引协议；不是已经证明语义规则正确、完整快照发布成功或任务完成。本次没有把这个内存副本写回实验、没有发布知识，也没有调用 actor。真实原响应与失败状态原样保留。

## 安全的后续修复方案

### 1. 程序提供合法保留操作，LLM 不猜索引

- 每个 `selected` 记录显式提供 `valid_retain_rule_indices` 与带索引的已有规则，而不只给 `rules` 文本。
- 空规则记录的解码约束应强制 `retain_rule_indices=[]`。如果整个局部包所有记录均无已有规则，可用普通数组 schema 加 `maxItems: 0`，无需让模型作这个不存在的选择。
- 对空/非空记录混合包，使用每个工具独立的输出分支（工具 ID 为单值 enum，各自约束合法索引），或使用程序生成的合法规则操作句柄。不能把所有工具的索引并成一个全局 enum，否则另一条有规则的工具会让空规则工具的 `[0]` 仍在解码层合法。
- 保留程序侧对范围、唯一性、排序与最终快照的检查。不能通过删除检查、任意丢掉越界索引来让当前实验过关。
- 如采用 `anyOf` / `maxItems` / 索引 enum，应先验证实际服务商支持的 strict-schema 子集，并把展开后的 schema 字节也纳入输入预算，避免为修格式又引入输入膨胀。

### 2. 程序提供证据读取选项，LLM 不发明 JSON pointer

- 为当前候选/引用变化范围内可读的字段与精确子树生成 `selector_id -> {tool_id,side,field,pointer}` 本地表。模型返回有限的 selector ID，程序恢复原选择器，再走现有字段与 scope 校验。
- `usage_rules` 是数组；根 `""` 表示整个字段，已有元素才允许 `/0`、`/1`。`/selected/rules` 是提示包位置，绝不能被当成字段内 pointer。
- 没有必要把全局目录或完整 schema 重新上传。当前对象已有 `rules=[]`，这种机械事实可由程序直接告知，无需额外证据请求。
- 若允许按需探索更深子树，只在候选字段内部展开下一层合法选项并计费；不知道某个路径时标为不可用，不提供执行代码或任意读取接口。
- 选择器必须按完整组合约束，不能仅给 tool_id、side、field、pointer 各自的独立 enum；独立 enum 的笛卡尔积可能包含不存在的组合。

### 3. 修订反馈应可操作，同时保留冻结边界

当前 `admission_diagnostics` 在本例为空，LLM 只看到总错误字符串。后续可由程序返回：具体工具、当前已有规则数、模型给出的索引、合法索引集合以及 `expected=[]`。这是确定性协议诊断，不提供任务答案或 judge 信息。

建议增加离线回归：六条空规则原回复被解码器拒绝；合法空保留通过；混合包的合法索引不串工具；无效字段路径/错 side 拒绝；合法根读取通过；仍保留未知证据、覆盖、删除工具引用和最终准入失败测试。新方法完成离线验证后再启动新的冻结评测，不修改当前 V6-r1 的失败记录。

## 结论

本例是 **模型输出的机械协议错误 + 不可操作的修订反馈 + 自由构造 pointer 的二次错误**。它不足以证明“模型不懂 SwiftUI”或“Selective 无价值”。安全修复方向是把可由程序确定的索引与证据位置变成合法操作集合，保留语义判断给 LLM，并保留全部最终准入检查。

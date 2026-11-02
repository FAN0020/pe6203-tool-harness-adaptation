# 当前分支 evaluation

评测代码版本：`5b772ff54be7d43c1c3ff3c3fde0068fb94a3fb2`；分支 `codex/completion-quality-study`。本次复算已有真实实验，没有重新采样 actor/judge，也没有新增模型费用。

**结论：证据完整性与全分支测试通过，但尚无候选达到研究晋级要求。** 这两种“通过”必须分开。旧结果和旧结论未改写。

- 全测试：729 passed，0 failed / error / skipped，48.29 秒；包含真实本地 MCP 与模拟模型协议的集成测试。
- 历史 36 候选：复算 45 个 cohort、775 个计划格、517 个已执行格、2555 个有效评分槽、445 份已有产物审查；0 原评分差异、0 知识锁差异。33 个有 actor 记录的候选自身产物均已审查；尚有 72 个历史对照格没有映射产物审查。
- 最近 7 轮：6 轮完整，1 轮中断；69 条真实轨迹、68 条完整评分、340 个评分槽、69 份产物审查。另 1 个原型只做代码测试，不计作 benchmark 实验。

## 最近版本：同题配对结果

每项为 SP → 候选。133/283 合并同题 Middle/Late，235 为 Late；不跨题平均、不按单分排名。正常完成与完整产物通过各自计算，后者要求全部必要属性通过，未知不算通过。

| 版本 | 干预任务 | 正常完成 | 完整产物 | TF | PE | 本轮已知费用 USD | 决定 |
|---|---:|---|---|---|---|---:|---|
| observed_dictionary | 133 | 2/2 → 0/2 | 0/2 → 1/2 | 9.6 → 9.6 | 7.8 → 8.3 | 0.236955324 | 开发淘汰 |
| observed_contrastive | 133 | 0/2 → 1/2 | 0/2 → 0/2 | 9.7 → 9.7 | 6.8 → 7.2 | 0.223354932 | 开发淘汰 |
| capability_consolidation | 133 | 2/2 → 0/2 | 0/2 → 0/2 | 9.7 → 9.2 | 8 → 4.8 | 0.253853268 | 开发淘汰 |
| relational_probe_memory | 283 | 0/2 → 0/2 | 0/2 → 0/2 | 9.7 → 8.4 | 8.9 → 8.4 | 0.201469284 | 开发淘汰 |
| pruned_episode_memory | 283 | 0/2 → 0/2 | 0/2 → 0/2 | 9.4 → 9 | 7.8 → 9.2 | 0.178438368 | 开发淘汰 |
| capability_relation_matrix | 133 | 2/2 → 1/2 | 0/2 → 0/2 | 9.8 → 9.6 | 7.2 → 6.8 | 0.211661676 | 开发淘汰 |
| relation_witness_basis | 133 | 1/2 → 0/1已运行；1未运行 | 0/2 → 0/1已审查 | 9.3 → 缺失 | 8.3 → 缺失 | 0.184309596 + 未知 | 中断，晋级已不可能 |

中断行分母不同，只描述完成度，不作为完整配对均值比较；逐阶段结果见 CSV。`relation_witness_basis` 即使剩余133 Middle正常完成，也最多1/2，不能严格超过SP的1/2；保持题235完整产物SP1/1、候选0/1，亦未通过保持要求。缺失TF/PE和未运行产物仍为空。

这轮复算不改变原语义判断。`observed_dictionary` 的133产物局部通过出现在截断轨迹；`observed_contrastive` 的完成收益未伴随完整产物改善；较高PE、正确原生调用或较少调用均不能替代最终交付。283/235在最近数学干预中知识与SP相同，其波动不能归因于该干预。

## 比较文件与适用边界

- [36候选评测层级](candidate-maturity-36.csv)：3个无actor结果的候选为workflow_notes、semantic_contract_closure、active_contract_probing；生成或准入失败不等于整类机制失败。
- [Top 5逐条件配对表](top5-pairs.csv)：80行（64个旧配对条件，加16个至少一臂未执行的计划条件），明确sufficiency_feedback、observed_contract、discovery_contract、budget_feedback、shared_contract_refs及各cohort/版本，不合并同名不同版本。
- [全部历史逐条件表](historical-pairs.csv)：227行含55个至少一臂未执行的计划条件；未执行不补成失败评分。原benchmark、带固定fixture的原题、受控合成各自标注；377不纳入可执行比较。部分早期cohort实际provider混用，不能与固定DigitalOcean试验合并归因。
- [最近逐条件表](recent-pairs.csv)及[逐格表](recent-cells.csv)：分别列完成、全部必要产物属性、TF/PE、工具错误和成本，未运行/未评分保留缺失。最近轮次核验器未输出输运事件总数，该列留空，不补0。费用列为actor/judge已知费用；共享updater/preflight成本在轮次总费用中，不重复摊算。
- [机器结果](evaluation.json)：失败门槛、样本数、文件哈希和限制。开发样本已暴露，不是未见任务或独立验证；ECS需要匹配三阶段，本次不凭Middle/Late补算。

已有盲审偏差继续保留：relational_probe_memory最后2份曾有聚合分数暴露；capability_relation_matrix最后1份可能暴露方法，其10份均在分数解盲前。最新中断轮9份审查均在方法与分数解盲前封存。本次仅复算这些判断，不把同一协调者的复查称为独立盲审。

## 中断与费用

最新第9格actor已结束，首个judge请求120秒超时，无generation ID；五槽没有有效分数。原协议将该失败标为不可恢复；第10格尚未执行。冻结的unknown_charge停止规则与尚未批准的A3例外仍有效，本次没有重采评分、跳过收费停止或改写失败。

本次新增模型费用 **USD0**。历史去重 **6386** 笔已定价回执，已知费用下界 **USD8.6984822585**；4笔ledger未知及早期缺ID失败请求仍保留，预留金额不当作实际费用。没有新增总费用上限。

## 复算命令

在仓库根目录运行；均不调用付费模型。旧脚本closure会重写相同内容的旧核验JSON，其他输出写入本目录。

```bash
uv run pytest -q --junitxml=results/evaluation/current-branch-5b772ff-20261102/pytest.xml
uv run python scripts/verify_reaudit_closure.py
uv run python results/evidence/capability-relation-matrix-20261102/verify_trial.py
uv run python results/evidence/relation-witness-basis-20261102/verify_at_stop.py
uv run python results/evaluation/current-branch-5b772ff-20261102/replay_registry.py
uv run python results/evaluation/current-branch-5b772ff-20261102/summarize.py
```

前三个归档核验的stdout分别保存在prior-five.json、capability-relation-matrix.json、relation-witness-basis.json；独立错误日志为空。所有历史原始记录和实验源码保持原样。

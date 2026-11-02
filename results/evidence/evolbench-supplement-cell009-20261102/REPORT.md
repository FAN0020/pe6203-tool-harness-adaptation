# EvolBench 官方评分补充结果

按用户选择“只补评缺失的1条”，对 `relation-witness-basis-pilot-20261102 / cell-009` 的既有轨迹完成一次单独官方评分。任务为原benchmark **283 / Middle / Selective Patch**；冻结提交 `f08fb29`。

| 评分槽 | TF | PE | Grounding |
|---:|---:|---:|---:|
| 1 | 10 | 9 | 10 |
| 2 | 10 | 9 | 10 |
| 3 | 10 | 9 | 10 |
| 4 | 10 | 5 | 10 |
| 5 | 10 | 9 | 10 |
| **均值** | **10.0** | **8.2** | **10.0** |

**5/5 槽有效，5次真实judge请求均首次成功。新增费用 USD0.010989048，新增未知费用0。** 沿用 `deepseek/deepseek-v4.1-flash-1017` / DigitalOcean、temperature0、4096 tokens、120秒请求超时、关闭reasoning和原有重试规则。逐笔回执的实际model/provider均匹配。

评分调用使用项目已冻结的EvolBench官方rubric适配器：保留原rubric及工具观察1000字符截断，附加既有concise-counts-v1格式和输入计数；原5个提示逐字复用，未改变评分尺度或重新洗牌。不是运行pytest或离线均值复算来代替模型评分。

## 结果边界

- 原actor未重新运行，仍为 `max_rounds`。第10格没有执行。
- 原第9格失败、不可恢复标记、缺失主评分和未知费用均逐字保留。本结果是用户明确要求的**独立补充评分批次**，不覆盖或回填主实验，不称作独立任务验证。
- 已有产物审查 `R02` 仍为未通过：coverage和scope_preserved通过，structure_and_scope与delivery_truth未知；最终答复为空。官方TF高分不能替代完整交付验收。
- 没有改变开发淘汰结论，也没有达到双提升Goal。

## 复算与费用

离线核验通过：91份冻结输入/代码、23份补充原始文件，全部5个prompt/request/response/score/receipt匹配。模型调用前33项judge/重试/费用测试通过。准备阶段曾因哈希清单引用不存在的本地模块而失败，已在模型调用前修正，详见preparation-errors.json；不归因于候选或评分模型。

历史费用去重合计 **6391** 笔已定价回执，已知下界 **USD8.7094713065**。原4笔ledger未知及早期缺ID请求仍为未知，没有新增费用上限。

- [评分及逐笔费用核验](verification.json)
- [费用增量](cost-addendum.json)
- [冻结方案](freeze.json)
- [用户授权范围](authorization.json)

```bash
uv run python results/evidence/evolbench-supplement-cell009-20261102/verify.py
```

该命令仅复算已归档结果，不调用模型。run_supplement.py拒绝已有输出/账本的重采；不要再次执行--run。

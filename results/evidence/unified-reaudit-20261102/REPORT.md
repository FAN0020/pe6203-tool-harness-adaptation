# PE6203 统一复评工作记录（2026-11-02）

状态：审计与新机制迭代进行中，完整研究Goal未达成。旧实验结论、评分与失败均未改写。

36项的可核实定义是请求前提交 `d6b60d2` 的 `patch_variants.VARIANTS`。这是登记项清单，不等于36个均完成实测的方法；描述压缩生成器等额外原型另有费用与证据，不塞进这36项。

**Top 5来源已由用户补齐。** 明确名称为sufficiency_feedback、observed_contract、discovery_contract、budget_feedback、shared_contract_refs；第5项原文为“shared_contract_refs等最近候选”，未指明的集合成员不擅自补列。budget_feedback与observed_contract合并后无需新增重复项。版本和原记录见top5-provenance.json。以下36项按登记顺序列出，不是排名。

离线复算：45个队列、775计划格、517已执行格、2555有效评分槽；340格已有可映射的逐属性产品判断。原始槽与TF/PE均值不符0，冻结知识文件哈希不符0。未执行格与缺失判断不计成功。

| 登记候选 | Actor/5槽评分格 | 已有逐属性审查格 | 原题 / 固定fixture原题 / 合成 | 版本与证据边界 |
|---|---:|---:|---|---|
| `delta_notes` | 6/6 | 0 | 6 / 0 / 0 | 协议：selective-search-v1, selective-search-v1.1 |
| `linked_notes` | 6/6 | 0 | 6 / 0 / 0 | 协议：selective-search-v1, selective-search-v1.1 |
| `feedback_notes` | 6/6 | 0 | 6 / 0 / 0 | 协议：selective-search-v1, selective-search-v1.1 |
| `sufficiency_notes` | 6/6 | 0 | 6 / 0 / 0 | 协议：selective-search-v2, selective-search-v2.1 |
| `workflow_notes` | 0/0 | 0 | 0 / 0 / 0 | v2生成后语义拒绝；没有actor结果 |
| `sufficiency_feedback` | 39/39 | 15 | 39 / 0 / 0 | 完整108格四臂确认；供应商未固定、未完成逐项产品审查，非当前Goal通过 |
| `budget_feedback` | 34/32 | 24 | 34 / 0 / 0 | v3开发、两次中断108格计划、后续固定供应商复查；不得称108已完成 |
| `budget_contract` | 3/3 | 3 | 3 / 0 / 0 | 协议：budget-contract-v1 |
| `evidence_scope` | 3/3 | 3 | 3 / 0 / 0 | 协议：evidence-scope-v1 |
| `observed_contract` | 21/21 | 21 | 21 / 0 / 0 | 原题pilot6格；验证36格=两批各18格；两批均失败 |
| `artifact_contract` | 4/4 | 4 | 2 / 2 / 0 | 原题457必须区分缺fixture、补PDF、补runtime各准备版本；执行数不是全部原计划数 |
| `document_sequence` | 3/3 | 3 | 1 / 2 / 0 | 协议：document-sequence-v1 |
| `project_state_contract` | 2/2 | 2 | 2 / 0 / 0 | 协议：project-state-v1 |
| `thinking_contract` | 2/2 | 2 | 2 / 0 / 0 | 协议：thinking-contract-v1 |
| `weather_provenance` | 3/3 | 3 | 3 / 0 / 0 | 协议：weather-provenance-v1 |
| `contract_reconcile` | 3/3 | 3 | 3 / 0 / 0 | 协议：contract-reconcile-v1 |
| `native_media_contract` | 3/3 | 3 | 3 / 0 / 0 | 协议：native-media-contract-v1 |
| `discovery_contract` | 21/21 | 21 | 21 / 0 / 0 | 原题pilot6格；验证36格=两批各18格；两批均失败 |
| `native_argument_routing` | 2/2 | 0 | 1 / 0 / 1 | 原377缺输入未执行；actor证据来自独立合成扩展及235保持 |
| `verified_component_memory` | 2/2 | 2 | 1 / 0 / 1 | 原生准入及共同运行依赖通过后仅合成扩展actor；不能替代原377 |
| `prefix_workflow_memory` | 3/3 | 3 | 1 / 2 / 0 | 协议：prefix-workflow-memory-v1 |
| `semantic_contract_direct` | 6/6 | 6 | 6 / 0 / 0 | v1生成拒绝；v2主张修复与后续optional_projection共同对照分开记录 |
| `semantic_contract_closure` | 0/0 | 0 | 0 / 0 / 0 | 联合edit/edge生成未准入；没有closureactor结果 |
| `optional_parameter_projection` | 3/3 | 3 | 3 / 0 / 0 | 协议：optional-parameter-projection-v1 |
| `capability_warning` | 2/2 | 2 | 2 / 0 / 0 | 协议：capability-withdrawal-v1 |
| `capability_withdrawal` | 2/2 | 2 | 2 / 0 / 0 | 协议：capability-withdrawal-v1 |
| `native_record_batch` | 2/2 | 2 | 2 / 0 / 0 | 协议：native-record-batch-v1 |
| `dependency_cut` | 13/13 | 13 | 5 / 0 / 8 | 协议：dependency-cut-v1 |
| `observation_coverage` | 13/13 | 13 | 5 / 0 / 8 | 协议：observation-coverage-v1 |
| `ready_link` | 5/5 | 5 | 5 / 0 / 0 | 协议：ready-link-v1 |
| `reviewed_coverage` | 5/5 | 5 | 5 / 0 / 0 | 协议：reviewed-coverage-v1 |
| `evidence_dispatch` | 5/5 | 5 | 5 / 0 / 0 | 协议：evidence-dispatch-v1 |
| `instruction_scope` | 5/5 | 5 | 5 / 0 / 0 | 协议：instruction-scope-v1 |
| `instruction_scope_quote` | 5/5 | 5 | 5 / 0 / 0 | 协议：instruction-scope-v1 |
| `active_contract_probing` | 0/0 | 0 | 0 / 0 / 0 | v1及一次引用恢复共13updater请求；语义/规则准入失败，没有actor结果 |
| `shared_contract_refs` | 5/4 | 5 | 5 / 0 / 0 | 10格中9评分+1原429失败；A2只补未开始4格，未重复失败格 |

所有数字均为该候选臂自身，不重复计入SP。每个协议、知识哈希、原题文本/哈希、评分槽、状态与审查来源见 `candidate-inventory.json`、`cohorts.json`、`cells.json`；精确条件表见 `condition-comparison.csv`。

## 优先复评：相同任务条件逐项展示

下面展示5个已核实名称及所在队列SP；不同队列、任务或阶段不求统一均值、不作加权排名。完成/全属性列分母是实际执行格；全属性分子后另列审查覆盖，避免把未审查混成失败。缺分或未跑完整计划时完整TF/PE保持空值。

| 队列 | 题/阶段 | 方法 | 完成/执行 | 全属性通过/已审查 | TF/PE（评分n） | 外层工具错/调用 | Actor+Judge已知$ |
|---|---|---|---:|---:|---|---:|---:|
| completion-quality-v1-20261031 | 283/late | selective_patch | 0/1 | 0/1 | 10.000/9.000（1） | 4/75 | 0.024464674 |
| completion-quality-v1-20261031 | 283/middle | selective_patch | 1/1 | 0/1 | 10.000/9.000（1） | 0/52 | 0.015620497 |
| completion-quality-v1-20261031 | 235/middle | budget_feedback | 1/1 | 0/1 | 10.000/7.000（1） | 0/4 | 0.0075123728 |
| completion-quality-v1-20261031 | 133/middle | selective_patch | 0/1 | 0/1 | 10.000/8.000（1） | 0/9 | 0.011839407 |
| completion-quality-v1-20261031 | 235/late | selective_patch | 1/1 | 0/1 | 10.000/10.000（1） | 0/3 | 0.0064258676 |
| completion-quality-v1-20261031 | 133/late | selective_patch | 1/1 | 0/1 | 9.800/8.000（1） | 2/15 | 0.010657038 |
| completion-quality-v1-20261031 | 283/middle | budget_feedback | 1/1 | 1/1 | 10.000/9.200（1） | 1/50 | 0.0333147932 |
| completion-quality-v1-20261031 | 235/late | budget_feedback | 1/1 | 0/1 | 10.000/10.000（1） | 0/3 | 0.0035700820 |
| completion-quality-v1-20261031 | 235/middle | selective_patch | 1/1 | 0/1 | 10.000/10.000（1） | 0/3 | 0.0036481268 |
| completion-quality-v1-20261031 | 133/late | budget_feedback | 1/1 | 0/1 | 10.000/10.000（1） | 0/2 | 0.0050576556 |
| completion-quality-v1-20261031 | 133/middle | budget_feedback | 0/1 | 0/1 | 10.000/7.400（1） | 0/10 | 0.012730017 |
| completion-quality-v1-20261031 | 283/late | budget_feedback | 0/1 | 0/1 | 10.000/9.200（1） | 0/41 | 0.022368004 |
| daily-migration-pilot-20261031 | 90/late | selective_patch | 1/1 | 0/0 | 10.000/10.000（1） | 0/4 | 0.017328144 |
| daily-migration-pilot-20261031 | 90/middle | selective_patch | 1/1 | 0/0 | 10.000/10.000（1） | 0/4 | 0.016931388 |
| daily-migration-pilot-20261031 | 90/early | selective_patch | 1/1 | 0/0 | 10.000/9.400（1） | 0/4 | 0.016766580 |
| daily-migration-pilot-20261031 | 90/middle | budget_feedback | 1/1 | 0/0 | 10.000/8.800（1） | 0/4 | 0.016337424 |
| daily-migration-pilot-20261031 | 90/early | budget_feedback | 1/1 | 0/0 | 10.000/9.400（1） | 0/4 | 0.016338168 |
| daily-migration-pilot-20261031 | 90/late | budget_feedback | 1/1 | 0/0 | 10.000/9.800（1） | 0/4 | 0.016425636 |
| discovery-contract-pilot-20261101 | 235/late | discovery_contract | 1/1 | 0/1 | 10.000/10.000（1） | 0/3 | 0.007095720 |
| discovery-contract-pilot-20261101 | 87/late | selective_patch | 0/1 | 0/1 | 9.800/8.400（1） | 0/9 | 0.012458088 |
| discovery-contract-pilot-20261101 | 87/middle | selective_patch | 1/1 | 0/1 | 9.800/8.800（1） | 1/11 | 0.016060140 |
| discovery-contract-pilot-20261101 | 87/late | discovery_contract | 1/1 | 0/1 | 9.800/8.600（1） | 0/10 | 0.015386340 |
| discovery-contract-pilot-20261101 | 87/middle | discovery_contract | 1/1 | 0/1 | 10.000/9.800（1） | 0/10 | 0.013839744 |
| discovery-contract-pilot-20261101 | 235/late | selective_patch | 1/1 | 0/1 | 10.000/10.000（1） | 0/3 | 0.007606332 |
| discovery-contract-validation-20261101 | 235/late | discovery_contract | 6/6 | 0/6 | 10.000/10.000（6） | 0/18 | 0.042878220 |
| discovery-contract-validation-20261101 | 87/late | selective_patch | 6/6 | 0/6 | 9.900/8.167（6） | 2/64 | 0.086609652 |
| discovery-contract-validation-20261101 | 87/late | discovery_contract | 5/6 | 0/6 | 8.633/7.600（6） | 0/46 | 0.076995024 |
| discovery-contract-validation-20261101 | 235/late | selective_patch | 6/6 | 1/6 | 10.000/10.000（6） | 0/18 | 0.043403580 |
| discovery-contract-validation-20261101 | 87/middle | discovery_contract | 6/6 | 0/6 | 8.633/7.467（6） | 2/53 | 0.071212524 |
| discovery-contract-validation-20261101 | 87/middle | selective_patch | 5/6 | 0/6 | 9.967/8.333（6） | 2/67 | 0.086444724 |
| evidence-scope-pilot-20261031 | 235/late | budget_feedback | 1/1 | 0/1 | 10.000/10.000（1） | 0/3 | 0.007339416 |
| evidence-scope-pilot-20261031 | 133/late | budget_feedback | 1/1 | 0/1 | 9.600/9.800（1） | 0/2 | 0.008543628 |
| evidence-scope-pilot-20261031 | 283/late | budget_feedback | 0/1 | 0/1 | 9.800/8.600（1） | 0/55 | 0.036876864 |
| existing-method-recheck-20261031 | 235/late | budget_feedback | 1/1 | 1/1 | 10.000/10.000（1） | 0/3 | 0.007635516 |
| existing-method-recheck-20261031 | 283/middle | selective_patch | 0/1 | 0/1 | 9.600/9.200（1） | 1/58 | 0.040768020 |
| existing-method-recheck-20261031 | 133/late | selective_patch | 1/1 | 0/1 | 9.800/9.000（1） | 0/2 | 0.011241180 |
| existing-method-recheck-20261031 | 133/late | budget_feedback | 1/1 | 0/1 | 9.400/6.600（1） | 0/6 | 0.009618228 |
| existing-method-recheck-20261031 | 283/middle | budget_feedback | 0/1 | 0/1 | 7.400/7.400（1） | 7/76 | 0.040210620 |
| existing-method-recheck-20261031 | 235/late | selective_patch | 1/1 | 0/1 | 10.000/10.000（1） | 0/3 | 0.006913236 |
| observed-contract-pilot-20261031 | 235/late | observed_contract | 1/1 | 0/1 | 10.000/10.000（1） | 0/3 | 0.006941016 |
| observed-contract-pilot-20261031 | 133/late | selective_patch | 0/1 | 0/1 | 7.600/5.800（1） | 1/13 | 0.012920376 |
| observed-contract-pilot-20261031 | 133/middle | selective_patch | 0/1 | 0/1 | 9.400/6.200（1） | 1/8 | 0.011015736 |
| observed-contract-pilot-20261031 | 133/late | observed_contract | 0/1 | 0/1 | 9.600/6.600（1） | 1/12 | 0.011316492 |
| observed-contract-pilot-20261031 | 133/middle | observed_contract | 1/1 | 0/1 | 9.600/5.800（1） | 1/12 | 0.010515420 |
| observed-contract-pilot-20261031 | 235/late | selective_patch | 1/1 | 0/1 | 10.000/10.000（1） | 0/3 | 0.007131732 |
| observed-contract-validation-20261031 | 235/late | observed_contract | 6/6 | 2/6 | 10.000/10.000（6） | 0/18 | 0.043809540 |
| observed-contract-validation-20261031 | 133/late | selective_patch | 2/6 | 0/6 | 9.533/6.667（6） | 3/61 | 0.070010700 |
| observed-contract-validation-20261031 | 133/late | observed_contract | 2/6 | 0/6 | 9.300/7.300（6） | 5/84 | 0.073298664 |
| observed-contract-validation-20261031 | 235/late | selective_patch | 6/6 | 3/6 | 10.000/10.000（6） | 0/18 | 0.043485648 |
| observed-contract-validation-20261031 | 133/middle | observed_contract | 3/6 | 0/6 | 9.500/8.000（6） | 1/43 | 0.063646032 |
| observed-contract-validation-20261031 | 133/middle | selective_patch | 6/6 | 0/6 | 9.800/8.733（6） | 0/34 | 0.058622280 |
| paired-extension-20261031 | 283/late | selective_patch | 0/1 | 0/1 | 10.000/9.200（1） | 2/79 | 0.041296608 |
| paired-extension-20261031 | 133/middle | selective_patch | 0/1 | 0/1 | 9.600/6.000（1） | 2/18 | 0.012289920 |
| paired-extension-20261031 | 235/late | budget_feedback | 1/1 | 0/1 | 9.200/10.000（1） | 0/3 | 0.006665232 |
| paired-extension-20261031 | 235/late | selective_patch | 1/1 | 0/1 | 10.000/10.000（1） | 0/3 | 0.007028628 |
| paired-extension-20261031 | 283/middle | selective_patch | 0/1 | 0/1 | 7.600/9.000（1） | 1/38 | 0.024176712 |
| paired-extension-20261031 | 133/late | selective_patch | 0/1 | 0/1 | 9.400/6.200（1） | 1/17 | 0.012929112 |
| paired-extension-20261031 | 133/late | budget_feedback | 1/1 | 0/1 | 9.800/7.200（1） | 0/5 | 0.010016736 |
| paired-extension-20261031 | 235/middle | selective_patch | 1/1 | 0/1 | 9.800/9.800（1） | 0/3 | 0.006990240 |
| paired-extension-20261031 | 283/middle | budget_feedback | 1/1 | 1/1 | 10.000/9.200（1） | 0/43 | 0.030568260 |
| paired-pilot-20261031 | 133/middle | budget_feedback | 1/1 | 0/1 | 10.000/10.000（1） | 0/3 | 0.008080608 |
| paired-pilot-20261031 | 283/late | budget_feedback | 1/1 | 0/1 | 9.800/9.200（1） | 0/41 | 0.027842064 |
| paired-pilot-20261031 | 235/middle | budget_feedback | 1/1 | 0/1 | 10.000/10.000（1） | 0/3 | 0.007993548 |
| selective-search-confirmation-r1-20261031 | 235/early | sufficiency_feedback | 3/3 | 1/3 | 10.000/8.333（3） | 0/11 | 0.016320107 |
| selective-search-confirmation-r1-20261031 | 235/middle | selective_patch | 3/3 | 1/3 | 10.000/10.000（3） | 0/9 | 0.015804464 |
| selective-search-confirmation-r1-20261031 | 283/late | selective_patch | 1/3 | 0/0 | 10.000/8.800（3） | 3/181 | 0.057323424 |
| selective-search-confirmation-r1-20261031 | 283/early | selective_patch | 0/3 | 0/0 | 10.000/8.400（3） | 2/142 | 0.051378074 |
| selective-search-confirmation-r1-20261031 | 283/late | sufficiency_feedback | 1/3 | 0/0 | 10.000/9.267（3） | 0/137 | 0.038124482 |
| selective-search-confirmation-r1-20261031 | 133/late | selective_patch | 1/3 | 0/0 | 10.000/7.467（3） | 1/53 | 0.043391738 |
| selective-search-confirmation-r1-20261031 | 283/early | sufficiency_feedback | 0/3 | 0/0 | 10.000/8.533（3） | 1/202 | 0.049743504 |
| selective-search-confirmation-r1-20261031 | 133/early | sufficiency_feedback | 0/3 | 0/0 | 10.000/7.067（3） | 3/63 | 0.033786567 |
| selective-search-confirmation-r1-20261031 | 133/middle | sufficiency_feedback | 1/3 | 0/0 | 9.933/9.267（3） | 0/20 | 0.046179107 |
| selective-search-confirmation-r1-20261031 | 133/early | selective_patch | 3/3 | 0/0 | 10.000/8.600（3） | 0/20 | 0.031316519 |
| selective-search-confirmation-r1-20261031 | 235/early | selective_patch | 3/3 | 0/3 | 10.000/9.000（3） | 0/10 | 0.012147916 |
| selective-search-confirmation-r1-20261031 | 283/middle | sufficiency_feedback | 1/3 | 0/0 | 10.000/9.000（3） | 0/185 | 0.068620842 |
| selective-search-confirmation-r1-20261031 | 235/late | sufficiency_feedback | 3/3 | 0/3 | 10.000/10.000（3） | 0/9 | 0.011427112 |
| selective-search-confirmation-r1-20261031 | 235/middle | sufficiency_feedback | 3/3 | 0/3 | 10.000/10.000（3） | 0/9 | 0.012007970 |
| selective-search-confirmation-r1-20261031 | 133/late | sufficiency_feedback | 2/3 | 0/0 | 10.000/9.200（3） | 0/22 | 0.026503114 |
| selective-search-confirmation-r1-20261031 | 235/late | selective_patch | 3/3 | 1/3 | 10.000/9.000（3） | 0/10 | 0.010207135 |
| selective-search-confirmation-r1-20261031 | 133/middle | selective_patch | 2/3 | 0/0 | 10.000/7.933（3） | 4/60 | 0.032150825 |
| selective-search-confirmation-r1-20261031 | 283/middle | selective_patch | 1/3 | 0/0 | 9.933/8.067（3） | 4/148 | 0.052201428 |
| selective-search-confirmation-r2-20261031 | 235/early | budget_feedback | 1/1 | 0/0 | 缺失/缺失（1） | 0/3 | 0.003500422 |
| selective-search-confirmation-r2-20261031 | 235/middle | selective_patch | 1/1 | 0/0 | 缺失/缺失（1） | 0/3 | 0.003206395 |
| selective-search-confirmation-r2-20261031 | 283/late | selective_patch | 1/1 | 0/0 | 缺失/缺失（1） | 1/91 | 0.029514328 |
| selective-search-confirmation-r2-20261031 | 283/early | selective_patch | 0/1 | 0/0 | 缺失/缺失（1） | 0/38 | 0.0111037996 |
| selective-search-confirmation-r2-20261031 | 283/late | budget_feedback | 0/1 | 0/0 | 缺失/缺失（0） | 0/32 | 0.014331773 |
| selective-search-confirmation-r2-20261031 | 133/late | selective_patch | 0/1 | 0/0 | 缺失/缺失（0） | 0/0 | 0 |
| selective-search-confirmation-r3-20261031 | 235/early | budget_feedback | 1/1 | 0/0 | 缺失/缺失（1） | 0/3 | 0.003725864 |
| selective-search-confirmation-r3-20261031 | 235/middle | selective_patch | 1/1 | 0/0 | 缺失/缺失（1） | 0/3 | 0.002938164 |
| selective-search-confirmation-r3-20261031 | 283/late | selective_patch | 0/1 | 0/0 | 缺失/缺失（1） | 1/68 | 0.021933332 |
| selective-search-confirmation-r3-20261031 | 283/early | selective_patch | 0/1 | 0/0 | 缺失/缺失（0） | 0/6 | 0.003220548 |
| selective-search-confirmation-r3-20261031 | 283/late | budget_feedback | 0/1 | 0/0 | 缺失/缺失（0） | 0/0 | 0 |
| selective-search-v2.1-development-20261031 | 235/middle | selective_patch | 1/1 | 0/0 | 10.000/10.000（1） | 0/3 | 0.005812644 |
| selective-search-v2.1-development-20261031 | 283/late | sufficiency_feedback | 0/1 | 0/0 | 9.800/8.200（1） | 0/54 | 0.028638821 |
| selective-search-v2.1-development-20261031 | 133/late | selective_patch | 1/1 | 0/0 | 10.000/7.800（1） | 1/11 | 0.007097256 |
| selective-search-v2.1-development-20261031 | 283/middle | selective_patch | 0/1 | 0/0 | 9.800/5.600（1） | 0/65 | 0.030339384 |
| selective-search-v2.1-development-20261031 | 283/late | selective_patch | 1/1 | 0/0 | 10.000/9.000（1） | 1/49 | 0.014555858 |
| selective-search-v2.1-development-20261031 | 133/late | sufficiency_feedback | 0/1 | 0/0 | 10.000/7.800（1） | 0/13 | 0.0113315880 |
| selective-search-v2.1-development-20261031 | 133/middle | sufficiency_feedback | 1/1 | 0/0 | 10.000/8.000（1） | 0/13 | 0.009180518 |
| selective-search-v2.1-development-20261031 | 235/late | sufficiency_feedback | 1/1 | 0/0 | 10.000/10.000（1） | 0/3 | 0.002650173 |
| selective-search-v2.1-development-20261031 | 283/middle | sufficiency_feedback | 1/1 | 0/0 | 10.000/9.000（1） | 0/38 | 0.010018960 |
| selective-search-v2.1-development-20261031 | 133/middle | selective_patch | 0/1 | 0/0 | 9.800/3.400（1） | 1/31 | 0.012531861 |
| selective-search-v2.1-development-20261031 | 235/middle | sufficiency_feedback | 1/1 | 0/0 | 10.000/10.000（1） | 0/3 | 0.002705030 |
| selective-search-v2.1-development-20261031 | 235/late | selective_patch | 1/1 | 0/0 | 10.000/10.000（1） | 0/3 | 0.0069911044 |
| selective-search-v3-development-20261031 | 235/middle | selective_patch | 1/1 | 0/1 | 10.000/10.000（1） | 0/3 | 0.009145804 |
| selective-search-v3-development-20261031 | 283/late | budget_feedback | 1/1 | 1/1 | 10.000/8.800（1） | 1/36 | 0.013237148 |
| selective-search-v3-development-20261031 | 235/middle | sufficiency_feedback | 1/1 | 0/1 | 10.000/10.000（1） | 0/3 | 0.005777290 |
| selective-search-v3-development-20261031 | 283/late | sufficiency_feedback | 0/1 | 0/1 | 10.000/9.000（1） | 0/64 | 0.031226874 |
| selective-search-v3-development-20261031 | 133/late | selective_patch | 1/1 | 0/1 | 10.000/7.600（1） | 0/17 | 0.012398259 |
| selective-search-v3-development-20261031 | 235/late | sufficiency_feedback | 1/1 | 0/1 | 10.000/7.000（1） | 0/4 | 0.003781865 |
| selective-search-v3-development-20261031 | 283/middle | selective_patch | 1/1 | 1/1 | 10.000/9.000（1） | 0/36 | 0.019540726 |
| selective-search-v3-development-20261031 | 283/middle | sufficiency_feedback | 1/1 | 0/1 | 10.000/9.800（1） | 0/31 | 0.011831768 |
| selective-search-v3-development-20261031 | 283/late | selective_patch | 0/1 | 0/1 | 10.000/9.000（1） | 0/61 | 0.016315997 |
| selective-search-v3-development-20261031 | 133/late | budget_feedback | 1/1 | 0/1 | 10.000/10.000（1） | 0/3 | 0.004388326 |
| selective-search-v3-development-20261031 | 133/middle | budget_feedback | 1/1 | 0/1 | 10.000/5.200（1） | 0/6 | 0.006774807 |
| selective-search-v3-development-20261031 | 133/middle | sufficiency_feedback | 0/1 | 1/1 | 9.800/8.200（1） | 1/12 | 0.012632991 |
| selective-search-v3-development-20261031 | 235/late | budget_feedback | 1/1 | 0/1 | 10.000/10.000（1） | 0/3 | 0.002910616 |
| selective-search-v3-development-20261031 | 283/middle | budget_feedback | 1/1 | 0/1 | 10.000/9.800（1） | 0/27 | 0.007655458 |
| selective-search-v3-development-20261031 | 133/middle | selective_patch | 1/1 | 0/1 | 10.000/8.000（1） | 0/11 | 0.012311685 |
| selective-search-v3-development-20261031 | 133/late | sufficiency_feedback | 0/1 | 0/1 | 10.000/8.400（1） | 0/7 | 0.014336400 |
| selective-search-v3-development-20261031 | 235/middle | budget_feedback | 1/1 | 0/1 | 10.000/10.000（1） | 0/3 | 0.003541106 |
| selective-search-v3-development-20261031 | 235/late | selective_patch | 1/1 | 1/1 | 10.000/10.000（1） | 0/3 | 0.006527488 |
| shared-contract-refs-pilot-20261101 | 133/late | shared_contract_refs | 0/1 | 0/1 | 9.600/7.200（1） | 0/6 | 0.016176480 |
| shared-contract-refs-pilot-20261101 | 235/late | selective_patch | 1/1 | 0/1 | 9.800/10.000（1） | 0/3 | 0.007313892 |
| shared-contract-refs-pilot-20261101 | 133/late | selective_patch | 0/1 | 0/1 | 9.200/9.000（1） | 0/5 | 0.010615284 |
| shared-contract-refs-pilot-20261101 | 235/late | shared_contract_refs | 1/1 | 0/1 | 10.000/10.000（1） | 0/3 | 0.007525596 |
| shared-contract-refs-pilot-20261101 | 283/late | selective_patch | 0/1 | 0/1 | 9.800/8.800（1） | 2/77 | 0.071846256 |
| shared-contract-refs-pilot-20261101 | 283/late | shared_contract_refs | 0/1 | 0/1 | 缺失/缺失（0） | 1/28 | 0.011581140 |
| shared-contract-refs-pilot-20261101 | 283/middle | shared_contract_refs | 0/1 | 0/1 | 9.800/9.000（1） | 0/57 | 0.031997040 |
| shared-contract-refs-pilot-20261101 | 133/middle | selective_patch | 1/1 | 0/1 | 10.000/5.600（1） | 0/6 | 0.010265556 |
| shared-contract-refs-pilot-20261101 | 283/middle | selective_patch | 0/1 | 0/1 | 9.600/9.000（1） | 2/59 | 0.033480312 |
| shared-contract-refs-pilot-20261101 | 133/middle | shared_contract_refs | 1/1 | 0/1 | 9.600/6.000（1） | 0/21 | 0.013006524 |
| tool-migration-pilot-20261031 | 430/late | selective_patch | 1/1 | 0/0 | 9.800/7.400（1） | 0/6 | 0.009238872 |
| tool-migration-pilot-20261031 | 430/middle | selective_patch | 1/1 | 0/0 | 10.000/7.600（1） | 0/8 | 0.008698068 |
| tool-migration-pilot-20261031 | 430/early | selective_patch | 1/1 | 0/0 | 10.000/7.400（1） | 0/10 | 0.010272216 |
| tool-migration-pilot-20261031 | 430/middle | budget_feedback | 1/1 | 0/0 | 9.800/9.800（1） | 0/6 | 0.008383476 |
| tool-migration-pilot-20261031 | 430/early | budget_feedback | 1/1 | 0/0 | 10.000/6.000（1） | 1/13 | 0.011762652 |
| tool-migration-pilot-20261031 | 430/late | budget_feedback | 1/1 | 0/0 | 10.000/6.800（1） | 0/7 | 0.007958184 |

**可比性限制：** 早期sufficiency_feedback完整108格实际涉及12个actor供应商；completion-quality旧12格也采用价格路由，不能与固定DigitalOcean结果合并归因。existing-method-recheck、paired-extension和observed_contract验证实际均为DigitalOcean。`comparability.json`保留每队列实际供应商计数、原题/工具来源与知识锁。两批observed_contract验证已经包含全属性审查，不重跑。

235在这些固定实验中是精确同K0的保持任务；其完成、TF/PE与产品差异应作为运行波动报告，不能归因为知识干预。457补齐PDF/共同渲染依赖的版本单列固定fixture原题。900000以上独立编号为受控合成；377原输入缺失始终不纳入可执行比较。

## 费用与未知

响应ID去重并集：5560个已定价响应，已知USD **7.2084398105**。这是下界，不是已结清总额。

其中匹配队列actor/judge收据USD 6.9149795745；较广历史账本USD 4.753494864；updater收据USD 0.161608292。三者有重叠，**不可相加**。较广账本含课程基线、准入、原生诊断相关模型请求等。保留3笔未决账本请求；另有早期失败actor请求缺ID，不能仅用网页/key累计额度补记为0。

`cost-receipts.json`给出去重来源；`cost-audit.json`给出账本原数、复算、范围和未知。新字典轮费用在独立账本另报，不混入以上历史快照。

## 已推进的新机制

第一方向：对observed_contract原16条探针证据做无损表示。首版observed_dictionary共享完全相同的结果，保留全部输入/结果与边界，解码可恢复原记录；只改真实变化的validate_syntax知识。它不同于跨工具参数描述引用、语义主张替换和额外预算提示。

来源依据：本地observed_contract_note每条重复相同文本与限制；复用EasyTool论文2401.06201v3及官方JARVIS SHA7624cf388b47334ff8a0868e7d862dde18cfda86中的紧凑工具文档思想，未采用其分段执行器。这是本项目的无损编码机制，不声称复现完整EasyTool。

第一轮10格已完成，源冻结0393d55、盲审封存cbcfa17。SP→字典版：133正常完成2/2→0/2、完整产物0/2→1/2；全变化完成2/4→0/4、完整产物0/4→1/4、TF9.60→9.25。开发失败，不验证。117笔请求全部结算$0.236955324；50评分槽、335原生调用。92源文件/421原始文件与知识哈希、评分、响应ID全部核验。R04宽松主判通过但最终答复截断；预存严格敏感性将其guidance判unknown时也不晋级。

第二轮observed_contrastive在664057a单独冻结并开始10格开发：同表达式的观察基准参数+精确set/remove差分，保留全部16条输入/结果。检验显式输入关系是否有用，不声称比字典更短。知识只影响133，283/235逐字等同SP；当前只有一个准入方向，其他方向仍须证据比较，不凑数。

## 复算

```sh
uv run python scripts/research_reaudit.py
uv run python scripts/research_cost_reaudit.py
uv run python scripts/render_reaudit_report.py
```

上述均不调用模型、judge或MCP。离线哈希/分数复算不能替代语义产品审查；原生工具错误、模型输运错误、产品错误与审查代码错误必须分开记录。Top5名称已核实；未覆盖的逐属性审查、新方向及后续轮次仍属于待完成工作。新补的历史审查标注posthoc_scores_exposed，不能冒充盲态验证。审计映射修正见audit-corrections.json：不向未执行的准备计划挂载同ID后续产物审查。

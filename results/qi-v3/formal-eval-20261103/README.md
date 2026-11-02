# V3 formal knowledge-only evaluation

Four selected original MCPEvol-Bench tasks, three environments, No Update vs Full Rewrite vs V3, three independent actor executions per cell. Five official-rubric judge ratings per trajectory. Model repeats have no reproducibility seed. No extra Python execution/repair in either arm. Catalog-only V3 with frozen literal capability evidence; no source/probe bundle.

| Arm | Saved / planned | Final answers | TF /10 | PE /10 | Actor USD | Update USD once | Cohort deployment USD |
|---|---:|---:|---:|---:|---:|---:|---:|
| no_update | 36/36 | 35/36 | 9.483 | 7.622 | 0.309394212 | 0.0 | 0.309394212 |
| full_rewrite | 36/36 | 36/36 | 9.789 | 8.483 | 0.321119664 | 0.046184052 | 0.367303716 |
| selective_patch | 36/36 | 36/36 | 9.906 | 8.728 | 0.333520284 | 0.00489690 | 0.338417184 |

Update API charges are counted once per task/environment and reused across its three actor executions. Judge charges are evaluation overhead, excluded from deployment costs. Final-answer termination does not independently certify task completion. TF/PE are model-judged; five ratings are not five independent actor executions.

| Task | Stage | TF NU → V3 | PE NU → V3 | Actor USD NU → V3 | V3 update USD | Single-task USD NU → V3 | Errors NU → V3 |
|---|---|---:|---:|---:|---:|---:|---:|
| 430 | early | 10.000 → 9.933 | 7.000 → 7.267 | 0.006622 → 0.007415 | 0.000000 | 0.006622 → 0.007415 | 0.33 → 0.00 |
| 430 | middle | 9.933 → 10.000 | 6.800 → 8.200 | 0.006875 → 0.006877 | 0.000213 | 0.006875 → 0.007090 | 0.00 → 0.00 |
| 430 | late | 9.933 → 9.933 | 5.933 → 8.133 | 0.008422 → 0.007015 | 0.000399 | 0.008422 → 0.007414 | 4.33 → 0.00 |
| 133 | early | 9.200 → 9.800 | 5.467 → 8.133 | 0.007397 → 0.008810 | 0.000000 | 0.007397 → 0.008810 | 0.33 → 0.33 |
| 133 | middle | 9.267 → 9.867 | 7.267 → 6.600 | 0.007275 → 0.009848 | 0.001199 | 0.007275 → 0.011047 | 1.67 → 0.67 |
| 133 | late | 9.400 → 9.333 | 4.667 → 7.333 | 0.007240 → 0.009985 | 0.002209 | 0.007240 → 0.012194 | 6.00 → 1.67 |
| 90 | early | 10.000 → 10.000 | 10.000 → 9.733 | 0.015896 → 0.014209 | 0.000000 | 0.015896 → 0.014209 | 0.00 → 0.00 |
| 90 | middle | 10.000 → 10.000 | 9.133 → 9.800 | 0.015745 → 0.014332 | 0.000356 | 0.015745 → 0.014687 | 0.00 → 0.00 |
| 90 | late | 7.000 → 10.000 | 5.200 → 9.533 | 0.013450 → 0.014437 | 0.000521 | 0.013450 → 0.014958 | 2.33 → 0.00 |
| 235 | early | 9.533 → 10.000 | 10.000 → 10.000 | 0.004711 → 0.006116 | 0.000000 | 0.004711 → 0.006116 | 0.00 → 0.00 |
| 235 | middle | 9.533 → 10.000 | 10.000 → 10.000 | 0.004737 → 0.006048 | 0.000000 | 0.004737 → 0.006048 | 0.00 → 0.00 |
| 235 | late | 10.000 → 10.000 | 10.000 → 10.000 | 0.004763 → 0.006081 | 0.000000 | 0.004763 → 0.006081 | 0.00 → 0.00 |

## All three strategies by task and stage

| Task | Stage | Arm | TF | PE | Actor USD mean | Update USD once |
|---|---|---|---:|---:|---:|---:|
| 430 | early | no_update | 10.000 | 7.000 | 0.006622 | 0.000000 |
| 430 | early | full_rewrite | 9.933 | 7.333 | 0.009154 | 0.000000 |
| 430 | early | selective_patch | 9.933 | 7.267 | 0.007415 | 0.000000 |
| 430 | middle | no_update | 9.933 | 6.800 | 0.006875 | 0.000000 |
| 430 | middle | full_rewrite | 9.933 | 7.467 | 0.005439 | 0.000818 |
| 430 | middle | selective_patch | 10.000 | 8.200 | 0.006877 | 0.000213 |
| 430 | late | no_update | 9.933 | 5.933 | 0.008422 | 0.000000 |
| 430 | late | full_rewrite | 10.000 | 8.400 | 0.007957 | 0.001072 |
| 430 | late | selective_patch | 9.933 | 8.133 | 0.007015 | 0.000399 |
| 133 | early | no_update | 9.200 | 5.467 | 0.007397 | 0.000000 |
| 133 | early | full_rewrite | 9.400 | 6.333 | 0.006729 | 0.000000 |
| 133 | early | selective_patch | 9.800 | 8.133 | 0.008810 | 0.000000 |
| 133 | middle | no_update | 9.267 | 7.267 | 0.007275 | 0.000000 |
| 133 | middle | full_rewrite | 9.733 | 7.933 | 0.007849 | 0.010113 |
| 133 | middle | selective_patch | 9.867 | 6.600 | 0.009848 | 0.001199 |
| 133 | late | no_update | 9.400 | 4.667 | 0.007240 | 0.000000 |
| 133 | late | full_rewrite | 8.667 | 5.933 | 0.009162 | 0.010748 |
| 133 | late | selective_patch | 9.333 | 7.333 | 0.009985 | 0.002209 |
| 90 | early | no_update | 10.000 | 10.000 | 0.015896 | 0.000000 |
| 90 | early | full_rewrite | 9.933 | 9.800 | 0.014746 | 0.000000 |
| 90 | early | selective_patch | 10.000 | 9.733 | 0.014209 | 0.000000 |
| 90 | middle | no_update | 10.000 | 9.133 | 0.015745 | 0.000000 |
| 90 | middle | full_rewrite | 9.933 | 9.200 | 0.015399 | 0.001803 |
| 90 | middle | selective_patch | 10.000 | 9.800 | 0.014332 | 0.000356 |
| 90 | late | no_update | 7.000 | 5.200 | 0.013450 | 0.000000 |
| 90 | late | full_rewrite | 10.000 | 9.400 | 0.013950 | 0.001983 |
| 90 | late | selective_patch | 10.000 | 9.533 | 0.014437 | 0.000521 |
| 235 | early | no_update | 9.533 | 10.000 | 0.004711 | 0.000000 |
| 235 | early | full_rewrite | 9.933 | 10.000 | 0.004767 | 0.000000 |
| 235 | early | selective_patch | 10.000 | 10.000 | 0.006116 | 0.000000 |
| 235 | middle | no_update | 9.533 | 10.000 | 0.004737 | 0.000000 |
| 235 | middle | full_rewrite | 10.000 | 10.000 | 0.005928 | 0.009726 |
| 235 | middle | selective_patch | 10.000 | 10.000 | 0.006048 | 0.000000 |
| 235 | late | no_update | 10.000 | 10.000 | 0.004763 | 0.000000 |
| 235 | late | full_rewrite | 10.000 | 10.000 | 0.005959 | 0.009920 |
| 235 | late | selective_patch | 10.000 | 10.000 | 0.006081 | 0.000000 |

All cells use unmodified original questions. Official selected-task membership, question SHA256, upstream commit, release archive hashes and source/config hashes are saved in preflight.json and plan.json. Raw receipts include strict DigitalOcean-only routing and provider-reported usage/cost. Unknown costs remain null and stop new requests.

Costs can vary with cache hits and answer lengths. Early and task235 preserve the same underlying catalog/rules, but V3 additionally supplies literal capability-boundary context. They expose evidence-framing cost/quality as well as run variation, not metadata-change recovery alone. Three repeats per cell do not support broad significance claims or a main-merge decision by themselves.

API accounting: {"updater": {"calls": 15, "usd": "0.051080952", "prompt_tokens": 121302, "completion_tokens": 40744}, "agent": {"calls": 405, "usd": "0.964034160", "prompt_tokens": 9656652, "completion_tokens": 225520}, "judge": {"calls": 540, "usd": "0.262590708", "prompt_tokens": 3937181, "completion_tokens": 88509}}. Total actual charged USD: 1.277705820; unknown-charge requests: 0.

See trajectories.csv for every actor execution, summary.json for individual repeats and both ECS conventions, artifact-facts.json for static checks, and answers-*.md for the exact final answers. Static parsing is not execution or a security proof.

## Findings and source checks

Optimized V3 achieved TF 9.906 and PE 8.728 versus No Update 9.483/7.622 and Full Rewrite 9.789/8.483. Its measured cohort deployment cost was 7.86% below Full Rewrite and 9.38% above No Update. V3 updater charges were 89.40% below Full Rewrite, while actor charges were higher than both baselines. V3's literal capability layer is present even in Early/no-change conditions and remains part of actor input. These are finite selected-task results, not a claim that V3 wins every task or significance has been established.

All 108 trajectories were scored. No Update had one empty-answer termination (133-Early-r3); it was retained without rerunning. All 36 V3 and 36 Full Rewrite runs terminated with final answers. Task90 daily-problem source consistency held in 24/27 runs; the three missing observations were all No Update Late. Automatic chart data checks passed 26/27; offline review confirmed the remaining case used the valid Clothing synonym 服饰 and matched all supplied values. The original automatic flag remains in product-checks.json, with separate product-review.json. No rendering or generated-Python functional/security proof is claimed.

All 960 provider receipts were known: 15 updater, 405 actor, 540 judge calls, USD 1.277705820 total. Frozen source/knowledge/evidence, receipt reconciliation, question hashes and pipeline checks passed. See interpretation.zh-CN.md for the readout and main-integration/ for compatibility evidence.

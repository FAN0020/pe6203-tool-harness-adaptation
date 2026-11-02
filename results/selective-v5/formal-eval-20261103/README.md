# V5 formal knowledge-only evaluation

Four selected original MCPEvol-Bench tasks, three environments, No Update vs V5, three independent actor executions per cell. Five official-rubric judge ratings per trajectory. Model repeats have no reproducibility seed. No extra Python execution/repair in either arm. Catalog-only V5; no independent source/probe bundle.

| Arm | Saved / planned | Final answers | TF /10 | PE /10 | Actor USD | Update USD once | Cohort deployment USD |
|---|---:|---:|---:|---:|---:|---:|---:|
| no_update | 36/36 | 36/36 | 9.461 | 7.672 | 0.311551920 | 0.0 | 0.311551920 |
| selective_patch | 36/36 | 36/36 | 9.856 | 8.333 | 0.320856324 | 0.00978264 | 0.330638964 |

Update API charges are counted once per task/environment and reused across its three actor executions. Judge charges are evaluation overhead, excluded from deployment costs. Final-answer termination does not independently certify task completion. TF/PE are model-judged; five ratings are not five independent actor executions.

| Task | Stage | TF NU → V5 | PE NU → V5 | Actor USD NU → V5 | V5 update USD | Single-task USD NU → V5 | Errors NU → V5 |
|---|---|---:|---:|---:|---:|---:|---:|
| 430 | early | 10.000 → 9.800 | 7.267 → 6.600 | 0.006870 → 0.008453 | 0.000000 | 0.006870 → 0.008453 | 0.00 → 1.33 |
| 430 | middle | 9.933 → 10.000 | 7.267 → 7.133 | 0.006596 → 0.006977 | 0.000202 | 0.006596 → 0.007178 | 1.00 → 0.33 |
| 430 | late | 9.800 → 9.867 | 5.667 → 7.933 | 0.007984 → 0.009177 | 0.000358 | 0.007984 → 0.009536 | 2.67 → 0.00 |
| 133 | early | 9.400 → 9.400 | 6.800 → 6.800 | 0.007994 → 0.006686 | 0.000000 | 0.007994 → 0.006686 | 1.00 → 0.33 |
| 133 | middle | 9.133 → 9.533 | 6.000 → 5.733 | 0.008837 → 0.007283 | 0.002316 | 0.008837 → 0.009600 | 0.33 → 1.33 |
| 133 | late | 8.600 → 9.733 | 4.800 → 7.467 | 0.007143 → 0.007246 | 0.006086 | 0.007143 → 0.013332 | 5.67 → 1.00 |
| 90 | early | 10.000 → 10.000 | 9.600 → 9.467 | 0.015742 → 0.015786 | 0.000000 | 0.015742 → 0.015786 | 0.00 → 0.00 |
| 90 | middle | 10.000 → 10.000 | 9.467 → 9.267 | 0.014616 → 0.015217 | 0.000341 | 0.014616 → 0.015558 | 0.00 → 0.00 |
| 90 | late | 6.667 → 10.000 | 5.200 → 9.600 | 0.013824 → 0.015795 | 0.000480 | 0.013824 → 0.016275 | 2.00 → 0.00 |
| 235 | early | 10.000 → 10.000 | 10.000 → 10.000 | 0.004783 → 0.004804 | 0.000000 | 0.004783 → 0.004804 | 0.00 → 0.00 |
| 235 | middle | 10.000 → 10.000 | 10.000 → 10.000 | 0.004723 → 0.004763 | 0.000000 | 0.004723 → 0.004763 | 0.00 → 0.00 |
| 235 | late | 10.000 → 9.933 | 10.000 → 10.000 | 0.004739 → 0.004765 | 0.000000 | 0.004739 → 0.004765 | 0.00 → 0.00 |

All cells use unmodified original questions. Official selected-task membership, question SHA256, upstream commit, release archive hashes and source/config hashes are saved in preflight.json and plan.json. Raw receipts include strict DigitalOcean-only routing and provider-reported usage/cost. Unknown costs remain null and stop new requests.

Costs can vary with cache hits and answer lengths. The Early conditions and task235 have equal knowledge and are controls for variation, not evidence of an update benefit. Three repeats per cell do not support broad significance claims or a main-merge decision by themselves.

API accounting: {"updater": {"calls": 11, "usd": "0.00978264", "prompt_tokens": 36652, "completion_tokens": 4424}, "agent": {"calls": 281, "usd": "0.632408244", "prompt_tokens": 5971733, "completion_tokens": 155435}, "judge": {"calls": 360, "usd": "0.181249860", "prompt_tokens": 2670469, "completion_tokens": 60956}}. Total actual charged USD: 0.823440744; unknown-charge requests: 0.

See trajectories.csv for every actor execution, summary.json for individual repeats and both ECS conventions, artifact-facts.json for static checks, and answers-*.md for the exact final answers. Static parsing is not execution or a security proof.

## Main findings and product checks

V5 raised mean TF by 0.394 and PE by 0.661, with 38 -> 13 tool errors. The measured cohort execution-plus-one-time-update bill was 6.13% higher. Task90 Late gained its missing daily-challenge subtask (TF 6.667 -> 10), while task430 Late made fewer failing calls and scored higher PE (5.667 -> 7.933). These are results for the combined update strategy, not an isolation of the LLM review contribution.

Offline source checks found daily-problem answer/title agreement in all nine V5 task90 runs, versus six of nine No Update runs; the three missing No Update observations were all Late. All 18 runs retrieved the card and image bytes. The global daily endpoint returned 2026-11-02 during this Singapore 2026-11-03 evaluation. All 18 task235 runs matched the requested province, monthly and category/region chart values; browser rendering is untested. Task133 code was not executed and its safety is not established by remote math/template success.

Cache discounts were not controlled. For task90 Late, V5 used 263419 input tokens across three executions versus 417872 for No Update, but cached-input counts were 10368 versus 206080, respectively. Lower total input did not yield a lower actual bill. Cache details are retained in cache-readout.json.

See interpretation.zh-CN.md for the Chinese readout. Protocol/source/receipt consistency checks in verification.json passed. Evaluator control tests: 5 passed. The raw archive and its file manifest preserve full requests, responses, MCP traces, knowledge updates and all judge ratings.

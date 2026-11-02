# V3 — 133 / 235 / 283

This is the current three-task reporting view, aligned to original V6 task IDs. It is derived offline from recorded evaluations; no task has been rerun or relabelled by this view. Original four/five-task studies and negative results remain historical evidence.

| View | Scored / planned | Normal final answers | TF | PE | ECS population |
| --- | --- | --- | ---: | ---: | ---: |
| First attempt | 24/27 | 21/27 | 9.683 | 8.617 | unavailable |
| Once-retry supplement | 27/27 | 22/27 | 9.674 | 8.593 | 9.370 |

First-attempt averages exclude unscored conditions and must be read with the denominator. The retry view includes every valid first-retry score on a previously missing condition, even if its inclusion lowers the mean. It does not conceal or replace the first-attempt failures. Five judge ratings are not five actor executions.

First-attempt update+actor USD 0.263124660; extra retry update+actor USD 0.071007252; combined deployment USD 0.334131912. Judge and local CPU costs are separate.

Sources are pinned to commit `7e4094e4e5fcc9dd3e4f108c3872789b6b6b946a` on the historical evaluation branch: [first cohort](https://github.com/FAN0020/pe6203-tool-harness-adaptation/blob/7e4094e4e5fcc9dd3e4f108c3872789b6b6b946a/evaluation/supplements/five-task-20261103/v35-original-three-20261103/summary.json), [once-retry cohort](https://github.com/FAN0020/pe6203-tool-harness-adaptation/blob/7e4094e4e5fcc9dd3e4f108c3872789b6b6b946a/evaluation/supplements/failed-updates-retry-once-20261103/summary.json). The source JSON hashes are recorded in both views. No later V6 development implementation is imported.

Offline regeneration: `python scripts/build_three_task_views.py`. The pinned source commit must be available locally (fetch the historical evaluation branch if necessary).

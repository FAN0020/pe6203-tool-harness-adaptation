# V3 — 133 / 235 / 283

This is the current three-task reporting view, aligned to original V6 task IDs. It is derived offline from recorded evaluations; no task has been rerun or relabelled by this view. Original four/five-task studies and negative results remain historical evidence.

| Scored / planned | Normal final answers | TF | PE | ECS population |
| --- | --- | ---: | ---: | ---: |
| 27/27 | 22/27 | 9.674 | 8.593 | 9.370 |

Method: this summary includes one retry of failed knowledge updates and every valid resulting actor score. It is a post hoc supplement, with three actor repeats per task/stage; five judge ratings are not five actor executions. Providers, repeat counts and artifact protocols differ from historical V6, so this is a descriptive comparison.

Actual update+actor cost, including failed attempts and retries: USD 0.334131912. Judge and local CPU costs are separate.

The displayed metrics come from [one-retry.json](one-retry.json). The [first-attempt record](first-attempt.json) is retained for audit, without a second headline table.

Sources are pinned to commit `7e4094e4e5fcc9dd3e4f108c3872789b6b6b946a` on the historical evaluation branch: [first cohort](https://github.com/FAN0020/pe6203-tool-harness-adaptation/blob/7e4094e4e5fcc9dd3e4f108c3872789b6b6b946a/evaluation/supplements/five-task-20261103/v35-original-three-20261103/summary.json), [once-retry cohort](https://github.com/FAN0020/pe6203-tool-harness-adaptation/blob/7e4094e4e5fcc9dd3e4f108c3872789b6b6b946a/evaluation/supplements/failed-updates-retry-once-20261103/summary.json). The source JSON hashes are recorded in both views. No later V6 development implementation is imported.

Offline regeneration: `python scripts/build_three_task_views.py`. The pinned source commit must be available locally (fetch the historical evaluation branch if necessary).

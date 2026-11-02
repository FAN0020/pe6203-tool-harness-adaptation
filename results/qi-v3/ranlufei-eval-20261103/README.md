# QI-V3 three-strategy evaluation — 2026-11-03

Historical result: these runs predate the 2026-11-03 program-first input
optimization. They are not scores for the optimized V3 updater. See
`results/qi-v3/scope-input-20261103/` for the new updater diagnostics.

## Scope

- Branch/implementation: `QI-V3`, selective strategy mode `hybrid_v3`.
- Tasks: 133, 235, and 283; stages: `early`, `middle`, and `late`.
- Strategies: `no_update`, `full_rewrite`, and `selective_patch`.
- One frozen repeat (`seed=0`): 27 planned task-stage-strategy cells and five judge records per scored trajectory.
- Frozen plan SHA-256: `3675f624844b9d129aea0ecc900185034f318ade2265ba7d321cb0631ef24408`.

## Delivery status

| Item | Result |
| --- | ---: |
| Planned cells | 27 |
| Cells with TF/PE scores | 22 |
| Fully completed executions | 12 |
| Complete three-strategy comparison groups | 5 |
| Blocked / cancelled / adaptation failed | 2 / 2 / 1 |

The incomplete cells are retained in the run ledger and **excluded from matched-strategy comparisons**. This is a partial V3 result, not a complete benchmark leaderboard.

## Matched three-strategy results

Only task-stage groups with all three scored strategies are reported below.

| Task | Stage | No Update (TF / PE) | Full Rewrite (TF / PE) | Selective Patch (TF / PE) |
| ---: | --- | --- | --- | --- |
| 133 | early | 10.0 / 6.0 | 10.0 / 5.6 | 9.8 / 6.0 |
| 133 | middle | 9.8 / 6.6 | 10.0 / 6.4 | 10.0 / 7.4 |
| 235 | early | 10.0 / 10.0 | 10.0 / 10.0 | 10.0 / 10.0 |
| 283 | early | 10.0 / 9.0 | 10.0 / 7.2 | 10.0 / 9.0 |
| 283 | late | 10.0 / 7.0 | 10.0 / 9.0 | 10.0 / 7.4 |

The middle-stage evidence is currently one matched task only; the late-stage evidence is also one matched task only. Do not infer an overall strategy ranking from these small, partially completed groups.

## Incomplete-cell handling

- `task133 / late / no_update`: cancelled during external runner progress stall.
- `task133 / late / full_rewrite`: adaptation failed before execution.
- `task235 / middle, late / selective_patch`: blocked before execution.
- `task283 / middle / selective_patch`: cancelled during external runner progress stall.

No scores were invented for these cells. Where update/agent calls had already consumed tokens, their recorded cost evidence is preserved in the raw ledger.

## Reproducibility and local evidence

Raw outputs, judge records, evidence snapshots, costs, and the full ledger are retained locally under:

`results/raw/ranlufei-qi-v3-three-strategy-20261103/`

The raw-summary SHA-256 is `14b595f52b12d20232fe443f99b73a861949aeffb75b94633305f7a88ff3739e`.

This repository delivery intentionally excludes raw model logs and credentials. The aggregate CSV and JSON below contain only task IDs, statuses, TF/PE values, and non-secret accounting fields.

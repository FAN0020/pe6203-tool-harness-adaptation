# QI-V2 benchmark results · 2026-11-01

This is the preserved result upload for the QI-V2 comparison prepared on `V2-eval`, with QI-V2 pinned to `bdf0ccc5c3466517725c84e7f715234733cde4a8`. It is a separate experiment from the later selective-adaptation research cohorts.

**Incomplete: 25 of 27 planned executions have official scores (125 valid judge slots); 19 executions completed normally.** Two cells failed during adaptation and never started the actor:

- `task133-middle-full_rewrite-r0`
- `task283-late-selective_patch-r0`

| Method | Normally completed / planned | Scored / planned |
|---|---:|---:|
| No Update | 7/9 | 9/9 |
| Full Rewrite | 6/9 | 8/9 |
| QI-V2 Selective Patch | 6/9 | 8/9 |

Missing scores remain null. Normal completion and official TF/PE do not certify complete product correctness. The original artifact review status and unknown costs are preserved. This upload does not rerun any experiment, establish a winner, or claim the research Goal is complete.

## Read the results

- [Original quick report](v2-eval/README.md), [summary](v2-eval/summary.json), and [per-run CSV](v2-eval/runs.csv).
- [27 case reports](v2-eval/cases/): original questions, answers, tool observations, and workspace hashes.
- [Analysis](analysis/): matched comparisons, ECS, recovery/retention, exclusions, and costs.
- [Frozen plan](plan.json) and [execution state](experiment.json).
- [Verification](verification.json), [duplicate check](duplicate-check.json), and [file manifest](manifest.json).

## Full original evidence

[raw-results.tar.gz](raw-results.tar.gz) is a byte-identical copy of the supplied `results/v2-eval-results.tar.gz`. It contains all **1067 files**, **71,802,168 uncompressed bytes**, from the supplied `results/v2-eval-20261101/` directory. Every relative path and SHA-256 matched before upload. The original directory and original archive were left unchanged.

Archive size: 10,414,333 bytes. SHA-256:

```text
c36e88370426d1aedcf5368b1bf2881bcbce8e259b532c14eac3804d8b920f22
```

The readable report files intentionally duplicate selected members of this archive; raw trajectories are stored once in compressed form. The prior remote `V2-eval` head `f90dbd57a58c28cd3f84454e0eddd38ef0acdca6` contained preparation materials, not these result summaries or this archive.

Verify with Python 3, without model calls:

```bash
python3 results/evidence/v2-eval-20261101/verify.py
```

Verification checks every archived file, every published result copy, and recomputes TF/PE from all 125 original judge slots. It does not independently re-judge products or resolve unknown charges.

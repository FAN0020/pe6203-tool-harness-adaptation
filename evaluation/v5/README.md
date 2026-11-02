# evaluation 5 — current tasks 133 / 235 / 283

Start with the [three-task aligned view](three-task-view/README.md), covering
the same task IDs as original V6. First attempts and the post hoc once-retry
supplement are separate. All valid retry scores and all incurred costs remain
included, even when the mean decreases. The active three-task evaluator is
`scripts/eval_v35_three_tasks.py`; the four-task scripts below are frozen
historical reproduction tools, not the current reporting scope.

## Historical studies (retained unchanged)

This package separates the original a97a599 V5 experiment from the later scoped
V5 knowledge-only experiment. It does not replace either result with the other.
The original paired-driver source remains provenance; current V3 and V5 results
are published separately and must not be inferred from that older driver alone.

- `code/scripts/eval_v5_formal.py`: later four-task × three-stage × two-arm ×
  three-repeat study (72 trajectories). Explicit --execute required for paid runs.
- `code/scripts/analyze_v5_formal.py`, `audit_v5_products.py`, `verify_v5_formal.py`:
  offline result, cost, artifact-fact and protocol checks.
- `code/scripts/measure_v5_scope.py`: before/after input diagnostic; scripted by
  default, --live is a separate paid opt-in. It is not an Evol actor benchmark.
- `recorded-72/`: full recorded results, 652 receipts and raw archive. No code
  execution/security certification was added to these knowledge-only arms.
- `historical-r2-code/`: byte-identical original local driver, preparation, cost
  and verification code. It retains old local paths and old paired-arm names.
  Its V5 result had 5/9 scored cells and four updater failures. These scores
  do not describe the later optimized V5.
- Runtime source archives bind both code revisions; no current main method is overwritten.

```sh
python evaluation/manage.py verify --version 5
python evaluation/manage.py extract --version 5 --artifact runtime --output outputs/evaluation5-source
python evaluation/manage.py extract --version 5 --artifact recorded-72 --output outputs/evaluation5-raw
# After extraction, use the raw archive's root directory for --input:
python evaluation/v5/code/scripts/verify_v5_formal.py --root outputs/evaluation5-source --input RAW_ROOT --output outputs/evaluation5-verification.json
```

Online execution requires MCPEvol services, the frozen runtime and private
OPENROUTER_API_KEY configuration. Do not run the evaluator against main's newer
source while claiming to reproduce a historical pinned implementation.

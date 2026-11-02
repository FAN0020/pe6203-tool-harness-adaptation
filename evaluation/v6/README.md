# evaluation 6

Exact code and evidence for the gated V6 experiment: offline catalog/input
checks → Task 133/Late pilot → remaining eight conditions. Execution source
8401df2 is frozen. Nine adaptations and ratings completed; seven executions
completed normally. Math Middle had no accepted code artifact; project Late
reached max rounds. Those failures remain in official recorded results.

`code/scripts/` publishes the evaluation, cost/integrity summarizer and offline
packing acceptance tool byte-for-byte. `recorded-results/` includes every source
snapshot, request/response, cost receipt, trajectory and diagnostic attempt in
the original archives. r1–r3 diagnostics are not pooled with final r4 scores.
Any V3 comparisons inside the historical report are old archived values, not
an evaluation or acceptance of the current unavailable V3.

```sh
python evaluation/manage.py verify --version 6
python evaluation/manage.py extract --version 6 --artifact formal-r4 --output outputs/evaluation6-raw
# Pure offline recomputation, no key required:
python evaluation/v6/code/scripts/summarize_v6.py --run outputs/evaluation6-raw/r4
python evaluation/manage.py extract --version 6 --artifact runtime --output outputs/evaluation6-source
```

The online evaluator takes --plan and --env-file explicitly, verifies source
and input hashes, reserves money before calls, and refuses an already-started
output run. Its historical env alias V5_API_KEY is just a private variable name.
No private env file or API Key is included. New paid runs require a newly frozen
plan/output directory and matching pinned runtime; never edit a recorded plan
or its acceptance criteria to resume a failed trajectory.

## Additional Math Middle execution

See [the separate repeat record](repeats/math-middle-20261103-01/README.md).
The same frozen knowledge yielded TF/PE 10/10 with two tool calls. Original
r4 scores are retained, and no sufficiency gate was introduced.

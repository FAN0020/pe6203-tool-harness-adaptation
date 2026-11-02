# V6 Task 133 / Middle — one additional execution

The owner requested one independent rerun. Knowledge, adaptation, execution
configuration, model/provider, budgets and independent artifact tests were
reused from formal r4. There was no updater call and no new information-
sufficiency gate. A fresh workspace path was the only difference in the first
actor request after path normalization.

| Execution | TF | PE | Tool calls | Result |
| --- | ---: | ---: | ---: | --- |
| Original r4 | 3.4 | 1.6 | 35 | No accepted code artifact |
| Additional actor execution | 10 | 10 | 2 | Completed; finite isolated code tests passed |

The repeat used two actor rounds, zero repair calls and five judge ratings.
The seven new API requests cost USD 0.004075700, including agent USD 0.003148565
and judge USD 0.000927135. Reused knowledge incurred no new update charge.
Native runner metadata still carries the original one-time update allocation
of USD 0.001623510; it must not be counted as a new bill.

The original nine-cell result is unchanged. Two executions show different
execution paths under the same frozen knowledge; they do not establish stable
performance or a causal benefit from a sufficiency gate. Passing finite tests
is not a complete security proof.

`run_repeat.py` is the execution-only adapter around the original 8401df2
audited evaluator. It takes --plan and --env-file explicitly and requires the
frozen source hashes; do not run it against a different active runtime while
claiming exact reproduction. `raw-repeat.tar.gz` retains source snapshots,
original adaptation, all seven requests/responses, trajectory and artifact tests.
`repeat-summary.json` contains the exact equality, cost and score checks.

## Later display-selection request

The owner subsequently requested using this repeat in the current nine-cell
summary. See [the current report](../../recorded-results/REPORT.md). The
original r4 raw records remain unchanged; the current display is explicitly
marked as selected after observing the repeat, with all incurred fees retained.

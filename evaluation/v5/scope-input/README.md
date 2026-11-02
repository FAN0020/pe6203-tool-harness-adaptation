# V5 program-first scope: input acceptance, 3 November 2026

**Input reduction is established on the recorded bounded diagnostics. Benchmark effectiveness and complete semantic recall are not established.**

## Implemented workflow

Program metadata synchronization and classification -> one lightweight candidate screen -> candidate union/deduplication -> one detailed local decision+edit per candidate -> existing evidence/schema/preservation gates.

Program-complete records are not reclassified by the LLM. Explicit referring rules and independent evidence hosts become program semantic seeds. The screen sees descriptions/rules and exact change views; it proposes only potential impact or uncertainty. Selected records have a combined keep/update/unresolved and local-edit response. Immutable fields remain program-owned. Unresolved rules are withdrawn and marked unknown. There is no repeated scope-expansion loop.

## Real same-model diagnostic

Model: deepseek/deepseek-v4.1-flash-1017; DigitalOcean only, temperature 0, no fallback/retries; synthetic task-free catalogs. All requests/usage/responses are retained.

- Complete 3-record pair: **17,632 -> 1,294 input tokens (-92.66%)**. Both arms detected the known consumer impact, removed its stale direct-pass rule and preserved unrelated rules and exact metadata. Calls remained 2 -> 2; the benefit here is smaller inputs, not fewer requests. Reported updater charges: USD0.002721984 -> USD0.000275832; this single observation includes provider/cache pricing and is not a universal cost estimate.
- Program-only parameter case: original V5 used 2 calls / 9,975 input tokens; revised V5 used **0 calls / 0 input tokens** while synchronizing the exact required schema.
- 42-record revised V5: **2 calls / 3,361 input tokens**, one implicit consumer found and reviewed. The old V5 failed source-coverage admission after 3 requests / 86,856 input tokens. This is a retained failed baseline, **not a complete paired reduction percentage**. The new result is an explicit conflict warning/withdrawal, not a verified conversion implementation.
- The old run is not resampled. `live-after-continuation/freeze.json` verifies that the new arm used the identical previously frozen 42-record inputs. The additional small complete pair was declared separately after that failure; it is diagnostic, not a replacement for the failed large pair.
- The original new-large acceptance checker wrongly treated the phrase “without conversion” inside a warning against that behavior as retaining the old rule. `offline-review.json` records the correction to exact retained-rule entries and manual reading of the warning. Raw measure/failure/response files remain unchanged; no model was rerun. Tests cover both warning quotations and actually retained stale entries.

Total real updater calls: **11**; known USD **0.022456632**; unknown charges **0**. No benchmark actor/judge call was made.

## Controlled scripted payload comparison

These use fixed replies and **tiktoken 0.14.0 / o200k_base as a proxy**, not the DeepSeek tokenizer or semantic-quality evidence. Original and revised outputs have identical knowledge hashes in each scripted pair.

| Frozen case | Before proxy tokens | After proxy tokens | Reduction | Requests |
|---|---:|---:|---:|---:|
| program_only_1 | 4,677 | 0 | 100.0% | 1 → 0 |
| implicit_3 | 19,295 | 1,217 | 93.7% | 2 → 2 |
| implicit_12 | 57,934 | 1,658 | 97.1% | 3 → 2 |
| implicit_42 | 208,381 | 3,128 | 98.5% | 8 → 2 |
| explicit_42 | 208,367 | 3,131 | 98.5% | 8 → 2 |

The fixtures deliberately include irrelevant schema fields to expose duplication. The percentages characterize these fixtures, not all real tool catalogs. `scripted-final/freeze.json` pins source and input hashes.

## Raw evidence packaging

All original requests, responses, frozen cases, audits, knowledge and failed-run
outputs are retained byte-for-byte in `raw-measurements.tar.gz`. Its complete
file hashes were verified before packaging; see `raw-manifest.json`. Small
summaries/freezes/measures remain directly browsable. To inspect every path
mentioned below, extract into this directory:

```sh
tar -xzf raw-measurements.tar.gz
```

The extra local unpacked copy lives under ignored `results/raw/`; it is not a
replacement for the committed, verified archive.

## Checks and reproduction

Protected V1/V2 updater, rule/evidence admission, baseline updater, actor, judge, Docker checker and course config are byte-identical to the baseline; hashes are in acceptance-summary.json. Existing acceptance-summary.json and old experiment archives elsewhere are preserved. Current test results are in tests-final.xml. The public CLI plus actual Docker functional-failure -> scripted SDK repair -> isolated retest passes in local-acceptance/acceptance.json. Scripted HTTP replies are not real LLM results.

Offline input comparison (new output directory required):

```sh
uv run --with tiktoken==0.14.0 python scripts/measure_v5_scope.py --output results/raw/v5-scope-input-new
```

**Do not rerun the archived live runs.** The optional `--live` entry makes real paid updater requests only after freezing inputs; existing output directories are rejected and failed/unknown requests stop without automatic retries. No key is stored in evidence. The archived baseline source must be available at commit a97a599790f076b6a48c2e023a7d538e196322f3.

## Remaining uncertainty

The screen may fail to nominate an implicit dependency, and a well-formed rule can still be semantically wrong. Receipt/ID/schema checks cannot prove semantic completeness. No silent token truncation, discarded candidates or mock model token counts are presented as live savings. Formal task completion, retention, output quality and total deployment cost still need the separate frozen V5 evaluation.

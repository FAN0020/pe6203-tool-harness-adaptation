# V3 program-first updater acceptance — 2026-11-03

Baseline: `selective-V3` at `b94d51226324e3eac70e5fe873a5be51e9cd8df1`.
The public mode remains `hybrid_v3`; its new core is
`hybrid_v3_program_first_v1`, scope policy
`program_first_light_screen_local_review_v1`.

## Design change

Program metadata synchronization -> program-complete records and explicit
semantic seeds -> one lightweight directory screen -> deduplicated candidates
-> one local review/edit per candidate -> existing quote/field/argument gates
-> unchanged literal capability-evidence enrichment -> frozen knowledge.

The repeated global knowledge index and old/target/patched triple-record payload
are removed. Exact changed leaves and relevant source views replace full schemas.
Program-complete metadata-only records do not enter detailed LLM review. The
light directory contains descriptions and stored rules. Missing/duplicate IDs,
coverage gaps, invented quotes, metadata edits and budget overflow fail closed;
there is no silent truncation, model-chosen scope loop or V1 fallback. An
unresolved local review still rejects the update under V3's original policy.

V2, deterministic V1, No Update, Full Rewrite, the actor/judge, model budgets,
and Python validation/repair code remain byte-identical to the baseline.
`enrich`, `fingerprint` and `load_evidence` retain identical ASTs.
The V3 adaptation wrapper also fixes a pre-existing no-change artifact bug:
`target_stage` records the requested environment while the reused knowledge
envelope may remain Early K0. Three stage-specific regressions verify zero
updater calls and preserved rules. This wrapper fix followed the input
measurements; the measured core functions are unchanged, and their original
capability source snapshot is retained as `engine-capability-frozen.py`. Source/probe
capability evidence is not sent to the semantic LLM. This preserves V3's literal
boundary design instead of importing V5's different typed-rule/unknown policy.

## Same-provider real updater input measurements

These are task-free synthetic catalogs, not benchmark task executions. Both
engines see the same frozen old/current catalogs and capability evidence. Fixed
model `deepseek/deepseek-v4.1-flash-1017`, DigitalOcean only, temperature 0,
16384 output limit, SDK retries 0, no provider fallback.

| Fixture | Calls old -> new | Provider input tokens old -> new | Input reduction | Actual updater USD old -> new |
|---|---:|---:|---:|---:|
| One program-only required-parameter change | 2 -> 0 | 4717 -> 0 | 100% | 0.001117620 -> 0 |
| 3 records, implicit unit dependency | 2 -> 2 | 7317 -> 1027 | 85.96% | 0.001628196 -> 0.000411660 |
| 42 records, implicit unit dependency | 8 -> 2 | 84670 -> 3055 | 96.39% | 0.012588264 -> 0.000862572 |

All 16 real updater calls are retained. Actual total cost: USD 0.016608312;
unknown charges: 0. The changed metadata, schemas/routes, unrelated rules and
literal capability boundaries passed checks. Observed before/after unit rules
were separately reviewed for this finite cents-to-dollars fixture. Exact quote
checks establish provenance, not general semantic entailment.

Scripted 1/3/12/42-record cases produced byte-equivalent knowledge envelopes.
Their exact input-character reductions were 100%, 85.85%, 92.92%, and 96.40%.
Scripted character/byte counts are not claimed as provider token measurements.

## Retained checker correction

Original real-request `summary.json` files retain the initial failed checker
outcomes. The checker mistakenly treated the changed source as an unrelated
record (the old engine redundantly documented its new schema as rules), and
required the numeral `100` even when the model explicitly said to convert cents
to dollars. Neither was an engine validation failure. The original measurement
script is saved as `measurement-script-frozen.py` and matches its freeze hash.

`offline-review.json` records the correction against the exact existing output
bytes, preserving the original checks and summary hashes. Regression cases
accept observed conversion wording, reject reverse conversion/unchanged values,
and reject retention of the obsolete direct-pass rule. No model request was
rerun for the correction. The updated checker is still a bounded fixture check,
not a general semantic proof.

## Regression and isolation

- 430 passed, 9 skipped, 13 native-MCP integration tests deselected.
- Actual configured Docker tests ran with an already installed pinned Python image.
- The public changed-metadata V3 CLI was exercised through a scripted local API.
- `local-acceptance/` additionally exercised public V3 CLI + runner -> actual
  Docker functional failure -> scripted repair -> actual isolated retest pass.
  These local HTTP replies are test doubles, not paid model effectiveness data.
- Protected source checks and frozen engine-source identities passed.

## Scope and reproduction

The existing 22/27 scored V3 benchmark records predate this optimization. They
remain unchanged and must not be relabelled as optimized-V3 scores. No task
actor/judge was run here. These measurements demonstrate input reduction on
finite fixtures, not full benchmark performance or end-to-end cost savings.
A lightweight screen can miss implicit dependencies. Evidence hashes/quotes do
not establish authenticity, entailment or complete security.

Run `uv run pytest -m 'not integration'` for local regressions. Actual Docker
cases additionally need `PE6203_ARTIFACT_IMAGE` set to an already reviewed local
pinned image and the Docker CLI on PATH. No runtime installation or image pull
is performed by the tests.

`uv run python scripts/measure_v3_scope.py --output results/raw/v3-new` measures
scripted inputs. `--live` opts into real paid updater calls using
`OPENROUTER_API_KEY`, a USD 0.50 known-charge guard and no retries. Always use a
fresh output directory. `--review-saved <directory>` rechecks archived bytes
without model calls. Select `--selective-mode hybrid_v3` for the updated public
CLI; the historical default remains V2.

Raw requests/responses, source snapshots, original and corrected checks,
scripted fixtures and Docker evidence are in `raw-measurements.tar.gz` with
`raw-manifest.json`. API credential values were scanned before publication.

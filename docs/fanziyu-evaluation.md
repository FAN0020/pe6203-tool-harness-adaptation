# Evaluation handoff — Fan Ziyu

This contribution connects the evaluation package shared on 21 October to the current repository. It provides an offline evaluator, a reproducible audit of the published development evidence, and an evidence-based failure review. No new model experiment was run for this handoff.

The [group allocation](https://docs.google.com/document/d/1fbhITsq__0Xaxjp85qVaQxIO1kQS6oDF-RFe7G7G5kQ/edit) assigns Fan Ziyu to Evaluation in Sprints 1–2 and Performance, Cost and Failure Analysis with Xiao Xiaohua in Sprint 3. Baseline implementation and Selective Patch integration belong to the corresponding method owners.

## What is ready

- `pe6203.evaluation`: TF/PE verification, matched three-strategy tables, ECS, recovery/retention, change-type breakdowns, exclusions and unique adaptation costs.
- `pe6203.evidence_audit`: hash-checked historical evidence inspection, individual judge records, recorded costs and unclassified tool errors. This command never produces formal strategy rankings.
- [Pilot analysis](../reports/fanziyu-pilot-analysis-20261027.md): the actual observations and remaining evidence requirements.
- [Saved audit outputs](../results/evaluation/fanziyu-pilot-audit-20261027/summary.json): machine-readable results, with CSV tables alongside them.
- [Input templates](../experiments/evaluation/): task review, run ledger, analysis manifest, human judge review and failure-case worksheets.

The original Drive package remains available in [04_Evaluation_Fanziyu](https://drive.google.com/drive/folders/1AMTNnCp9gI9tUvlWRBYlRZnPrsj3iSJn). Its earlier statement that real scoring was unavailable is superseded by this audit of the newly published evidence.

## Reproduce the evidence audit

From a checkout containing this contribution:

```bash
uv sync --frozen
uv run python -m pe6203.evidence_audit \
  --manifest experiments/evaluation/pilot-evidence.json \
  --output results/local-fanziyu-audit
uv run pytest -q tests/test_evaluation.py tests/test_evaluation_integration.py
```

Use a new output directory for each run. The audit refuses changed source hashes and does not overwrite existing output directories. It needs no API key or running MCP server.

The seven entries are an explicit evidence inventory, not a formal experiment manifest. They include two summaries for which raw judge records are not available in the selected published files. Four entries have five valid preserved judge records whose means agree with their saved TF/PE. Only the `result_eval` entry also contains the raw model responses inside its EVAL file. A verified mean is not proof that the judge's assessment is correct.

## Formal analysis after the team freezes the experiment

Copy `experiments/evaluation/analysis-manifest.json` and `run-ledger.json` into a new experiment directory. These templates deliberately remain unfrozen and empty. Complete them from the agreed task reviews and actual execution outputs; do not set `frozen` merely to make a command run.

The manifest records the experiment ID, benchmark and dataset revisions, repeat IDs, and task-level transition labels. Set `comparison_config_path` relative to the manifest file and record its **byte SHA-256**. Every formal task needs review evidence. Tasks 139 and 223 are reserved for development; add any further tuned tasks to `development_reserved_ids` before analysis.

Each ledger entry identifies one task × stage × strategy × repeat × attempt. Paths are relative to the ledger, and every result/EVAL file needs its byte SHA-256. Copy the runner's `config_sha256` into `expected_config_sha256`; do not confuse it with a file hash. This digest uses the runner's `json.dumps(config, sort_keys=True)` representation. Formal records must preserve the original config so that the digest can be recomputed. Historical `<REPO>` path-redacted bundles belong in the pilot audit, not in the formal loader.

| Runner field/file | Analysis use |
| --- | --- |
| `result.task_id`, `version`, `strategy`, `seed` | Ledger task, stage, strategy and repeat identity |
| `status`, `execution_status`, `judge_status` | Separate execution failure from grading completion |
| `EVAL/<task_id>.json` | Five raw judge records, exact unrounded TF/PE and aggregate checks |
| `config_sha256`, `protocol_sha256` | Per-run config verification and within-cell protocol agreement |
| `benchmark_commit`, `dataset_revision` | Prevent mixing benchmark releases |
| `cost.agent`, `cost.judge` | Preserve all-attempt execution and judge costs |
| Adaptation artifact and its cost | One ledger update record per actual artifact, reused by ID |

Use the same `comparison_config_file_sha256` on the manifest and all ledger entries. Review actual prompts, settings, fixtures and knowledge provenance before freezing: a matching identifier alone cannot establish a fair experiment. In particular, review differences between stages as well as within-stage protocol hashes.

Retain every failed attempt. Select at most one attempt per cell under the frozen retry rule, and document any extra attempt in `retry_evidence`. Do not select the highest score. Incomplete, blocked and missing runs remain visible; valid low scores and `max_rounds` runs with complete scoring remain included in eligible scored cells.

```bash
uv run python -m pe6203.evaluation \
  --manifest PATH/analysis-manifest.json \
  --ledger PATH/run-ledger.json \
  --output results/NEW_FORMAL_ANALYSIS
```

The `--demo` option accepts only manifests explicitly marked `synthetic_software_test`; it is for software checks. It is not a way to admit development runs as formal evidence.

## Metric definitions

For each stage, use task/repeat cells with complete scores for all three strategies. Average matched repeats within a task, then give tasks equal weight. Report the planned and matched counts beside means. Missing scores remain null.

ECS requires Early, Middle and Late for every strategy in the same task/repeat. The primary calculation is the mean of the three TF values minus their population SD, matching the pinned upstream implementation. The existing team protocol's sample-SD sensitivity is returned separately as `paper_sample`; it is not mixed into the primary table.

Recovery is the paired TF difference from No Update on changed tasks at the same target stage. Retention reports that difference on unaffected tasks and, when a matched Early cell exists, the difference from Early No Update. Uncertain transition labels are excluded from those subgroup analyses. TOOL/PARAM/DESC labels may overlap and are not additive sample counts.

For costs, the formal ledger counts each adaptation artifact once, including failed updates. Link each target-stage attempt to its artifact ID. Normalize the runner's `total_tokens` or legacy `tokens` to the update ledger's `tokens`. Preserve unknown values as null, use explicit zeros for No Update, and provide a pricing/invoice source for nonzero USD. Keep agent, judge and update costs separate. The formal evaluator also exports `execution_cost.csv`, including unselected and failed attempts, with known subtotals and missing-value counts. The historical audit reports recorded per-run costs without assuming cross-run update reuse or inventing a project-wide total.

## Judge and failure review

Use `judge_human_review.csv` for independent human TF/PE ratings on a stratified pilot sample. The current audit does not fill human scores. Review disagreements, then have a second person check any case used in the presentation. Five ratings of one trajectory are repeated judge measurements, not five agent runs.

For under-update, show the changed task-relevant rule, the omitted/misrepresented knowledge and the failing call. For over-update, show an unnecessary or incorrect knowledge change and a supported regression relative to a baseline or controlled correction. Preserve old/target/applied knowledge and full traces. A missing argument, low TF or Full Rewrite failure alone does not establish either mechanism.

## Next inputs and owners

| Owner | Required next input | Completion check |
| --- | --- | --- |
| Integration and C | Selective Patch in the common `adapt`/runner path | Same tasks, fixtures, agent and judge; no silent full rewrite fallback |
| A and D | Reviewed independent task subset and transition labels | Early/Middle/Late plus TOOL/PARAM/DESC and unaffected-task coverage |
| A/B/C | Frozen three-strategy pilot and adaptation artifacts | Result, EVAL, ANSWER, trace, config, knowledge and all attempt costs |
| Fan Ziyu and evaluation teammates | Human judge cross-checks | Actual reviewer names, scores and discrepancy notes |
| Fan Ziyu and Xiao Xiaohua | Under-/over-update causal cases | At least one supported trajectory of each type; currently unmet |

Current `main` already dispatches Full Rewrite to the LLM implementation; repeating the screenshot's original integration change is unnecessary. `experiments/protocol.v1.json` still has older implementation/updater status strings, while README and `docs/common-llm-baselines.md` describe the new entry point. Reconcile those planning records at the team freeze. The existence of C's branch does not establish integration on `main`.

## 给范子钰的使用说明

这次可以交的是：已接入仓库的评估程序、真实开发日志核对表、成本明细、评分分歧和失败候选分析。不能说三种策略的正式实验已经完成。

向组员说明进度时，可以直接指向本文件和 pilot analysis。接下来需要的不是再写一份空协议，而是统一 runner 的三策略实际输出、冻结任务清单，以及组内人工复核。收到这些文件后，按上面的输入格式生成最终表。PR 由组内 owner 审核后合并。

## Validation receipt

At this snapshot, lint and formatting checks pass. The non-integration suite reports 194 passed and 9 skipped; 10 integration-marked tests were deselected. The 39 evaluation/audit tests include real published fixtures. The skips are recorded in [validation.json](../results/evaluation/fanziyu-pilot-audit-20261027/validation.json); they are not evidence of successful live MCP execution.

The primary ECS function also agrees exactly with the pinned upstream implementation on all 1,000 integer triplets in the 1–10 range. Reproduce with:

```bash
uv run python scripts/check_evaluation_ecs.py \
  --upstream-file .cache/mcpevol/upstream/src/custom/analysis/answer/evolutionary_volatility.py \
  --output results/NEW_ecs_parity.json
```

This command requires the pinned upstream source file, validates its byte hash and makes no model call.

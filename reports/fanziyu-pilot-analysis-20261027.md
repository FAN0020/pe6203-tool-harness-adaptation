# Development evidence review — 27 October 2026

**Fan Ziyu — Evaluation / Performance, Cost and Failure Analysis**

The repository contains real development evidence, but no complete frozen three-strategy comparison. This review rechecks the published records at commit `d143cecb331d4933dc4b19a0937cadaba6d1fab1`. It does not rerun the model, change any score, or treat development tasks as held-out evaluation.

## Evidence inventory

All entries below concern task 139. “Verified” means that five preserved judge records produce the saved TF/PE means. It does not mean that execution completed or that a human endorsed the scores.

| Record | Stage / strategy | Reported TF | Reported PE | Execution | Score evidence |
| --- | --- | ---: | ---: | --- | --- |
| Initial integration | Early / No Update | — | — | completed | Judge incomplete; excluded |
| Integration v2 | Early / No Update | 9.8 | 8.6 | completed | Verified from preserved judge scores |
| Middle A | Middle / No Update | 9.4 | 5.0 | max_rounds | Summary only |
| Middle A | Middle / Full Rewrite | 8.4 | 7.0 | max_rounds | Verified from EVAL, including raw responses |
| Middle B | Middle / No Update | 8.2 | 7.0 | max_rounds | Verified from preserved judge scores |
| Middle B | Middle / Full Rewrite | 9.0 | 7.2 | max_rounds | Verified from preserved judge scores |
| Vanilla smoke | Early / current_metadata_smoke | 10.0 | 9.8 | completed | Summary only; not a strategy baseline |

Middle A is `baseline-pilot-20261019T125817848890Z`; Middle B is `xiaohua-cli-middle-20261019`. They are separate development batches. The B pair shares its recorded protocol hash, but neither batch supplies the full matrix. The opposite directions of the two reported TF differences are a reason to avoid a strategy-ranking claim, not to select the more favorable batch. Do not combine the smoke score with either batch to create ECS inputs.

The [audit manifest](../experiments/evaluation/pilot-evidence.json) records exact source paths and hashes. [runs.csv](../results/evaluation/fanziyu-pilot-audit-20261027/runs.csv) separates reported from verified values. All seven entries remain ineligible for formal tables.

## Costs observed in the records

These are saved token counts, not newly incurred API costs. The audit checks the source files and field formats; it does not independently reconstruct every provider response in every bundle.

| Attempt | Update tokens | Update seconds | Agent tokens | Judge tokens |
| --- | ---: | ---: | ---: | ---: |
| Middle A / No Update (summary) | 0 | 0 | 211,522 | 51,543 |
| Middle A / Full Rewrite | 18,831 | 10.555 | 250,812 | 69,653 |
| Middle B / No Update | 0 | 0 | 223,643 | 62,196 |
| Middle B / Full Rewrite | 17,928 | 9.791 | 264,811 | 84,525 |

The initial Early attempt also incurred 141,122 agent tokens and 83,406 judge tokens despite incomplete scoring. Excluding its scores must not erase its costs. USD remains unknown where the historical record reports null. No project-wide total is reported because shared update identities and all historical attempts have not been established. All seven records and the three cost roles appear in [recorded_costs.csv](../results/evaluation/fanziyu-pilot-audit-20261027/recorded_costs.csv).

## Judge consistency and review targets

Integration v2 has TF scores `[10, 10, 10, 10, 9]` and PE scores `[10, 9, 9, 9, 6]`. The PE mean is 8.6 and sample SD is approximately 1.517. One judge treated separate dependency-update calls as substantial avoidable work; others treated them as necessary steps. This is disagreement about planning efficiency within one trajectory, not evidence about variation across independent agent runs.

The same bundle's audit note reports 23 actual tool calls and 37 persisted relations. Several judge rationales count 24 calls, while the agent's answer says 36 relations. The retained tool events and persisted graph should be used for a human recount. Do not silently change the official TF/PE values to resolve these discrepancies.

Middle A Full Rewrite has TF scores `[7, 9, 8, 9, 9]` and five PE scores of 7. Its TF mean is 8.4, with sample SD approximately 0.894. These figures are reproducible from EVAL. The maximum-rounds outcome still needs to be shown alongside them.

Human validation remains pending. This analysis is an automated consistency check plus a review of recorded evidence; it is not a completed independent human-rating study. [judge_attempts.csv](../results/evaluation/fanziyu-pilot-audit-20261027/judge_attempts.csv) preserves individual values and whether raw responses are available.

## Failure review

### F1 — grading failure, not a zero-scoring task

`results/evidence/baseline-integration/real-early-no-update.json` records completed agent execution but incomplete judge evaluation. TF and PE remain null. This is an evaluation failure; assigning zero would conflate a scoring problem with task performance. Its five judge attempts and consumed tokens remain in the audit.

The same record includes a round-3 `create_entities` call with `{}` arguments. This occurs at Early, so it does not demonstrate failure to adapt to an Early→Middle/Late change. The tool error should remain an argument-generation candidate unless additional evidence establishes another mechanism.

### F2 — missing required argument in a Full Rewrite run

In Middle B Full Rewrite, tool event index 15 (zero-based), round 4, calls `@pimzino/agentic-tools-mcp_1mcp_create_task`. The supplied arguments omit `projectId`. The tool returns MCP error `-32602`, identifying the missing required string at `projectId`. This is direct evidence of an invalid call.

It is not yet an over-update case. The published bundle does not establish that rewriting the description caused the omission. Likewise, the error alone does not establish an omitted environment change. Inspect the applied schema/description against Early and target metadata, then compare a controlled correction under the same configuration. Keep diagnostic runs separate from the main experiment.

### F3 — repeated verification and non-termination

Both Middle batches reach the 12-round cap. The Middle B No Update judge records identify repeated `list_tasks`/`read_graph` verification without a final answer. Middle A Full Rewrite's published consistency audit reports 28 tool results with no tool errors, yet execution still reaches the cap. The common observable failure is non-termination under the configured limit. An adaptation-specific causal explanation has not been demonstrated.

These cases support reporting `judge_format` and `agent_execution` problems, but **do not satisfy** the brief's requirement for one demonstrated under-update and one demonstrated over-update trajectory. Both required causal categories remain open; no injected or hypothetical case is presented as an observed result.

## Readiness decision

Proceed with evaluation integration and pilot QA. Do not freeze a formal result table yet.

1. Integrate C's Selective Patch with the same runner used by the baselines and perform a real end-to-end check.
2. Reconcile the current LLM baseline implementation with stale implementation-status fields in the protocol.
3. Review an independent task subset. Task 223 is now a development optimization case alongside 139; neither belongs in the final held-out set.
4. Fix task transitions, model/decoding/judge settings, fixtures, implementation commits and retry policy before the formal comparison.
5. Collect all three strategies for the same tasks/repeats, with all three versions for ECS. Add actual human judge checks and causal failure evidence.

The evaluator can already produce the required tables once those inputs exist. Missing values, unmatched cells and all attempts are retained, so an incomplete run cannot quietly become a successful comparison.

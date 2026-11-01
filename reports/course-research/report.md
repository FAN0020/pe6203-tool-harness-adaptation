# Selective Tool Knowledge Adaptation under Environment Change

PE6203 Group Project 4   |   Research report   |   1 November 2026

## Research conclusion

The implementation can recover specific tool capabilities after an environment change, but no tested candidate has yet demonstrated the required joint improvement over the original Selective Patch on the frozen original benchmark subset. The latest ready_link development study tied normal completion at 1 of 4 changed conditions and reduced mean official task fulfillment from 9.8 to 7.4. Its apparent product-quality gain occurred on task 133, where the two arms used identical knowledge. The candidate was closed without formal validation. [3]

This report separates the completed 27-run course comparison, additional exposed development cohorts, and controlled synthetic diagnostics. Their scores are not pooled. No Update and Full Rewrite remain course baselines; new candidate studies use a fresh, contemporaneous original Selective Patch control. Five judge ratings per trajectory are measurement repeats, not five independent agent runs.

### Method and contribution

The original Selective Patch is a deterministic metadata and reference-based updater. It compares tool identity, parameters, descriptions, output schemas and routing; expands the affected set through explicit one-hop usage-rule references; copies authoritative changed records; and validates schemas, routing and preservation of unrelated records. Tool renames without stable evidence are treated as removal plus addition. Its reference index is a lexical heuristic, not a learned dependency graph. [1, 9]

No Update retains Early knowledge. Full Rewrite rebuilds structural fields from target metadata and uses the fixed model to regenerate all target descriptions. The course comparison therefore varies both update scope and generation mechanism; it is not a pure scope ablation. The later work tests source-grounded semantic repair, dependency scheduling and field-level observation knowledge while preserving the shared actor and judge. These are measured mechanism tests with negative as well as positive outcomes, not evidence of a universally superior updater.

### Delivery status

The research objective remains unmet. Two independent validation batches have not begun because development gates failed. A causal Selective Patch under-update example and a causal over-update harm example also remain unestablished. The user reports that the presentation has ended and has removed further slide and speaker-script work from scope. No external submission or publication is claimed.

## Study design and authority

The course brief requires fixed model, decoding, tasks and judge across No Update, Full Rewrite and Selective Patch; three environment stages; TOOL, PARAM and DESC coverage; TF, PE and ECS; recovery, retention and update cost; and failure trajectories. A documented fixed subset and one trajectory repeat are allowed, although three repeats are preferred. The user adds a stronger research criterion: strict gains in normal completion and actual product quality in development and separately in each of two fresh validation batches, with no TF or retention decrease. [1, 3, 10]

| Cohort | Conditions | Role |
| --- | --- | --- |
| Course baseline | 133, 235, 283 × Early, Middle, Late × NU, FR, SP; 27 runs | Course comparison; one run per cell |
| Current original development | 133 Middle/Late and 283 Middle/Late; 235 Late retention; 10 runs per two-arm study | Exposed development; fresh SP control |
| Daily migration | Task 90 × three stages × four methods; 12 runs | Separate exposed capability-recovery cohort |
| Synthetic diagnostics | Predeclared generated cases in separate protocols | Mechanism discrimination only |

Task 133 concerns secure mathematical-expression guidance; task 283 requests a structured project plan; task 235 checks unchanged chart-tool behavior. TOOL coverage in the course subset consists of relevant optional additions, not mandatory deletion or rename. The data and tools are available for the chosen original conditions. The missing-input search route for task 377 remains closed. Task 283 shares a server family with earlier development, so the subset is not an unseen-family holdout.

### Shared execution and information boundaries

Current development fixes deepseek/deepseek-v4.1-flash-1017 on DigitalOcean with fallback disabled, temperature 0, 4096 actor completion tokens including reasoning, 12 rounds, and request/run/tool timeouts of 120/900/30 seconds. No model seed is sent. The official rubric uses five first-valid judge slots, at most two logical attempts per slot and the frozen transport-retry policy. Judge tool observations are limited to 1000 characters. Historical course routing configuration is retained as recorded, rather than retroactively described as the current provider lock. [1, 3]

Updaters may consume changed metadata, relevant source and frozen task-free native probes. They may not consume benchmark questions, answers, scored trajectories or manually distilled answer recipes. Candidate knowledge, sources and hashes, order, repetitions, acceptance, failure handling and an independent ledger are frozen before model calls. A change of actor, model, single-run budget or acceptance threshold would require a different authorized study.

## Course baseline results

TF denotes task fulfillment and PE denotes planning and efficiency, each on the official 1–10 scale. Normal counts trajectories with completed execution status, independently of their judge scores.

| Stage | Method | Normal | TF | PE |
| --- | --- | --- | --- | --- |
| Early | NU | 2/3 | 9.933 | 8.667 |
| Early | FR | 2/3 | 10.000 | 9.000 |
| Early | SP | 2/3 | 9.667 | 9.667 |
| Middle | NU | 3/3 | 10.000 | 6.667 |
| Middle | FR | 3/3 | 9.933 | 7.800 |
| Middle | SP | 2/3 | 10.000 | 9.133 |
| Late | NU | 2/3 | 9.933 | 8.267 |
| Late | FR | 2/3 | 10.000 | 8.267 |
| Late | SP | 2/3 | 10.000 | 8.533 |

All 27 trajectories have complete official ratings: 20 ended normally, five reached the round limit and two were output-truncated. Mean scores do not imply correct final artifacts. Every row contains only three different tasks and one execution per task. [1]

| Method | ECS pop | ECS sample | Update tokens | Seconds | USD |
| --- | --- | --- | --- | --- | --- |
| NU | 9.924 | 9.917 | 0 | 0.000 | 0.000000 |
| FR | 9.946 | 9.939 | 177974 | 203.508 | 0.049176 |
| SP | 9.732 | 9.696 | 0 | 1.145 | 0.000000 |

ECS is calculated for each matched task as mean TF across Early, Middle and Late minus its standard deviation, then averaged over the three tasks. Both the released population and paper sample conventions are retained. SP has zero model-update tokens but does not lead ECS in this cohort. Early task 133 varied despite identical knowledge across methods, affecting ECS without an adaptation difference.

For changed tasks, SP minus NU mean TF is 0.0 in Middle and +0.1 in Late; FR is −0.1 and +0.1. For unchanged task 235, all methods have TF 10 in Middle and Late, with zero change from NU Early. This establishes score retention of chart-specification behavior, not browser-rendered dashboard correctness. NU Middle also repeats the map call five times, showing that repeated calls are not unique to Full Rewrite.

## Mechanisms tested beyond the baseline

### Semantic contract repair

The LLM in semantic repair made content decisions rather than merely rephrasing a fixed note. The first version proposed edits and dependency scope but failed source validation. In version 2, the program fixed the admissible changed fields and supplied a claim inventory; the LLM classified claims as retained, replaced or unknown with source support. It retained four and replaced ten of fourteen claims. This is narrower than unrestricted learned impact discovery. Six original runs on 133 Middle/Late and 235 Late produced equal changed-task normal completion at 1/2 and core quality at 0/2, despite TF rising from 9.3 to 9.9 and PE from 5.9 to 7.7. The version was rejected. [4]

### Dependency scheduling knowledge

dependency_cut separated record creation from dependency linking, eliminating the need to know dependency identifiers during initial creation. ready_link then made this conditional: include the complete dependency set when all real identifiers already exist; otherwise defer the link and release it when its own prerequisites are available. It never invents identifiers or submits partial dependency sets. The change is confined to knowledge attached to the changed create_project record; task 133 and retention-task knowledge remain byte-identical to SP. [3, 5]

The borrowed principle is ready-prerequisite release in LLMCompiler, pinned to paper 2312.04511v3 and author commit a00c9d35507507da70e8c637eee64efc8c1857ae, task_fetching_unit.py lines 100–133. The original planner, symbolic argument runtime, parallel executor and replanning are not imported. Here a static tool-knowledge rule must be adopted by the unchanged actor; it does not execute the schedule itself. Native tests therefore establish legality and state equivalence, not agent completion.

### Observation coverage knowledge

observation_coverage records which returned fields can support which claims and conservatively invalidates stale observations after mutation. Its proposed benefit was fewer unnecessary reads and better grounded final claims. All four original project trajectories made zero get_task calls, weakening the specific explanation that removing redundant get_task reads caused the observed Middle success. A later controlled diagnostic also found no reliable read saving and one false claim that a field was unavailable through all read-only tools. [6]

### How prior literature was used

ACE contributes local playbook operations and feedback accounting; A-MEM contributes related-memory evolution; Reflexion relies on executable feedback and further attempts. Earlier delta_notes, lexical linked_notes and pre-frozen feedback_notes did not implement those complete systems. Author code and paper versions are pinned in reference 8. Full Reflexion retries would alter the current actor protocol, and answer-bearing benchmark experiences cannot be supplied to the updater. A failed implementation does not establish that an entire method family is ineffective.

## Original development results and decisions

| Study | Arm | Normal | Core | TF | PE |
| --- | --- | --- | --- | --- | --- |
| Dependency cut | SP | 1/4 | 0/4 | 9.05 | 8.20 |
| Dependency cut | Candidate | 1/4 | 0/4 | 9.70 | 7.80 |
| Observation coverage | SP | 2/4 | 1/4 | 9.70 | 8.25 |
| Observation coverage | Candidate | 3/4 | 1/4 | 9.70 | 7.80 |
| Ready link | SP | 1/4 | 0/4 | 9.80 | 8.00 |
| Ready link | Candidate | 1/4 | 2/4 | 7.40 | 7.90 |

Each study independently evaluates the same four original changed conditions and one retention condition per arm. Results are displayed together for interpretation, not pooled as a larger independent sample. Core means every predeclared substantive product property passes; unknown or missing evidence is not a pass. Normal completion and core quality remain separate outcomes. [3, 5, 6]

Dependency cut failed both strict-gain criteria. Observation coverage improved normal completion from 2/4 to 3/4 but tied core quality at 1/4; retention TF fell from 10 to 9.8. Ready link tied completion at 1/4 and reduced TF. Its two core passes were on task 133 with identical knowledge in both arms, so they do not establish an adaptation effect. Under a stricter intermediate-resource-bound interpretation of one answer, candidate core becomes 1/4; the rejection decision is unchanged.

### Why local savings did not establish success

In ready_link Late, the candidate used 33 calls for 30 records, including 22 inline dependency writes; SP used 74 calls for 53 records and 18 later link updates. Both reached 12 rounds with an empty final delivery. The 41-call difference comprises 23 fewer creates and 18 fewer updates, so it cannot all be attributed to scheduling. Candidate Middle stopped after one list_projects call; the next response used its entire 4096-token allowance and ended with length. This proves truncation, not its root cause.

The task-free native suite checked 18 equivalent end states, six invalid-identifier controls and 232 calls. Ready link reduced theoretical waves on two of three generic graph patterns. However, post hoc reconstruction of the three saved original project graphs gave six waves for both global deferral and ready release. That analysis assumes the whole final graph is known in advance and ignores planning and token packing. It weakens transfer of the canary advantage to these observed plans; it does not prove how the actor would behave under an executable scheduler.

Decision: close these specific versions without validation or additional sampling. The open competing explanations concern planning granularity, binding time, adoption of the knowledge rule and output-budget consumption. None is resolved simply by adding another scheduling sentence.

## Failure analysis and causal limits

### Knowledge adaptation

Course task133-late-no_update-r0 made four initial calls without the newly required allow_variables parameter and was rejected. It then repaired the calls from runtime feedback and completed after 38 tool calls, with TF 9.8 and PE 7.2. The paired SP trajectory supplied allow_variables in three accepted validate_syntax calls, used four tool calls overall and received TF 10 and PE 7. This directly supports stale-parameter failure and successful schema adaptation, while final-score causality remains limited by one run. It is a No Update failure, not a demonstrated SP under-update. [1]

### Execution and budget

Repeated round exhaustion with incomplete handoff is a high-impact bottleneck in task 283. Native call validity and lower call count do not guarantee final delivery. Early task 133 also truncates under identical knowledge. Finish metadata establishes the stopping condition; it cannot by itself distinguish excessive planning, response length, poor tool selection or prompt-induced behavior. These are intervention hypotheses, not established causes.

### Product generation

Saved state and final claims require separate checking. In ready_link, a substantial saved project can coexist with an empty final answer. In the dependency-factorial diagnostic, all four SP chain cases saved correct state but exhausted rounds; the candidate completed all four yet passed all product properties in only two. One candidate omitted a dependency and another changed a project description while claiming an extra tag. Completion gains alone therefore did not establish reliable quality gains. Synthetic outcomes remain separate from original benchmark success. [7]

### Environment and data

A missing upstream method and an agent-generated empty argument object are different failures. The course archive records review_workspace_health(includeMemories=true) failing because listMemories is absent, alongside two rejected empty create_task calls. Those observations do not demonstrate damage to unrelated knowledge. Task 235 returns chart specifications; hosted rendering was not tested. Missing original input for task 377 is excluded as unavailable, not scored as a strategy failure.

### Evaluation uncertainty and over update

The six-run chart rollback diagnostic gave both arms TF/PE 10 and one map call per run; it did not reproduce the suspected rewrite harm. Offline review nevertheless found an incorrect annual total in one rewritten answer and an omitted map-specification unit in one rollback answer. These remain product defects, not proof of a causal over-update effect. Judge observation truncation also hides some retrieved facts in the separate daily cohort. Original scores are retained. Product reviews were performed by the same coordinator before score disclosure in recent studies, not by an independent human or under strict method blinding. [1, 2]

## Additional recovery evidence and cost

| Task 90 method | Normal | TF | PE | ECS pop |
| --- | --- | --- | --- | --- |
| NU | 3/3 | 8.933 | 8.667 | 7.425 |
| FR | 3/3 | 9.933 | 9.600 | 9.839 |
| SP | 3/3 | 10.000 | 9.800 | 10.000 |
| Budget feedback | 3/3 | 10.000 | 9.333 | 10.000 |

In this separate 12-run exposed development cohort, No Update Late used an obsolete tool twice and failed to retrieve the current daily problem. Updated methods recovered the content through daily=true. All methods nevertheless completed all three stages, so this supports content recovery over NU, not a completion advantage over SP. Budget feedback also mislabeled setcode 221 as a card password in one answer; the actual card ID was 89631139. Core retrieval and additional unsupported assertions are distinguished. [2]

| Cohort | Known USD | Unknown | Accounting scope |
| --- | --- | --- | --- |
| Course main 27 | 0.406912 | 1 | Excludes preflight and separate diagnostics |
| Daily migration 12 | 0.202213 | 0 | Includes recorded preflight and updater |
| Dependency cut 10 | 0.205121 | 0 | 119 settled model requests |
| Observation coverage 10 | 0.180154 | 0 | 114 settled model requests |
| Ready link 10 | 0.164358 | 0 | 106 settled model requests |

Amounts are provider-reported request charges, not an independently exported invoice. They are selected cohort totals, not the full research cost. Earlier failures, preflights and diagnostics remain in their original ledgers. The separate dependency-factorial study has one unresolved timeout without a generation ID; the user-approved A1 exception allowed its completion without treating that request as free. This is distinct from the older course connection-failure charge. [1, 7]

The current-key endpoint reported usage USD 9.599346951 of a USD 10 limit at 11:25:10 UTC on 1 November 2026. That is a credential-level aggregate, not a project-total or individual-request invoice. A backup key is configured but has not been activated. This report build makes no actor, updater, judge or native-tool calls and adds no experiment model cost.

## Reproduction and remaining requirements

The companion REPRODUCE.md is the local entry point. It indexes the pinned inputs, immutable raw archives, historical commands and offline verifiers. source-manifest.json records SHA256 digests of the synthesis inputs; metrics.json contains the exact unrounded data used for the tables. Rebuilding this document does not rerun any experiment. The report deliberately preserves separate source cohorts and their original scores.

MCPEvol-Bench is pinned to commit 888c779a0fe735f612ca62bdd1fdd7c9e6bf8701 and dataset revision 162e3ffbea1717ac8a20fe9b26465e29117229e4. The course raw archive hash is e95e15694abe9a12e37c813f81e6e0fb0b5ccd00c2003f2a25a36a092c8001c9. The ready_link model freeze is a95ad2d, with product reviews frozen at 89cfd3d before score disclosure. Its verifier covers 420 raw files, 188 frozen source files and 50 original judge slots. Historical replay uses its archived implementation, rather than assuming current source still matches every old freeze. [1, 3]

| Requirement | Evidence status |
| --- | --- |
| NU and FR course baselines; TF, PE, ECS; cost | Present for 27 main runs; limited subset and one repeat disclosed |
| Changed-task recovery and unchanged retention | Measured; limited recovery evidence, no general superiority claim |
| Causal SP under-update and over-update examples | Not established; related trajectories and failed diagnostic retained |
| Strict original development dual improvement | Not achieved by the reported candidates |
| Two independent validation batches | Not started because development gates failed |
| Report and reproducibility entry | Produced locally; no external submission claimed |
| Presentation work | Ended per user; no further slides or speaker scripts requested |

If a future candidate passes development, the recorded validation design requires two fresh batches of 30 trajectories each: three repeats per condition and arm, empty isolated task workspaces, no shared actor memory and separate ledgers. The same knowledge must remain byte-identical across batches. Each batch separately must pass strict normal-completion and core-quality gains on the whole changed subset and the project subset, with TF and retention nondecrease. Independence means fresh executions on already exposed tasks, not unseen-task generalization or proven statistical independence of the provider.

No new candidate is admitted by this synthesis. The report closes a delivery gap, not the research gap. A next experiment needs a distinct, lawful knowledge decision and a falsifiable prediction that separates the remaining explanations. A failed version may be closed without declaring the entire mechanism family ineffective; a new version need not already have proved success before a fair test.

## Evidence and references

[1] Course baseline. results/evidence/course-v1.3-20261031. summary.json, interpretation.json, cost-audit.json, metrics-audit.json, plan.json and reproduction.json. Contains the named trajectory IDs and the separate rollback diagnostic.

[2] Daily migration. results/evidence/daily-migration-pilot-20261031. trial-verification.json, quality-review.json and reproduction.json. Twelve exposed original-task runs; live public content.

[3] Ready link. results/evidence/ready-link-20261101. decision.json, interpretation.json, research-decision.json and reproduction.txt; protocol experiments/ready-link-v1.json.

[4] Semantic claim repair. results/evidence/semantic-claim-repair-20261101. decision.json and interpretation.json; source src/pe6203/semantic_contract_maintenance.py.

[5] Dependency cut. results/evidence/dependency-cut-20261101. decision.json and interpretation.json; original development separated from the later factorial diagnostic.

[6] Observation knowledge. results/evidence/observation-coverage-20261101. decision.json; controlled follow-up in results/evidence/observation-selection-20261101.

[7] Dependency factorial. results/evidence/dependency-factorial-20261101. decision.json; synthetic mechanism diagnostic and unresolved-charge accounting.

[8] Mechanism literature. results/evidence/method-learning-20261101/method-review.json. ACE 2510.04618v1, ace-agent/ace SHA 82709de050e1db6e6ef2f07bcb0393560b94992a. A-MEM 2502.12110v1, WujiangXu/AgenticMemory SHA f9a173dec325d84fcc97e7828775c7b241c33466. Reflexion, NeurIPS 2023, noahshinn/reflexion SHA 218cf0ef1df84b05ce379dd4a8e47f17766733a0. Exact functions and implementation limits are recorded in this file.

[9] Selective updater implementation. src/pe6203/selective.py. Metadata diff, explicit reference index, impact expansion and adaptation validation. Full Rewrite implementation is in src/pe6203/baselines.py; optional updater availability is not evidence it was used.

[10] Course authority. PE6203 Group Project 4 brief. Tool Harness Adaptation under Environment Change. Supplied DOCX SHA256 6a74fda17b7a8b9280151e55ec46b46a70d1d717e4be24c5f9c38d134611af0d. User research requirements and later presentation-scope update take precedence for this work.

LLMCompiler: https://arxiv.org/html/2312.04511v3 ; https://github.com/SqueezeAILab/LLMCompiler/tree/a00c9d35507507da70e8c637eee64efc8c1857ae . Borrowed ready-prerequisite logic only; native equivalence and agent outcomes are reported separately.

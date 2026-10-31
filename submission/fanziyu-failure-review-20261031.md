# Failure analysis: evidence and presentation notes

Fan Ziyu（范子钰） · PE6203 Project 4 · 31 October 2026  
Scope: P10–P11 and their supporting failure evidence. Status: ready for team review.


Deliverables: [reviewed P10/P11 deck](https://docs.google.com/presentation/d/1w7xBz3D0C3KBliX86qDPl8i0gRZn12xs/edit) · [analysis and evidence package](https://drive.google.com/file/d/1rjIp5CIs37isogP22eXnVqd3MMpnDAJ6/view). The allocation table records Fan Ziyu as owner and the material as ready for team review.

## 1. Which conclusions are supported?

The controlled omission confirms a local under-update mechanism: calls that omit the newly required `allow_variables` field receive eight matching rejections, compared with zero under the complete knowledge snapshot. It does not show that the original Selective Patch updater omitted the field, and correcting the knowledge does not improve PE in this pair.

The rule rollback is suggestive evidence about execution expansion. It does not establish the required over-update chain of **unrelated knowledge changed → normal behaviour damaged**. The rule concerns a related validator, execution is stochastic, and there is only one trajectory per condition. Six earlier chart diagnostics did not reproduce the historical score regression. These negative results remain part of the analysis.

The course brief does not explicitly require natural occurrence. Neither does it automatically establish that fault injection is sufficient. Course-case acceptance remains pending TA clarification. We should submit the supported mechanism, counterevidence and open requirement together, without presenting the gap as resolved.

## 2. Keep the evidence sets separate

| Evidence set | Executions | Judge ratings | Use |
|---|---:|---:|---|
| Frozen main benchmark | 27 | 135 | Three methods × three tasks × three stages × one execution |
| Targeted controlled diagnostics | 4 | 20 | Two intervention/control pairs, each executed once |
| Earlier chart diagnostics | 6 | 30 | Historical negative evidence, separate from the main result |

The historical 108-trajectory confirmation study is not the main benchmark. Five ratings assess the same trajectory and do not constitute five independent executions. We did not run new model calls or change frozen scores for this review.

## 3. Under-update case: the missing required field

**Task:** 133, Late. **Intervention:** start from the correct main Patch knowledge and remove only `math-mcp::validate_syntax.parameters.properties.allow_variables` and its entry in `parameters.required`. The complete condition retains both. The environment still requires the field.

```diff
 properties.allow_variables:
- {"type":"boolean", "description":"Explicitly specify whether variable references are allowed during validation"}
+ absent
 required:
- ["expression", "allow_variables"]
+ ["expression"]
```

| Condition | Missing-field rejections | All calls / tool errors | Terminal status | TF | PE |
|---|---:|---:|---|---:|---:|
| under_omitted | 8 | 27 / 9 | output_truncated | 10 | 5.8 |
| under_complete | 0 | 5 / 1 | completed | 10 | 5.6 |

The omitted arm produces two missing-field rejections in round 1, five in round 2 and one in round 3. Its ninth tool error has a different cause. The complete arm's one tool error is an upstream `batch_evaluate` handler defect, not a missing-field rejection. Tool-error totals count `isError=true`; a returned syntax-validation finding can have `isError=false`.

**Representative calls.** The table below preserves exact relevant arguments and observations. The JSON evidence contains all calls, including unselected results.

### under_omitted, round 1: `math-mcp::validate_syntax`

```json
{
  "expression": "2 + 3 * (4 - 1) / 2",
  "detailed": true,
  "show_ast": true
}
```

Observation: `Error: validate_syntax requires allow_variables to be explicitly provided as a boolean`

### under_omitted, round 2: `math-mcp::validate_syntax`

```json
{
  "expression": "2 + 3 * (4 - 1) / 2",
  "detailed": true,
  "show_ast": true,
  "check_balanced": true,
  "max_depth": 20
}
```

Observation: `Error: validate_syntax requires allow_variables to be explicitly provided as a boolean`

### under_omitted, round 3: `math-mcp::validate_syntax`

```json
{
  "expression": "2 + 3 * (4 - 1) / 2",
  "detailed": true,
  "show_ast": true,
  "check_balanced": true,
  "max_depth": 20
}
```

Observation: `Error: validate_syntax requires allow_variables to be explicitly provided as a boolean`

### under_complete, round 1: `math-mcp::validate_syntax`

```json
{
  "expression": "(a + b) * 2 / (c - 1)",
  "allow_variables": true,
  "detailed": true,
  "show_ast": true
}
```

Observation: `Expression is syntactically valid.`

### under_complete, round 2: `math-mcp::batch_evaluate`

```json
{
  "expressions": [
    "2 ** 10",
    "sqrt(144) + 3",
    "1 / 0",
    "abs(-7) * 2"
  ],
  "stop_on_error": false
}
```

Observation: `Error: this.toolHandlers.handleBatchEvaluate is not a function`

**Root cause and scope.** The error names the omitted required field and appears on every validator call in the omitted arm. That directly supports the local rejection mechanism. Final TF remains 10 in both conditions, and PE is 0.2 lower in the complete arm. Therefore “restoring the field improves overall PE” is contradicted for this pair. The paired trajectories choose different expressions and follow different paths, so a broad effect size cannot be estimated from them.

**Main-run context.** U1 is No Update, not Patch: task133 Late makes four initial missing-field calls and later recovers, finishing with TF 9.8 and PE 7.2. U2 is the original Patch: the knowledge includes the required field, all three validator calls supply it, and there are no tool errors. The claim that U2 failed because Patch omitted the field is contradicted by its knowledge and calls.

**Measurement caveat.** Four complete-arm judge rationales incorrectly treat `batch_evaluate` as unavailable despite its presence in the available knowledge. The observed failure is a missing handler. Original scores remain unchanged. A separate analysis can flag measurement validity without inventing corrected grades.

## 4. Over-update candidate: rollback of one related rule

**Task:** 133, Middle. **Method provenance:** historical `linked_notes`, not the original main-benchmark Patch. The controlled pair differs only in `math-mcp::evaluate.usage_rules`. Three other historical rules remain identical.

Retained rule, verbatim:

> validate_syntax now accepts optional detailed and allow_variables flags; evaluate's validate_only remains a separate syntax-only path, so choose based on whether evaluation is also wanted.

Reverted value: `[]`.

| Condition | Calls / tool errors | Terminal status | TF | PE |
|---|---:|---|---:|---:|
| over_note | 22 / 2 | output_truncated | 10 | 7.8 |
| over_reverted | 4 / 0 | completed | 9.8 | 10 |

Both arms successfully validate an expression with `allow_variables=true` in round 1. The retained-rule arm makes five additional validator calls in round 2 and continues evaluating in round 3. The reverted arm makes all four tool calls in round 1 and returns its final answer in round 2.

### over_note, round 1: `math-mcp::validate_syntax`

```json
{
  "expression": "(revenue - cost) / max(units, 1) * 100",
  "detailed": true,
  "allow_variables": true
}
```

Observation: Expression is syntactically valid.

### over_note, round 2: `math-mcp::validate_syntax`

```json
{
  "allow_variables": true,
  "expression": "sqrt(area) + abs(delta) - round(ratio, 2)"
}
```

Observation: Expression is syntactically valid.

### over_reverted, round 1: `math-mcp::validate_syntax`

```json
{
  "expression": "(a + b) * sqrt(c) / max(d, 1)",
  "allow_variables": true,
  "detailed": true
}
```

Observation: Expression is syntactically valid.

### over_reverted, round 1: `math-mcp::evaluate`

```json
{
  "expression": "(3 + 4) * sqrt(9) / max(5, 1)"
}
```

Observation: {
  "expression": "(3 + 4) * sqrt(9) / max(5, 1)",
  "result": 4.2,
  "type": "number"
}

**Interpretation.** Reverting the rule accompanies 18 fewer calls, a 2.2-point PE increase and normal completion. TF decreases by 0.2. This is a possible trade-off rather than uniform recovery. One execution per arm cannot show that the rule generally causes unnecessary exploration. `evaluate` has unchanged metadata, but the rule explicitly refers to the changed validator, so metadata invariance does not establish semantic irrelevance.

**Negative evidence.** Historical O1 rewrites 28 unchanged chart descriptions in Full Rewrite and scores TF 8.8 / PE 4.2. It repeats map generation, but the rewritten description still mentions `dataValueUnit`. Thus missing guidance is not established. All six later chart rewrite/rollback diagnostic trajectories complete and score TF/PE 10. They do not reproduce the historical score regression, so the original causal claim remains inconclusive. Manual review finds the incorrect 24.4M annual total in three answers across both groups, while the correct total is 25.4M. The high grades do not prove absence of factual errors or absence of over-update risk.

## 5. Claim-level decisions and next steps

| Claim | Decision | Evidence boundary |
|---|---|---|
| Omitted required field causes the eight corresponding rejections | Confirmed | Controlled local call mechanism |
| The original Patch updater omitted this field | Contradicted in U2 | Correct field and three correctly formed calls |
| Restoring the field raises PE in the diagnostic pair | Contradicted | 5.6 complete versus 5.8 omitted |
| Retaining the evaluate rule increases exploration | Suggestive | Single run per arm, different realised calls |
| The rule is unrelated knowledge and causes normal behaviour to degrade | Inconclusive | Semantic relation and TF trade-off remain |
| Historical chart description rewrites caused O1's low score | Inconclusive | Six negative comparisons and retained unit guidance |

A useful implementation follow-up would be an invariant check that every target-required schema field remains represented after updating. The controlled deletion is a regression fixture for that check, not evidence that the current updater violates it. A future over-update causal test would need a justified unrelated record, a minimal intervention, matched conditions and agreed repetitions. This review does not authorize or execute that new experiment.

Questions for the team to send to the TA, if still unanswered:

1. May the disclosed controlled omission, including eight directly attributable errors and the negative PE result, count as the under-update example? Must we also demonstrate a failure by the updater itself?
2. May we report the suggestive related-rule case and negative chart diagnostics with an explicit unresolved over-update cause, or is another directly supported unrelated-knowledge case required?

## 6. English speaking script (about 2.5 minutes total)

### P10

In the main experiment, stale No Update knowledge caused four missing-parameter rejections, while the original Patch supplied the required field. That does not establish a Patch omission. We therefore examine a separately reported fault injection. For task 133 Late, the diagnostic removes allow_variables from both the schema properties and the required list. The omitted condition makes two rejected calls in round one, five in round two, and one in round three. The complete snapshot has zero missing-field rejections. This confirms the local missing-parameter mechanism. But final quality does not improve uniformly: both TF scores are ten, and PE is 5.8 with the omission versus 5.6 with complete knowledge. The complete arm also hits an upstream batch_evaluate handler defect. We report the fault mechanism, the negative PE result, and the separate tool defect together. Whether this controlled case satisfies the course requirement remains for the TA to confirm.

### P11

For over-update, we need evidence that changing unrelated knowledge damages otherwise normal behaviour. Our strongest current comparison rolls back one evaluate usage rule in the historical linked_notes variant. It is separate from the main Patch benchmark. With the rule retained, the agent makes twenty-two calls and truncates. With the rule removed, it makes four calls and completes. PE rises from 7.8 to ten, but TF falls from ten to 9.8. This is suggestive, not a confirmed over-update cause. There is only one execution per condition, and the rule refers to the changed validator, so it is semantically related. We also retained six earlier chart rewrite and rollback diagnostics. All scored ten on both metrics and did not reproduce the historical score regression, although manual review found factual errors. Our conclusion is that unrelated-knowledge damage remains unproven. A lower score or extra calls alone cannot establish that causal chain.

## 7. 中文讲解与对接提示

你负责的是失败原因和证据边界，不需要把所有历史实验都讲一遍。P10 先说“真正确认的是缺参导致拒绝”，随后说明删参是受控注入、原 Patch 并未漏参、补回后 PE 也没提高。P11 先说“回退后调用减少，但这还不能证明 over-update”，再解释规则相关、每组一次、TF 有下降，最后带出六条负结果。

如果老师问“那算完成失败分析了吗”，回答：我们完成了轨迹、知识差异、对照和反例分析；under-update 的局部机制有直接证据，over-update 的无关修改与损害之间尚缺因果证据。受控案例是否满足课程要求，需要按教师解释确认，不能把证据缺口写成已解决。

如果被问“为什么不继续跑到找到一个失败”，回答：继续重复未必补齐“知识无关性”和因果归因。我们先固定现有结论并保留所有负结果，只有在需要检验明确假设时才设计额外实验。

群内对接消息（待你自行发送）：

> 我已认领并整理好 P10/P11 的失败分析，英文页面、讲稿和对应证据已放共享文件夹，状态是待复核。Under-update 目前能确认受控删参造成 8 次拒绝，但不是原 Patch 自身漏参；over-update 规则回退仍属提示性证据，六条负诊断也保留了。麻烦合稿时使用这版两页，TA 对受控案例的要求确认后再统一最终表述。

## 8. Sources and verification scope

- [HANDOVER.md](https://github.com/FAN0020/pe6203-tool-harness-adaptation/blob/3198d23fcee1bdd99de883de7267296af9d872d1/HANDOVER.md)
- [submission/diagnostics-20261031/audit.json](https://github.com/FAN0020/pe6203-tool-harness-adaptation/blob/3198d23fcee1bdd99de883de7267296af9d872d1/submission/diagnostics-20261031/audit.json)
- [submission/diagnostics-20261031/exact-knowledge-diffs.json](https://github.com/FAN0020/pe6203-tool-harness-adaptation/blob/3198d23fcee1bdd99de883de7267296af9d872d1/submission/diagnostics-20261031/exact-knowledge-diffs.json)
- [submission/diagnostics-20261031/plan.json](https://github.com/FAN0020/pe6203-tool-harness-adaptation/blob/3198d23fcee1bdd99de883de7267296af9d872d1/submission/diagnostics-20261031/plan.json)
- [submission/diagnostics-20261031/classifications.json](https://github.com/FAN0020/pe6203-tool-harness-adaptation/blob/3198d23fcee1bdd99de883de7267296af9d872d1/submission/diagnostics-20261031/classifications.json)
- [submission/evidence/case-details/U1.json](https://github.com/FAN0020/pe6203-tool-harness-adaptation/blob/3198d23fcee1bdd99de883de7267296af9d872d1/submission/evidence/case-details/U1.json)
- [submission/evidence/case-details/U2.json](https://github.com/FAN0020/pe6203-tool-harness-adaptation/blob/3198d23fcee1bdd99de883de7267296af9d872d1/submission/evidence/case-details/U2.json)
- [submission/evidence/case-details/O1.json](https://github.com/FAN0020/pe6203-tool-harness-adaptation/blob/3198d23fcee1bdd99de883de7267296af9d872d1/submission/evidence/case-details/O1.json)
- [submission/evidence/diagnostic-review.json](https://github.com/FAN0020/pe6203-tool-harness-adaptation/blob/3198d23fcee1bdd99de883de7267296af9d872d1/submission/evidence/diagnostic-review.json)

All sources are pinned to `3198d23fcee1bdd99de883de7267296af9d872d1`. The diagnostic runtime itself comes from the frozen main source `12d693c`, as recorded by its plan. The source revision is the evidence snapshot, not a claim that experiments used the later documentation commit.

`verify_review.py` recomputes the four diagnostic TF/PE means from the 20 stored ratings, counts calls/errors from the preserved call arrays, verifies rejection rounds and the exact intervention, and checks the six negative cases. This is a fresh check of the exported audit evidence. It does not reconstruct the complete raw archive or re-run the project-wide verification, and it does not adjudicate the correctness of every judge rationale. Full archive reconstruction remains available through the repository's `submission/handover-20261031/verify.py`.

Raw diagnostic archive: `submission/evidence/targeted-diagnostics-20261031.tar.gz`. Relevant members: `raw/cells/<under_omitted|under_complete|over_note|over_reverted>/run/` (knowledge, events, trace and original judging). The package retains the exact source JSONs used here. No new executions or re-scoring.

The reviewed PPTX keeps 18 pages and changes only P10/P11 and their speaker notes. Other pages retain the source package contents. For collaborative merging, copy P10/P11 into the current group deck instead of replacing a concurrently edited full deck. The shared allocation table is the authority for current ownership.

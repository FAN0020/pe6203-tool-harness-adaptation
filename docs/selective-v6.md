# Selective V6

V6 is based on selective-V5 a97a599, with a new `hybrid_v6` updater and explicit
`run-v6` execution entry. Historical implementations, default hybrid_v2, No
Update and Full Rewrite algorithms remain unchanged. V6 is a **full-system**
comparison with unchanged baselines; it does not isolate knowledge update from
the additional Python artifact tests/repair inherited from V3/V5.

## Update before execution

1. Keep complete K0, target catalog, schema, independent source/probe material
   locally. The deterministic core synchronizes authoritative metadata and
   removes dangling rules. The model never repeats that work.
2. Reuse K0 without a paid screen if no metadata changes or credible independent
   anomalies exist. A failed predeclared finite probe check triggers review;
   matched probes alone do not fabricate a change or prove universal behavior.
   Supplied source excerpts trigger review without being treated as true claims.
3. Send one light global screening packet containing current purposes, retained
   rules, exact changed paths and brief event summaries. No full schemas, source
   excerpts or probe payloads are included. Check exact full-catalog ID coverage.
4. Union program-required rule/dependency/anomaly candidates, model potential
   dependencies and uncertain candidates. Program dependencies are transitive
   explicit name references, a heuristic. Model coverage receipts cannot prove
   semantic recall; implicit dependencies can still be missed.
5. Hydrate candidate and cited-change evidence only. Automatically include exact
   changed schema leaves; additional fields use validated JSON pointers. Value
   pools deduplicate identical content inside each packet. No global directory
   is sent with local patches. The complete provenance registry stays local.
   A selector naming only tool/side/field deterministically means that whole
   field (root pointer); unknown keys, out-of-scope tools and invalid subpaths
   are rejected. Requesting an already supplied field is not new evidence.
6. Model edits only usage rules. Retained indices and typed evidence references
   are validated; unrelated records remain equal. Catalog statements are
   declarations, source excerpts are source observations, probes are finite
   observations. LLM guidance is explicitly unverified; unknown/conflict remains
   explicit. Provenance does not establish semantic entailment, and preservation
   of unrelated natural-language rules within selected records still requires
   substantive review, beyond structural validation.
   Candidate packets include program-computed citation scopes (own tool and
   relevant changed tools). A rejected patch receives exact missing-citation
   diagnostics for its one revision; the program never silently adds citations
   or relaxes the evidence coverage requirement to admit it.
   V6 alone uses strict JSON Schema response formatting at the model API. The
   transport envelope has `patches` and `need_evidence` arrays; only one may be
   nonempty. Extra fields are forbidden. The decoder format is counted in
   request-size estimates; independent program admission still validates actual
   IDs, citations and patch contents. Historical API callers are untouched.
7. One patch plus at most one directed evidence/admission revision per batch.
   No implicit updater transport retry. Invalid/incomplete screen fails rather
   than invoking another full screening. If budget is insufficient, stop with
   costs and unresolved failure; no silent deterministic fallback.
8. Check schemas, routes, IDs, evidence scope, unaffected records and independently
   declared argument cases. Existing frozen task-independent probes bound any
   behavioral observations; the updater cannot generate or execute new probes.
   Publish a hash-bound versioned snapshot. Failed admission publishes no KB.

## Budgets and packing

Preflight records characters, UTF-8 bytes, estimated tokens and worst-case dollar
reservation before each request. Token estimate is UTF-8 bytes / 3 + 32, an
engineering heuristic, **not** the DeepSeek tokenizer. Dollar reservation instead
uses a conservative byte-based token allowance plus maximum output; actual usage
and billed USD come from responses. Unknown charges stop subsequent calls.

Defaults: 32 calls/update, 8 candidates/batch, 1 revision/batch, 900 seconds,
120,000 characters/request, 1,000,000 cumulative estimated input tokens and
$0.05/update. These are configurable deployment guards, not paper requirements.
The 10,000-token first-screen goal is a soft engineering target, not a rejection
threshold. Actual catalog packing must be measured before a formal plan freezes
these guards. Oversized candidate groups split without dropping candidates or
evidence. A single candidate still too large fails explicitly with a requirement
for narrower evidence packaging; nothing is silently truncated. Retry context
that is retransmitted is counted again, including cached input usage.

Default example rates ($0.035/M input, $0.5/M output) were checked against
OpenRouter Relace/fp4 on 2026-11-03. A formal run must freeze the live endpoint
prices; defaults are not timeless pricing guarantees. Local CPU/probe costs are
reported as time/calls, without inventing a dollar rate. Updater, execution,
artifact repair and judge costs are separated; judge overhead is also excluded
from the reported task-system subtotal. Failed paid requests stay in totals.

Offline: `python scripts/accept_v6.py --inputs FROZEN_INPUTS --output NEW_RECEIPT`.
This checks all nine actual catalogs and stress-tests the case where all tools
are candidates. It makes no API calls and does not establish real model quality.

## Frozen execution and diagnosis

`run-v6` checks the published knowledge and updater acceptance hashes, then saves
a freeze receipt before scored execution. The independent Python `artifact-v1`
protocol, applicable only to Python deliverables, allows at most one repair from
concrete artifact feedback. Tests run against the generated code in a reviewed
pinned Docker image, with the V3 isolation controls. Finite tests do not certify
security. Other task types explicitly declare Python validation not applicable.

Knowledge, artifact acceptance tests and judge rubrics do not change during the
current Evol. Artifact feedback may enter the bounded **code repair** call, never
the tool-knowledge updater. Post-run diagnosis records findings/hypotheses:

| Observation | Follow-up |
|---|---|
| Knowledge stale/missing | Independently establish facts for a future KB version |
| Retrieval/selection/injection mismatch | Inspect delivery while retaining KB content |
| Planning/call/generated-code error | Only predeclared execution/code repair allowance |
| Insufficient evidence/evaluator concern | Preserve uncertainty; investigate separately |

Program checks precede hypotheses, including actual call names and arguments
against the frozen model-facing schemas. Trace events and tool calls are counted
separately. Current diagnosis is conservative, read-only
and makes no additional paid LLM requests. It cannot prove semantic knowledge
correctness or blame the evaluator from TF/PE. The saved runner knowledge is
checked, but its equality alone is not proof of correct model attention or use.
No feedback is automatically used to create another KB in the current run.

The pilot is a previously failing changed cell (Task 133/Middle), followed by the
other eight cells only after pilot infrastructure/coverage/cost/freeze gates pass.
Task quality failures remain failures; a score threshold is not adjusted to let
the pilot pass. Official TF/PE is retained separately from artifact acceptance.

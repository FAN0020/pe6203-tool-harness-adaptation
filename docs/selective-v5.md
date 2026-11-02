# Selective V5: evidence-scoped updates and exact Python artifact validation

V5 starts at `selective-V2` (`bdf0ccc5c3466517725c84e7f715234733cde4a8`).
It adds evidence-scoped local knowledge edits and ports V3's `artifact-v1`
validation/repair implementation. It does not merge main or V4, change the
No Update / Full Rewrite updater, modify historical scores, or report an Evol win.
The historical `adapt` default stays `hybrid_v2`; V5 is an explicit mode.

## 3 November update: program-first scope and lower input volume

The public mode remains `hybrid_v5`. The new audit records
`scope_policy=program_first_light_screen_local_review_v1`; the old V5 checkpoint
is `a97a599790f076b6a48c2e023a7d538e196322f3`. Old acceptance and benchmark
archives are not overwritten.

- The program synchronizes exact metadata first. A directly changed record with
  no stored rules or independent evidence needs no LLM to repeat that operation.
  This certifies metadata synchronization, not behavioral truth.
- The program selects existing rules on changed records and explicit referring
  records for semantic review. Description-only changes also trigger reference
  lookup. Independent evidence events can seed review without a metadata diff.
- A lightweight directory pass sees exact descriptions/rules, compact changed
  fields and any independent evidence. It proposes only additional potentially
  affected or uncertain records. Program-classified items are context, not another
  classification job. No full catalog schema/index is repeatedly sent.
- Candidate IDs are unioned and deduplicated. Each candidate receives one local
  detailed review, with edits returned in that same response. Relevant evidence
  is sent once per local batch; only changed schema leaves are shown. The program
  validates exact coverage, rule indices, evidence and immutable metadata.
- Missing scope receipts, invented IDs, excessive requests or oversized input
  fail explicitly. Nothing is silently truncated or skipped to manufacture savings.
  A negative lightweight screen is not proof of no semantic impact: model recall
  remains an empirical limitation. New independent evidence can start a later
  update event; this update does not repeatedly expand its own scope.

Input characters/UTF-8 bytes are recorded separately from provider token usage.
`measure_v5_scope.py` compares frozen task-free catalogs with original V5. Its
scripted measurements use an explicitly labelled tokenizer proxy; only `--live`
measurements claim actual model input tokens. These are updater diagnostics,
not benchmark completion/quality or universal dependency-recall results.

## Responsibilities and acceptance thresholds

1. **Program:** synchronize authoritative additions/removals/schema/description/
   routing changes using the existing deterministic V1 implementation.
2. **Program:** assign evidence IDs to old/current catalog fields and optional,
   independently frozen source excerpts or probe exchanges. Bind external
   evidence to the benchmark commit, stage and contract fingerprint; verify
   content hashes before any model request. No model copies source quotations.
3. **Program + LLM:** the program resolves metadata operations and explicit
   semantic candidates first. The LLM screens the remaining lightweight directory
   for implicit impact/uncertainty, then reviews the deduplicated candidate union
   once. A local response combines the keep/update/unresolved decision with any
   usage-rule edit, evidence IDs and retained rule indices. No task question,
   answer, judge trace or task-specific acceptance result enters the updater.
4. **Program:** enforce coverage, IDs, field protection, edit scope and argument
   schema examples. Render rule types itself:

   | Rule type | Accepted basis and published scope |
   | --- | --- |
   | `documentation` | Exact current description, explicitly a declaration |
   | `source_observation` | Exact supplied source excerpt, not runtime proof |
   | `probe_observation` | Recorded arguments/check/actual outcome for one exchange |
   | `guidance` | LLM interpretation of current declared evidence, explicitly unverified |
   | `unknown` / `conflict` | Explicit uncertainty; no behavioral promise |

   There is no free-form `behavior_guarantee` type. Literal rules cannot contain
   model paraphrases. Model rule citations must be included in patch citations.
   New schema facts do not wait for behavioral probes. An unresolved review
   withdraws that record's suspect rules and publishes an unknown instead of
   keeping possibly obsolete advice; withdrawn text and reasons stay in the audit.
   Ordinary edits retain explicitly selected unrelated rules. The program cannot
   resolve an `unresolved` record's safe subset, so that terminal action withdraws
   all its rules. If a valid subset is identifiable, the model should instead
   choose `update`, retain that subset and add an explicit unknown/conflict rule.
   The program cannot
   determine natural-language entailment or guarantee that an LLM keeps/removes
   every correct rule. Tests cover both necessary updates and rejected claims;
   no completeness or universally correct semantic judgment is claimed.
5. **Execution agent:** receives the frozen knowledge and chooses its own tools
   and arguments, as before. No new result cache, duplicate-call blocker or
   mandatory workflow is added. Baseline run configurations remain untouched.
6. **Python artifact validation:** before generation, freeze an independent test
   protocol and require the exact V3 JSON artifact contract. Save/hash the exact
   source, statically parse/compile it, then run finite tests in restricted Docker.
   Functional/syntax failure can receive bounded completion-only repair from the
   same execution model; every repair re-enters the checks. There is no host
   execution fallback, runtime installation, image pull or extra repair tool call.

V3 previously appended literal `capability_boundary` observations while retaining
the V2 quoted-rule updater. V5 instead integrates IDs and typed scope into rule
admission, supports task-independent evidence events even when tools/list is
unchanged, and explicitly withdraws unresolved old rules. V3's Python checker is
reused, not claimed as an original V5 mechanism.

## Independent evidence collection

`collect-v5-probes` accepts 1..16 reviewed, predeclared MCP calls (1..30 seconds
each), a frozen catalog and declarative JSON-pointer checks (`equals` / `contains`).
Only `{workspace}` substitution in workspace fields is supported. It verifies
live contract fingerprints, validates arguments, records actual outcomes including
failed expectations, and writes `evidence.json`. No LLM generates executable probe
code or dynamically selects more actions. Source/probe outputs have size limits;
oversized evidence fails without silent truncation. No built-in task-133 fix or
benchmark-answer-derived probe is supplied. Probe plans must be independently
reviewed/frozen before scored task generation; a `reviewed` boolean alone cannot
certify independence or adequacy.

The MCP services use the existing benchmark transport, sanitized child environment
and fresh workspace. This is **not an OS sandbox for native MCP servers**. Only
reviewed archived tools/actions should be used. The separate artifact checker
executes generated Python solely in Docker with no network, no host mounts,
non-root UID, read-only root, dropped capabilities and bounded resources.

Evidence manifests have exactly `version: selective-evidence-v5` and `entries`.
Each entry has `tool_id`, `tool_fingerprint`, `stage`, `benchmark_commit`, `kind`
(`source` / `probe`), relative `path`, and `sha256`. Files stay within the bundle
directory. A source file is a bounded literal excerpt. A probe file contains
exactly the first four subject fields plus `arguments`, `result`, `check`.
`check` has `pointer`, `operator`, `expected`; its outcome is recomputed by the
loader, never trusted from an LLM. Imported files can still be fabricated: hashes
establish byte/subject consistency, not authentic provenance. Even a real probe
supports only its recorded conditions. An unmatched expectation is preserved as
an observation, not relabeled a tool failure or a universally false contract.
Probe-collection time/calls are recorded separately from updater cost; do not
present updater cost alone as end-to-end adaptation cost.

## Commands

Environment/dependencies are the repository's existing `uv sync --frozen` setup.
Do not put API keys in JSON or git; updater config accepts environment names.
All output directories must be new, including failed attempts.

```sh
# Optional: prepare/freeze a reviewed task-independent plan against current metadata.
uv run pe6203 --root . collect-v5-probes --plan reviewed-plan.json --output results/raw/probes-new

uv run pe6203 adapt --strategy selective_patch --selective-mode hybrid_v5 \
  --old-knowledge early-knowledge.json --new-metadata target-metadata.json \
  --evidence-bundle results/raw/probes-new/evidence.json \
  --updater-config updater.json --allow-metadata-api --output results/raw/v5-adapt-new

# Python task: protocol/test suite and image must be prepared independently beforehand.
uv run pe6203 --root . run-v5 --task-id 133 --version late \
  --config configs/full-catalog-smoke.json --adaptation results/raw/v5-adapt-new/adaptation.json \
  --artifact-protocol reviewed-python-protocol.json --output results/raw/v5-python-new

# Other deliverables: explicit non-Python scope; no invented code validation pass.
uv run pe6203 --root . run-v5 --task-id 235 --version late \
  --config configs/full-catalog-smoke.json --adaptation results/raw/v5-charts-adapt/adaptation.json \
  --non-python-deliverable --output results/raw/v5-charts-new
```

`--evidence-bundle` is optional: catalog-only V5 still distinguishes declarations
and unverified guidance; it must not claim independent behavioral verification.
`run-v5` requires a validated `hybrid_v5` adaptation and an explicit Python/non-
Python scope. It rejects hidden adaptation/knowledge overrides. The historical
`experiment` command has not been changed to silently select V5. Use the explicit
entry above; simply checking out this branch does not activate V5.

`examples/qi-v5/artifact-protocol.json` is a **synthetic normalize-function test
fixture**, not a task-133 test suite. Its all-zero image digest is an unusable
placeholder. Prepare task-appropriate tests from independently frozen requirements;
never reuse an old task answer or adapt tests after seeing the scored output.
The final checker is Python-only; charts/project artifacts are outside this
validator's scope. No backend/tests or unsupported dependencies mean unaccepted/
unverified, not passed. Passing finite tests does not prove complete correctness,
security or resistance to an adversarial artifact manipulating its test interpreter.

## Comparisons, accounting and validation

At the user's request, No Update and Full Rewrite retain their historical execution
configuration. V5-only Python testing/repair therefore makes new scores a **full
system comparison**, not an isolated causal effect of selective knowledge updating.
`run-v5` records `knowledge_update_effect_isolated: false` in `v5_protocol`.
Keep original TF/PE and historical results; report generation status, artifact
acceptance, repair origin and updater/actor/repair/probe costs separately. No claim
is made that higher artifact test performance necessarily improves official PE.

```sh
uv run pytest -q -m 'not integration and not artifact_isolation'
PE6203_ARTIFACT_IMAGE='python@sha256:<reviewed-local-digest>' uv run pytest -q -m artifact_isolation
uv run ruff check src integration tests scripts/accept_v5.py
uv run python scripts/accept_v5.py --output results/raw/v5-acceptance-new \
  --image 'python@sha256:<reviewed-local-digest>'
```

The acceptance script uses a **scripted local HTTP API**, not a real LLM: two
metadata updater requests plus initial generation and repair. It exercises public
CLI knowledge generation and the actual SDK/agent loop. With a local reviewed
Docker image it records functional failure → observed feedback → scripted repair
→ exact isolated retest; without it, the honest isolation-gap status remains.
The archived MCPEvol servers and real semantic model quality are not certified by
this synthetic acceptance. See `results/selective-v5/acceptance-summary.json` for
the actual run, tests and limitations. No paid API or Evol run is part of this
development acceptance.

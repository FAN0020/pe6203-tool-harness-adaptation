# QI-V2 Selective Patch: program + LLM

This branch upgrades the updater, not the execution agent. The public
`pe6203 adapt --strategy selective_patch` and `pe6203.baselines.adapt` entries
now default to **hybrid_v2**. The 27-run course results remain evidence for
**deterministic_v1 only**. V2 has implementation acceptance and a synthetic
real-LLM smoke, not a new benchmark result or a demonstrated performance gain.

## Responsibilities and actual execution order

| Step | Owner | Implemented behavior |
| --- | --- | --- |
| 1. Detect and synchronize explicit changes | Program | Reuses the deterministic diff, direct-reference impact analysis and target-metadata patch. Added/deleted records and changed catalog fields are handled without asking the model to invent definitions. |
| 2. Check semantic impact | LLM | Reviews **every surviving record**, in bounded batches. Each request includes the actual changes, the batch's old/target/patched records, and a full-catalog description/rule index. Records outside the deterministic impact set can be selected. Every reviewed ID needs a keep/update/unresolved decision. |
| 3. Propose local rule edits | LLM | A separate request rewrites `usage_rules` only for selected IDs. Both review and edits must cite real diff IDs and exact source quotations covering the edited record and a changed tool. Names, descriptions, schemas and routing remain program-controlled. |
| 4. Validate and test | Program + automated regression suite | Rejects unknown/missing/duplicate IDs, unsupported fields, invented quotes, unresolved edits and truncated outputs. Reuses schema/routing/catalog/unchanged-record validation and checks supplied positive/negative argument cases. Automated tests exercise new-required-input and unchanged-tool cases, incomplete review, failed providers, cost uncertainty and rollback. |

After acceptance, the existing runner receives the frozen knowledge. The same
LLM agent still selects its tools and arguments. This is not an agent that
autonomously detects deployments or decides when to update its own memory.

Implementation: `src/pe6203/hybrid_selective.py`; public dispatch:
`src/pe6203/baselines.py`; CLI: `src/pe6203/cli.py`.

## Run the updater

Install with `uv sync --frozen`. Use a **new** output directory for every attempt.
The following sends the synthetic catalogs to the configured model; it does not
run benchmark tasks, a judge or real MCP tools:

```bash
export OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
# OPENROUTER_API_KEY must already exist in the environment. Do not put it in JSON.
uv run pe6203 adapt --strategy selective_patch \
  --old-knowledge examples/qi-v2/early.json \
  --new-metadata examples/qi-v2/late.json \
  --updater-config configs/qi-v2-updater.template.json \
  --validation-cases examples/qi-v2/validation-cases.json \
  --allow-metadata-api --output results/raw/qi-v2-new-attempt
```

The explicit historical mode is `--selective-mode deterministic_v1`, or context
`{"selective_mode": "deterministic_v1"}` for the shared Python entry. Direct
imports from `pe6203.selective` are the retained V1/core API, not the new public
default. Frozen source archives are unchanged. Never resume an old frozen
experiment using modified V2 source, or relabel old V1 scores/costs as V2.

## Acceptance and evidence

Offline contract/regression tests and local HTTP/SDK/CLI integration:

```bash
uv run pytest -q -m 'not integration'
uv run python scripts/accept_hybrid_patch.py --output results/raw/qi-v2-local-new
```

The second command uses an **explicit local API test double**, not a real LLM.
No production fallback uses those scripted replies. A separate, bounded smoke
can exercise the real provider (at most 2 requests and 120 seconds):

```bash
uv run python scripts/accept_hybrid_patch.py --live --output results/raw/qi-v2-live-new
```

Committed attempt records are under `results/qi-v2/`. Initial local/live attempts
failed the implicit-dependency acceptance check. Their first fixture used an
ambiguous flow and the generic tool name `amount`, which also matched words in
the consumer rule. The first real model chose to preserve that rule. Those
results are retained; they were not rewritten as passes. The revised fixture
explicitly documents the balance-service-to-display flow without naming the
source tool in the consumer rule. Local acceptance 02 and real-LLM smoke 02
passed all acceptance checks. In live smoke 02, the model selected the consumer
outside the deterministic impact set, proposed a unit-conversion rule, and
preserved the unrelated record. This establishes this example only, not recall
over arbitrary dependencies or benchmark superiority.

## Limits, failure handling and costs

- No metadata change means the semantic stages are skipped. Undocumented server
  behavior changes cannot be discovered from identical catalogs alone.
- Complete review coverage means every record received a decision. It does **not**
  mean the LLM found every dependency or that a cited edit is semantically right.
  The global index is a description/rule index, not a complete semantic graph.
- Exact quotes verify provenance, not entailment. A model can cite a real source
  and draw a wrong conclusion. Structural and argument checks cannot prove
  semantic correctness or end-to-end task recovery.
- Argument cases are JSON-Schema regressions. They do not execute real MCP tools.
  Tool behavior, task quality, retention and TF/PE/ECS still need separate V2
  experiments; those were not run here. If no argument cases are supplied, the
  artifact explicitly records an empty list rather than claiming tests ran.
- Requests/time/input size/output size are bounded. Evidence is never silently
  truncated to fit a request. Insufficient budget, missing opt-in, malformed or
  unresolved model output fails the attempt; no V1/Full Rewrite fallback occurs.
- An unsuccessful attempt retains its audit, responses and known/unknown cost;
  it publishes no `knowledge.json`. No output directory is overwritten. This
  implementation does not retry provider requests automatically.
- V2 uses updater LLM calls and therefore has different costs from V1's zero-LLM
  updater. Missing usage/billing stays null. `known_usd` records known charges;
  it is never substituted for a complete total with missing requests.

## Shared presentation

Only slide 4 and its English speaker notes were authorized for this upgrade.
It labels Program and LLM responsibilities and explicitly says later result
slides report deterministic V1; the V2 benchmark is pending. Other slides and
their notes must remain unchanged. Export verification is recorded in
`results/qi-v2/slide4-verification.json`.

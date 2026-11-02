# QI-V3 commands and fair comparisons

Use `uv sync --frozen` and a fresh output directory for each attempt. No command
below installs Docker or pulls an image. The image digest consisting of zeros in
the example is an explicit placeholder: **it is not a released usable image**.
Use only an independently reviewed, already installed Python image digest.

## Evidence initialization (offline synthetic example)

```bash
uv run pe6203 adapt --strategy selective_patch --selective-mode hybrid_v3 \
  --old-knowledge examples/qi-v3/catalog.json \
  --new-metadata examples/qi-v3/catalog.json \
  --capability-evidence examples/qi-v3/evidence.json \
  --output results/raw/qi-v3-evidence-new
```

No catalog change means no updater model call, while evidence enrichment still
runs. For a genuine catalog change, supply the V2 updater options and explicit
`--allow-metadata-api`; V2's full semantic review and quoted local-rule checks
remain required. No task-specific answer repair was added.

An evidence manifest has version `capability-evidence-v1` and entries containing
`tool_id`, `tool_fingerprint`, `kind`, `quote`. Source/probe entries additionally
specify a relative `path` under the manifest directory and exact file `sha256`.
The loader freezes the content before the update. Probe files must be JSON with
exactly `tool_id`, `tool_fingerprint`, `arguments`, `result`; a transcript remains
recorded evidence, not authenticated proof that the probe really ran. Unsupported
semantic assertions are rejected. See `capability.py:fingerprint` for the public
contract fingerprint helper. Do not use benchmark answers, judge trajectories
or acceptance-task outputs as capability evidence.

## User-facing execution

Add the contents of `examples/qi-v3/artifact-protocol.json` as
`artifact_validation` in an ordinary run config. Set its reviewed image digest.
Then use the existing `pe6203 run ... --config ...` entry. The runner performs
initial generation, validation, API-compatible execution-model repair and exact
revalidation; this is not a disconnected reviewer-side demo. Model calls require
the normal configured credentials; this implementation acceptance made none.
The execution callback is asynchronous and uses the same configured SDK/model.

The standalone artifact checker accepts an already generated **full JSON
contract**, not an arbitrary .py file or markdown block:

```bash
uv run pe6203 validate-artifact --answer deliverable.json \
  --protocol reviewed-artifact-protocol.json --output results/raw/check-new
```

This checker has no model callback and reports `repair_not_configured` after a
repairable failure. Exit code 0 means the artifact passed the configured finite
tests; code 2 includes unavailable, untested and failed states. The normal
benchmark run CLI's exit status still denotes official judging completeness;
inspect its separate `execution_status` and `artifact_validation` for artifact
acceptance. Official TF/PE is never replaced with artifact test results.

## Freeze five fair arms before execution

Two questions require separate experiments:

1. Updater-only comparison: fix the historical execution protocol and vary only
   No Update / Full Rewrite / deterministic V1 / hybrid V2 / hybrid V3 knowledge.
2. Execution-protocol comparison: compare the same five arms **all** under
   artifact-v1; if estimating the loop effect, also run all five without it.
   Never give only Selective Patch additional tests, repair calls or tokens.

Prepare five independently generated knowledge files and five run config files.
A plan is:

```json
{
  "version": "artifact-comparison-v1",
  "task_id": 999,
  "stage": "late",
  "seed": 0,
  "arms": [
    {"arm": "no_update", "knowledge": "no-update.json", "config": "no-update-config.json"},
    {"arm": "full_rewrite", "knowledge": "full-rewrite.json", "config": "full-rewrite-config.json"},
    {"arm": "deterministic_v1", "knowledge": "v1.json", "config": "v1-config.json"},
    {"arm": "hybrid_v2", "knowledge": "v2.json", "config": "v2-config.json"},
    {"arm": "hybrid_v3", "knowledge": "v3.json", "config": "v3-config.json"}
  ]
}
```

Task 999 here is illustrative, not a claimed selected benchmark task. Choose an
actual selected task for a real run. Paths resolve from the source plan directory.

```bash
uv run pe6203 freeze-artifact-plan --plan plan.json --output frozen-plan.json
uv run pe6203 run-artifact-arm --plan frozen-plan.json --arm hybrid_v3 \
  --output results/raw/v3-artifact-new
```

Freezing requires exactly all five arms, a shared benchmark commit, early
knowledge for No Update and equal full execution config (apart from operational
paths/updater costs). It compares model settings, tools policy, run timeout,
repair limits/tokens/input sizes, image and independent tests. Knowledge/config
hashes and absolute input paths are stored. The public frozen-arm entry verifies
them again, removes adaptation overrides and uses the exact pinned knowledge;
changed files are rejected. Execution still starts the fixed real task servers
through the normal runner. Tool descriptions/schemas differ by updater arm as the
experimental treatment; accessible environment/tool-name policy is shared.

This freezes inputs and rejects unequal protocols; it does not certify that the
five input files were produced by the claimed updater. Preserve each updater's
validated adaptation audit and verify method labels before scientific use. It
also does not prove test adequacy or independence; the experiment owner must
review and preregister those. Historical raw results remain unchanged and must
not be pooled with the new protocol. Report updater cost and generation/repair/
validation cost separately, including missing charges and stopped attempts.

## Acceptance commands and evidence levels

```bash
uv run pytest -q -m 'not integration'
uv run ruff check src integration tests scripts/accept_qi_v3.py
uv run python scripts/accept_qi_v3.py --output results/raw/qi-v3-local-new
```

The last command uses a **scripted local HTTP server** and the real OpenAI SDK
against the public CLI/runner. Without a backend it demonstrates syntax failure
→ API repair request → revised exact artifact → static pass → unavailable;
this is not isolated functional execution or a real LLM result. On an accepted
Docker machine, supply `--image <reviewed-local-image@sha256:...>` to exercise
actual functional failure → scripted API repair → isolated retest.

Actual isolated boundary and early-exit regression tests:

```bash
PE6203_ARTIFACT_IMAGE='<reviewed-local-image@sha256:...>' \
  uv run pytest -q -m artifact_isolation
```

They check benign and negative behavior, ordinary exit-zero bypasses, artifact
mutation, fresh containers, non-root UID, absent host marker/env secret, root
filesystem write denial, network connection denial and timeout. With no pinned
image/backend they **skip with explicit reasons**, never mock an isolated pass.
Synthetic/mock tests cover orchestration, scope/provenance, rejected assertions,
repair exhaustion, no artifacts/tests/backend, missing dependencies/resources,
shared budgets, exact source bytes, SDK failure/cancellation accounting and
outer-run timeouts. They do not establish hostile-evaluator robustness or model
reasoning quality. See `results/qi-v3/acceptance-summary.json` for actual outcomes.

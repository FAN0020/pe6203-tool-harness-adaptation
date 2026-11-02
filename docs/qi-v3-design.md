# QI-V3: capability evidence and exact-artifact validation

QI-V3 branches from QI-V2 `bdf0ccc5c3466517725c84e7f715234733cde4a8`.
It adds two separately versioned mechanisms. On 2026-11-03 its updater input
pipeline was optimized using V5's program-first scope policy. This does not by
itself establish a benchmark improvement.

## V2 versus V3

| Responsibility | QI-V2 | QI-V3 |
|---|---|---|
| Metadata diff / direct impact / protected catalog fields | Program | Reuses V2 unchanged |
| Semantic scope after a metadata change | LLM reviews all surviving records | Program completes metadata-only records; LLM screens a lightweight directory and reviews the deduplicated candidate union |
| Local usage-rule edits with diff IDs and source quotes | Separate review and patch requests | One combined local review/edit; same quote, field and argument gates |
| Capability evidence / object boundary | No explicit evidence object | Program adds literal evidence, subject fingerprint and limitations |
| No metadata diff | Skips semantic model stages | Same; independently supplied evidence can still initialize boundaries |
| Execute exact final Python | None | Optional shared `artifact-v1` protocol |
| Failed artifact → execution-model repair → repeat checks | None | Bounded; every proposed final repair is checked again |

Select `hybrid_v3` explicitly. The V3 branch retains its historical
`hybrid_v2` default; main preserves its existing `deterministic_v1` default.
Merging this V3 optimization does not implicitly switch main's default strategy.
Historical `deterministic_v1`, V2 APIs and default benchmark configurations remain
available. V1 course scores, V2 implementation tests, V3 mechanism acceptance,
and any future artifact-protocol scores are different evidence sets.

## 2026-11-03: reduced updater input

`hybrid_v3` now uses `scoped_selective_v3.py`, with
`updater_core_version=hybrid_v3_program_first_v1` and
`scope_policy=program_first_light_screen_local_review_v1`.
The historical V2 engine remains unchanged.

1. The program synchronizes authoritative metadata. A changed tool without
   stored rules is program-complete; it is not redundantly reviewed by the LLM.
2. The program seeds rule-bearing changed records and explicit referring rules.
   Description changes also trigger reference lookup.
3. One lightweight directory screen proposes implicit impacts or uncertainty
   among the remaining records. It receives descriptions/rules and exact changed
   leaves, not full schemas, a repeated global index, or three record copies.
4. The deduplicated seed/proposal union is batched for one local review/edit
   per record. Only relevant changes and compact source views are supplied.
   Keep/update/unresolved and any usage-rule edit share one model response.
5. Existing exact-quote, edit scope, schema/routing, and argument regression
   checks remain. Unresolved reviews fail closed without an accepted snapshot.
6. The existing literal capability-evidence layer runs separately; the optional
   shared Python artifact/repair loop is unchanged.

Missing/duplicate coverage, invented IDs/quotes, metadata edits and insufficient
budgets fail explicitly. Inputs are not silently truncated and no fallback to
V1 or a repeated scope-expansion loop is added. A negative screen can miss an
implicit dependency; hashes/quotes do not prove semantic entailment. Input
characters, UTF-8 bytes and provider-reported tokens are distinct measurements.

The no-change artifact wrapper records the requested target stage even when its
knowledge bytes reuse Early K0. This fixes Middle/Late execution preflight
without rewriting metadata, inventing a diff, or calling an updater model.

Evidence and the original diagnostic-checker correction are retained under
`results/qi-v3/scope-input-20261103/`. Existing 22/27 scored benchmark records
predate this optimization; new updater diagnostics are not new TF/PE scores.

## A. What the capability layer actually establishes

`capability.py` adds `capability_boundary` without rewriting names, descriptions,
schemas, routing, or existing rules. Source types are:

* `catalog`: exact substring of the current tool description. Its object is the
  **declared tool contract**, not observed behavior.
* `source`: exact excerpt from an independently frozen, hash-matched source file.
  Its object is the **tool source excerpt**, not a proof of runtime behavior.
* `probe`: exact excerpt from a hash-matched JSON exchange containing tool ID,
  tool fingerprint, arguments and result. The boundary carries the recorded
  arguments. Its scope is **that recorded input/result exchange only**.

These are literal observations. Arbitrary `establishes`, semantic assertions,
model opinions and invented quotations are rejected. No model infers a guarantee
from a quote. A recorded prompt template is guidance; neither it nor evaluation
of a remote expression executes the new local Python artifact. The same generic
limitation is supplied to the execution agent for every boundary.

The fingerprint covers identity, description, parameters, output schema and
routing; stage labels and locally learned rules are excluded. Changed contracts
invalidate stale evidence. Changed evidence is tracked as initial enrichment,
change propagation or evidence refresh. Missing evidence produces
`unresolved_no_evidence`, including on unchanged records. Previous boundary
fields are stripped and rebuilt; stale claims are not carried forward silently.
Unchanged non-boundary fields remain protected by V2 validation.

**Trust boundary:** hashes prove byte identity, not authentic origin, truthful
probe execution or semantic entailment. An experiment owner must independently
review and freeze source/probe provenance before task execution. No source fetch,
probe execution or automatic capability discovery is claimed. The updater model
receives only scoped catalog views and exact metadata deltas, never the capability
evidence bundle, artifact tests, answers or judge traces.
Unstructured semantic capability inference remains outside this conservative V3.
Synthetic examples demonstrate the mechanism, not genuine server capabilities.

## B. Exact-artifact execution protocol

`artifact-v1` is explicitly enabled through `config.artifact_validation` in the
existing public runner; its default behavior stays unchanged when absent.
The initial model receives an exact JSON artifact contract (one `artifact.py`
plus a summary). Ambiguous markdown, paths, languages, oversized/empty artifacts
and incomplete JSON are not executed. Each attempt's UTF-8 source bytes are
stored, hashed and statically parsed/compiled without host execution.

Tests and their kinds (`benign` / `negative`), container image, time/output/source
limits and repair budgets are validated and frozen **before generation**. Test
source is supplied by the experiment owner, never constructed from scored task
outputs. Only the configured container backend can execute artifacts or tests.
Static success alone is never behavioral success.

For a valid artifact with tests and an available backend, each test starts a
fresh container with the same original artifact bytes. The driver records
before/after artifact hashes, normal test-completion marker, exit status and
bounded output. A zero exit without normal completion (e.g. `SystemExit(0)` or
`os._exit(0)` during import), or a changed artifact hash, fails. Separate
containers prevent files/background processes from contaminating the next test.

Observed functional/syntax failures go to the **same execution model**, with
its existing conversation and frozen tool history. Repairs are completion-only;
no extra tool actions are allowed. All arms use the same repair policy. The
response must satisfy the artifact contract and re-enter the full validation
pipeline. Default repair allowance is one; configuration caps it at three.
Request characters, output tokens, timeout and total number of requests are
bounded. Failed/unknown-charge requests remain unknown in accounting.

A pass publishes the exact accepted source/hash, its corresponding summary and
`passed_finite_tests`. Failure publishes an explicit unaccepted envelope and
retains every draft/feedback plus the latest preserved artifact. The last repair
cannot bypass checks. `generation_status`, `completion_origin` and artifact acceptance are separate.
Accepted repair outcomes retain `execution_status=completed` for existing
completion aggregates; `completion_origin=artifact_repair` identifies repairs.
Unaccepted artifacts use `execution_status=artifact_unaccepted`.
The artifact audit is separate from official TF/PE; disagreements are retained.

## Isolation and verification assumptions

Only an already-installed Docker CLI/daemon and an independently reviewed local
Python image pinned by `@sha256:...` are supported. No images are pulled and no
runtime is installed. Every test uses `--network=none`, UID/GID 65534, read-only
root, no added capabilities, no-new-privileges, bounded CPU/memory/PIDs/file size,
no host bind mounts or host environment credentials, and a size-limited tmpfs.
The Docker client environment is sanitized; this implementation uses the default
local daemon/context. Custom credential-bearing Docker endpoints are not passed
through. Reviewed images must contain Python and must not contain secrets or
untrusted initialization code. Image immutability is not a security audit.

Host-side subprocesses run only the trusted Docker CLI. Generated Python and test
Python are never executed/imported on the host. `ast`/`compile` are static checks.
Timeout/output-limit/cancellation kills the CLI and force-removes its named
container. Cancellation requests backend cleanup and waits up to seven seconds;
Docker cleanup failures may require operator inspection. There is no host,
macOS `sandbox-exec`, or subprocess/tempdir fallback.

Completion markers and hashes catch ordinary early exit/mutation; this is **not
a tamper-proof adversarial evaluator**. Deliberately hostile Python can manipulate
its test interpreter (e.g. monkey-patch globals). Tests, the driver, local daemon,
image and kernel are trusted. Finite passing tests do not prove full functionality
or security. Stronger hostile-artifact attestation is future work.

The original V3 acceptance environment had no Docker/Podman, so its historical
records honestly retained `backend_unavailable`. The 2026-11-03 scope-update
acceptance uses an already-installed pinned Docker image and separately records
actual finite-test execution and repair/retest results. See the new acceptance
evidence; neither the old result nor the current finite checks prove full safety.

## Honest terminal statuses

| Status | Evidence / publication |
|---|---|
| `no_artifact` | No unambiguous executable deliverable; no execution |
| `syntax_failed` | Static observed failure; eligible for bounded repair |
| `no_tests` | Static check only; behavioral scope untested |
| `backend_unavailable` | Static check only; no isolated execution |
| `backend_error` | No trusted complete backend result; unaccepted |
| `unsupported_dependencies` | Observed missing module in the configured isolated image; no install/guess |
| `timeout` / `resource_failure` | Incomplete checks; unaccepted, no model repair guess |
| `test_failed` | Observed supplied-test failure; eligible for bounded repair |
| `passed_finite_tests` | All supplied tests normally completed for the hashed artifact; finite scope only |
| `cancelled` | Interrupted; audit/drafts retained, cleanup requested |

A repair attempt has an additional termination reason (`repair_exhausted`,
`repair_failed`, `repair_not_configured`). No artifact is called accepted unless
all configured finite tests pass. A mock can exercise orchestration internally,
but must retain `isolated_execution=false` and identify itself as a test double.

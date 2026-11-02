# QI-V3: capability evidence and exact-artifact validation

QI-V3 branches from QI-V2 `bdf0ccc5c3466517725c84e7f715234733cde4a8`.
It adds two separately versioned mechanisms. It does not report a benchmark
improvement. User approval of the parent chat's flowchart remains pending.

## V2 versus V3

| Responsibility | QI-V2 | QI-V3 |
|---|---|---|
| Metadata diff / direct impact / protected catalog fields | Program | Reuses V2 unchanged |
| Review every surviving record after a metadata change | LLM, bounded | Reuses V2 unchanged |
| Local usage-rule edits with diff IDs and source quotes | LLM proposes; program checks | Reuses V2 unchanged |
| Capability evidence / object boundary | No explicit evidence object | Program adds literal evidence, subject fingerprint and limitations |
| No metadata diff | Skips semantic model stages | Same; independently supplied evidence can still initialize boundaries |
| Execute exact final Python | None | Optional shared `artifact-v1` protocol |
| Failed artifact → execution-model repair → repeat checks | None | Bounded; every proposed final repair is checked again |

The public `adapt` default remains `hybrid_v2`. Choose `hybrid_v3` explicitly.
Historical `deterministic_v1`, V2 APIs and default benchmark configurations remain
available. V1 course scores, V2 implementation tests, V3 mechanism acceptance,
and any future artifact-protocol scores are different evidence sets.

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
receives only V2's catalog inputs, never artifact tests, answers or judge traces.
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

On this acceptance machine Docker/Podman are unavailable. Actual isolated
execution and functional-failure → repair → isolated-retest acceptance are
**not verified**. OS sandbox-exec exists but has not been accepted as a sufficiently
restricted backend. No heavy runtime/VM installation was authorized or attempted.
The mechanism fails closed with `backend_unavailable`.

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

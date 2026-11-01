# PE6203 research report reproduction

This is the integrated local entry point as of 1 November 2026. The report does
not certify the research Goal: strict original-benchmark development has not
passed and the two formal validation batches have not started. Presentation
slides and speaker scripts are outside current scope, following the user's
update that the presentation has ended.

## Verify this synthesis without models

Run from the repository root, on the existing branch:

```sh
uv run python reports/course-research/verify_report.py
```

The standard-library verifier checks all synthesis source hashes, recomputes
baseline means and ECS from 27 individual rows and development metrics from 30
individual rows, and checks the actual DOCX tables. It also checks the existing
course archive checksum without extracting it. It does not call the network,
models, native tools or any benchmark runner. A passing result means this
report matches its declared evidence; it does not establish experiment success
or independently validate the human product judgments.

## Rebuild the document

The builder requires Python 3.10 or newer and `python-docx==1.2.0` (already
available in the bundled document runtime used for this delivery). Set
`DOCX_PYTHON` to that Python executable, then run:

```sh
"$DOCX_PYTHON" reports/course-research/build_report.py
uv run python reports/course-research/verify_report.py
```

The builder writes the DOCX, its Markdown text, exact table data and input
manifest. These are synthesis outputs; it never changes the experiment data.
Regeneration records current input hashes, so run the verifier **before** a
rebuild if testing the originally delivered input snapshot. The builder records
the inspected source commit `d5d8a89`; it does not claim DOCX ZIP-byte identity
across builds. Render using the documents skill's `render_docx.py` and inspect
all pages after any layout or content change. The delivered file was rendered
and reviewed on all nine pages; no slides or speaker scripts were generated.

## Authoritative experiment packages

| Cohort | Evidence directory relative to repository root | Replay entry |
| --- | --- | --- |
| Course NU / FR / SP, 27 runs | `results/evidence/course-v1.3-20261031` | `reproduction.json` |
| Daily migration, 12 exposed runs | `results/evidence/daily-migration-pilot-20261031` | `reproduction.json` |
| Semantic claim repair, 6 original runs | `results/evidence/semantic-claim-repair-20261101` | `reproduction.txt` |
| Dependency cut, 10 original runs | `results/evidence/dependency-cut-20261101` | `reproduction.txt` |
| Observation coverage, 10 original runs | `results/evidence/observation-coverage-20261101` | `reproduction.txt` |
| Ready link, 10 original runs | `results/evidence/ready-link-20261101` | `reproduction.txt` |
| Dependency factorial, 16 synthetic runs | `results/evidence/dependency-factorial-20261101` | `reproduction.txt` |
| Observation selection, 16 synthetic runs | `results/evidence/observation-selection-20261101` | `reproduction.txt` |

These directories retain original plans, knowledge, raw archives, product
reviews, scores, positive and negative results, cost ledgers and verification
code. This entry reuses those packages; it does not create a misleading second
copy or merge the cohorts. The course archive is `raw-trial.tar.gz`, SHA256
`e95e15694abe9a12e37c813f81e6e0fb0b5ccd00c2003f2a25a36a092c8001c9`.

Historical course offline replay must use the implementation **inside that
archive**, as described in `reproduction.json`. Do not run its old `verify.py`
against evolving current source and assume a mismatch means the original study
failed. That file checks original frozen source paths and also writes audit
outputs. The archived report command is:

```text
PYTHONPATH=<extraction>/implementation/src:<extraction>/implementation
python -m pe6203.cli experiment report
  --output <extraction>/course-v1.3-final-20261031
```

The environment assignment and command above describe one shell invocation;
replace `<extraction>` with a separate local archive extraction directory.
Offline replay was verified in the original study with credentials removed and
sockets blocked. This synthesis does not claim to have rerun that old replay.

Ready link's existing offline evidence audit is:

```sh
uv run python results/evidence/ready-link-20261101/verify_development.py
```

Its detailed reproduction file distinguishes evidence recomputation from
native probes and model execution. Some historical verifiers regenerate their
derived JSON files; preserve original hashes when independently replaying them.

## Frozen execution versus future work

The original benchmark commit is
`888c779a0fe735f612ca62bdd1fdd7c9e6bf8701`; dataset revision is
`162e3ffbea1717ac8a20fe9b26465e29117229e4`.

At the integrated report snapshot, consult `experiments/ready-link-v1.json`, model
freeze `a95ad2d`, product-review freeze `89cfd3d` and final archive `ed329e5`.
The exact knowledge, original tasks, isolated task-state directories, fixed
provider/model/decoding, 4096-token single response limit, 12 rounds, scoring
protocol and per-study ledger are evidence, not knobs to change during replay.
The current research branch and worktree must remain in place for this task.

No command here authorizes a fresh inference replay of a closed candidate.
Future research requires a justified distinct mechanism, a pre-call freeze,
new output paths and independent ledgers. It may not overwrite old failures,
retune acceptance after outcomes, feed original questions/answers/scored traces
to the updater, or count exposed development as unseen validation. Source
archives and the report contain no API key; live model execution would require
local ignored environment credentials and fresh authorization within scope.

## Delivery boundary

The integrated report covers the measured course comparison and selected
mechanism tests, with explicit unresolved causal cases. It is not a claim that
every course requirement is satisfied. No repository push, deployment or
external submission was performed. The report and this reproduction entry are
local deliverables; the original strict dual-improvement Goal remains active.

## Later research addendum: instruction-scope, 2026-11-01

The subsequent15-cell original development is recorded in
[the instruction-scope result](../../results/evidence/instruction-scope-20261101/RESULT.md)
and [offline reproduction index](../../results/evidence/instruction-scope-20261101/reproduction.json).
Main candidate changed-task completion was1/4 versus SP2/4; actual product core
was0/4 for both. The project subset remained0/2 on both measures. Full TF and
retention TF also declined. The candidate was closed without validation;
the quote control was ineligible for promotion. Cost: USD0.308363940,171 settled
requests; all15 product reviews committed before unblinding. This addendum does
not rewrite the dated integrated-report cohort or substitute for the unmet Goal.

Offline, with no model calls or credentials:

```sh
uv run python results/evidence/instruction-scope-20261101/verify_development.py
uv run python results/evidence/instruction-scope-20261101/audit_execution.py
```

The verifier documents one reporting-only native-call label correction, with the
original frozen source and output preserved. Source/raw archives, judgments,
all scores and dedicated costs remain available. No slides or speaker-script
edits: the user stated that the presentation has ended.

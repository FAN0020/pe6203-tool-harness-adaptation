# Versioned evaluation code

This directory publishes the actual evaluation code, frozen configuration and
source provenance separately from main's active Selective implementations.
Packaging or merging an evaluation does not promote a strategy as best, change
scores, enable code validation for existing baselines, or run paid requests.

## Current reporting scope: 133 / 235 / 283

V3, V5 and the original V6 now share the same reporting task IDs. Start with
[V3's three-task view](v3/three-task-view/README.md),
[V5's three-task view](v5/three-task-view/README.md), and
[the frozen V6 package](v6/README.md). V3/V5 show first attempts and a separately
labelled once-retry supplement; this offline scope view does not rewrite any
historical four/five-task study or imply identical providers, repeats or artifact
protocols. Later V6 development changes are not included in this branch.

The active three-task V3/V5 evaluator is `scripts/eval_v35_three_tasks.py`.
Preparation and execution require a fresh output directory; paid execution still
requires explicit `execute` and credentials. The archived four-task evaluators
below remain byte-identical historical reproduction tools.

Regenerate only the derived summaries, with no API calls:

```sh
python scripts/build_three_task_views.py
```

| Label / branch | Directory | Publication scope |
| --- | --- | --- |
| evaluation 2 / `evaluation-2` | `v2/` | Original V2 evaluation engine, protocol and recorded partial results |
| evaluation 3 / `evaluation-3` | `v3/` | Current three-task reporting view; historical 108-trajectory study retained |
| evaluation 5 / `evaluation-5` | `v5/` | Current three-task reporting view; historical 72-trajectory study retained |
| evaluation 6 / `evaluation-6` | `v6/` | Gated V6 evaluation, offline checks, cost analysis and retained diagnostic attempts |

Start with each version's README and manifest. Batches carry exact source Git
revisions, task sets, provider/protocol differences and readiness. Do not pool
historical artifact-enabled evaluations with later knowledge-only experiments.
The latest V3 evaluation is now completed and verified. Its 108-trajectory
knowledge-only study is separate from the historical partial 22/27 V3 record.
Evaluation 2/3/5/6 packages are available without promoting a default strategy.

## Offline commands (no API calls)

```sh
python evaluation/manage.py list
python evaluation/manage.py verify --version 2
python evaluation/manage.py verify --version 3
python evaluation/manage.py verify --version 5
python evaluation/manage.py verify --version 6
python evaluation/manage.py verify --all
python evaluation/manage.py extract --version 6 --artifact runtime --output outputs/v6-recorded-source
```

`verify` checks all published hashes, every archive member, evaluator Python
syntax and known credential patterns. It never imports archived evaluator code,
reads a private env file, changes scores or sends model requests. Raw generated
artifacts may legitimately contain syntax failures and are preserved as evidence.
`extract` refuses existing output directories and unsafe archive paths/links.

The original scripts are copied without changing their algorithms; old local
paths in historical scripts are provenance, not portable defaults. Frozen source
archives include the runtime used in each batch. Re-running a paid experiment
requires a fresh output directory, matching archived source/protocol, installed
MCPEvol services and separately supplied credentials. See version READMEs for
parameterized current tools and original entry points. Secrets, local env files,
virtual environments, node_modules and benchmark release caches are excluded.

## Integration verification

See [integration-verification.json](integration-verification.json). Evaluation
2/5/6 package and recorded-result checks passed. The added 15 tests passed;
no new repository-test failures were introduced. The pre-existing main baseline
had 22 failing tests (missing untracked research fixtures plus one artifact
assertion) and 416 lint issues; the integration reproduced the same failures.
That earlier check is retained as historical context. The current optimized-V3
integration restored the ignored historical fixtures and the installed Node
path, then passed 945 repository tests with no failures or skips (15 native
integration tests deselected). See v3/integration-verification.json. Current V3
now has a completed controlled evaluation and verified merge candidate.

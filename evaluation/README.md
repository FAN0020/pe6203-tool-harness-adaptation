# Versioned evaluation code

This directory publishes the actual evaluation code, frozen configuration and
source provenance separately from main's active Selective implementations.
Packaging or merging an evaluation does not promote a strategy as best, change
scores, enable code validation for existing baselines, or run paid requests.

| Label / branch | Directory | Publication scope |
| --- | --- | --- |
| evaluation 2 / `evaluation-2` | `v2/` | Original V2 evaluation engine, protocol and recorded partial results |
| evaluation 3 / `evaluation-3` | `v3/` | Verified optimized V3 evaluator, frozen protocol and completed 108-trajectory / 540-rating knowledge-only study |
| evaluation 5 / `evaluation-5` | `v5/` | Historical V5 evaluation plus later knowledge-only 72-trajectory study and scope measurements |
| evaluation 6 / `evaluation-6` | `v6/` | Gated V6 evaluation, offline checks, cost analysis and retained diagnostic attempts |

Start with each version's README and manifest. Batches carry exact source Git
revisions, task sets, provider/protocol differences and readiness. Do not pool
historical artifact-enabled evaluations with later knowledge-only experiments.
The latest V3 evaluation is now completed and verified. Its 108-trajectory
knowledge-only study is separate from the historical partial 22/27 V3 record.
Evaluation 2/3/5/6 packages are available without promoting a default strategy.

## Five-task supplement (2026-11-03)

The current report treats V6 as the primary method and V1 as a historical
reference. [The five-task supplement](supplements/five-task-20261103/README.md)
adds a fresh V3/V5 study on tasks 133/235/283 and fills task 430/90 gaps for
V1/V2/V6 with contemporaneous, unchanged No Update and Full Rewrite controls.
All conditions have three planned actor executions in each new batch. Failed
knowledge updates remain explicit blocked conditions without invented scores.
The supplement retains the original V6 first-pass results and separately
preserves its previously selected repeat. Cross-batch coverage is not a
controlled five-task version leaderboard and does not promote a default method.
Its raw requests, receipts, source archive and offline verification are separate
from the version packages managed by `evaluation/manage.py`.

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

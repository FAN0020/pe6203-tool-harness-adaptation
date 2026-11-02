# Versioned evaluation code

This directory publishes the actual evaluation code, frozen configuration and
source provenance separately from main's active Selective implementations.
Packaging or merging an evaluation does not promote a strategy as best, change
scores, enable code validation for existing baselines, or run paid requests.

| Label / branch | Directory | Publication scope |
| --- | --- | --- |
| evaluation 2 / `evaluation-2` | `v2/` | Original V2 evaluation engine, protocol and recorded partial results |
| evaluation 3 / `evaluation-3` | Not merged | Pending and unavailable by owner instruction; no valid current V3 eval claim |
| evaluation 5 / `evaluation-5` | `v5/` | Historical V5 evaluation plus later knowledge-only 72-trajectory study and scope measurements |
| evaluation 6 / `evaluation-6` | `v6/` | Gated V6 evaluation, offline checks, cost analysis and retained diagnostic attempts |

Start with each version's README and manifest. Batches carry exact source Git
revisions, task sets, provider/protocol differences and readiness. Do not pool
historical artifact-enabled evaluations with later knowledge-only experiments.
The latest/current V3 evaluation is explicitly pending; old V3 records cannot
stand in for it. Only evaluation-2, evaluation-5 and evaluation-6 are merge targets.

## Offline commands (no API calls)

```sh
python evaluation/manage.py list
python evaluation/manage.py verify --version 2
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
This is a scoped evaluation-code acceptance, not a claim that the entire
repository CI is green. Current V3 remains unvalidated and unmerged.

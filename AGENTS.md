# Agent working instructions

This repository is PE6203 Project 4, Tool Harness Adaptation under Environment Change. Communicate in Chinese with English technical terms when useful.

## Read order

1. `README.md` for implemented capabilities and current limitations.
2. `docs/project-brief.md` and `docs/plan/sources.md` for course requirements and provenance.
3. `docs/plan/README.md`, `docs/plan/project-spec.md`, `docs/plan/evaluation-protocol.md`, and `docs/plan/interfaces.md` for the adopted project design.
4. `experiments/protocol.v1.json`, `experiments/backlog.json`, and the relevant task review for executable work planning.
5. `docs/group-a-handoff.md` and actual implementation before changing interfaces.

The course brief governs assignment requirements. The plan defines our design choices; it does not prove implementation or experimental success. User instructions remain controlling. If JSON and prose disagree, report and reconcile the discrepancy before executing dependent experiments.

## Status and scope

- `experiments/` currently contains planning records, not runnable `pe6203 run --config` files.
- `null` means unresolved or unmeasured. Never replace it with a guessed model, score, task ID, or cost.
- Candidate tasks are not the frozen evaluation set. Task 139 is reserved for development because it has already been used for debugging.
- Current runtime accepts any selected task with a complete reviewed server set. Eight profiles cover five task server sets; fixtures and task success are separate gates. Full 201-task inventory, complete catalogs and a conservative resumable batch runner are available; one real task-139 Early / No Update development smoke now has five valid judge results (see `docs/baseline-smoke.md`). Broader real model evaluation, more service reviews, LLM adaptation algorithms and formal analysis remain open. Read `docs/full-benchmark.md` for evidence and known upstream failures.
- Real MCP transport evidence is not a real model evaluation. Mocks test software wiring only.
- Sprint 1 No Update / deterministic Full Rewrite are integrated in `src/pe6203/baselines.py`; see `docs/baseline-smoke.md`. This prototype is not the planned LLM semantic rewrite. Current smoke uses full catalogs; obsolete four-tool knowledge and duplicate metadata were removed.
- Only mark an item `done` after linking concrete evidence and verifying its acceptance criteria. Files in `reports/templates/` are not results.

## Experiment integrity

- Keep the model, decoding settings, judge, task set, fixtures, and execution harness fixed across strategies.
- Preserve official task IDs and text. Do not expose reference answers, reference trajectories, historical scores, or mutation ground truth to the agent or adaptation method.
- No Update must keep Early knowledge. Runtime tool discovery must not silently refresh its schemas, descriptions, or routing.
- Use the fixed official server set for each task. Knowledge covers those servers’ complete catalogs; the obsolete four-tool task-139 smoke example was removed.
- Main comparisons independently adapt Early knowledge to Middle and Late. Sequential adaptation is a separately labeled optional experiment.
- Use isolated resettable state and retain failed attempts. Never select the best rerun or fill missing scores with zero.
- Keep development and evaluation tasks separate. Do not tune against final evaluation outcomes.
- Preserve upstream snapshots and labels. Document source/code discrepancies and any fixture substitutions.

## Repository work

Inspect Git status and relevant files before editing. Preserve unrelated work. Use a task branch for implementation and commit only task-owned changes. Follow the user's requested push/merge scope; do not infer permission for unrelated messages, account changes, or publication.

Do not put keys or local `.env` contents in Git. Runtime caches and raw outputs are ignored. Publish reviewed, redacted evidence with provenance rather than exposing local secrets or unrelated files.

For documentation changes, validate JSON syntax, cross-file consistency, local Markdown links, and `git diff --check`. For runtime changes, use relevant tests and real MCP checks when required. From the repository root:

```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run pytest -q
```

Tests requiring upstream snapshots may skip before bootstrap. Record skips; do not call them real MCP validation. See README for bootstrap and pinned Node setup. API keys and model endpoints are required for actual model runs.

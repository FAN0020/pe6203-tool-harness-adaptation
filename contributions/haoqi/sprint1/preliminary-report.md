# Selective Patch v1 — Preliminary Report

Author: HaoQI (`haoqi016`) · Branch: `HaoQI_V1` · Date: 2026-10-20
Scenario: scientific research — paper retrieval → webpage (task 223 planned; task 139 used for the verified adaptation example).

This is a **developmental** report. It records what actually ran; it is not a
benchmark scoreboard and makes no claim that Selective Patch beats either
baseline.

## 1. What was built

`src/pe6203/selective.py` implements the Diff-guided Selective Patch:

1. deterministic metadata diff (tool add / remove; parameters, description, output_schema, routing changes)
2. explicit one-hop reference index over `usage_rules`
3. impact localization (changed tools + records referencing them)
4. selected-record rewrite (structured fields grounded in target metadata; never invented)
5. schema / routing / unchanged-record validation
6. atomic artifact write + deterministic cache key

Common entry `adapt(old, new, strategy, context)` and `write_adaptation` dispatch
to it; the runner consumes the produced snapshot exactly like the baselines. All
common changes are listed in [COMMON_AGENT_CHANGES.md](../../../COMMON_AGENT_CHANGES.md).

## 2. What actually ran (real, this machine)

| Activity | Status | Detail |
| --- | --- | --- |
| Dependency install | **done** | `uv sync --frozen`, 42 packages |
| Offline test suite | **done** | `75 passed, 5 skipped (integration), 10 deselected` |
| Lint / format | **done** | `ruff check` clean; `ruff format --check` clean |
| Adaptation on real task139 catalogs (early→late) | **done** | 40→44 tools: 10 replaced + 4 added, 30 untouched; validation errors 0 |
| LLM updater call | **not_run** | gated; no `UPDATER_API_KEY` / verified model id |
| Real tool probes during validation | **not_run** | `max_probe_calls=0` (off by default) |
| Real agent task execution (task 223 / task139) | **not_run** | needs `bootstrap` (released Node services) + agent/judge keys |
| TF / PE / ECS comparison | **not_run** | requires the full three-strategy matrix + official judge |

### Real adaptation cost (task139, early→late)

```json
{
  "method": "deterministic_diff_selective_patch",
  "calls": 0,
  "total_tokens": 0,
  "usd": 0.0,
  "seconds": 0.1183,
  "update_operations": 14,
  "untouched_records": 30
}
```

Tokens/USD are genuinely **0** because the deterministic path performs no model
calls; this is measured, not an estimate. Full artifact:
`results/raw/haoqi-selective-v1/task139-early-late/` (gitignored); readable
trimmed copy:
[task139-early-to-late.sample.json](examples/task139-early-to-late.sample.json).

## 3. Synthetic diagnostics (clearly not benchmark results)

`tests/test_selective.py` covers the task-brief matrix: no-change skip,
add/remove, parameter/description/output changes, dependent-rule flagging,
dangling-rule removal, missing-evidence honesty, mixed-source rejection,
hard-failure rollback (never silent full rewrite), cache-key variation and
knowledge isolation.

A controlled case shows: when the output location moves (tool `old_tool`
`output_schema` changes) and a `publisher` rule says "take the body from
old_tool's result", the deterministic path **keeps** the rule and records a
`needs_semantic_rewrite` unresolved item rather than fabricating a fix. When a
referenced tool is removed, the now-dangling rule is **dropped** (recorded),
never left as an invalid reference.

## 4. under-update / over-update

- No real under-update or over-update failure has been observed yet (no real task
  runs). Per protocol this requirement is **unmet**, not assumed.
- Synthetic diagnostics above exercise both directions but do not substitute for
  real trajectory-based attribution.

## 5. Blockers (single most important first)

1. **The released three-stage environment and task223 profiles are not
   bootstrapped on this machine**, and the two task-223 servers
   (`fetcher-mcp`, `edgeone-pages-mcp`) have no reviewed profiles; live-source
   time and publish setup are unfrozen. This blocks any real TF/PE/ECS result.
2. The optional updater's model id / request params are unverified against a live
   service; `UPDATER_API_KEY` unset.

## 6. Next step

Bootstrap the pinned services (`uv run pe6203 bootstrap --scope smoke`), review
the task-223 server profiles and freeze the fetch-time / publish setup, then run
the first real `task 223 × Selective patch` end-to-end and hand the shared
interface to teammates for matched No-update / Full-rewrite runs.

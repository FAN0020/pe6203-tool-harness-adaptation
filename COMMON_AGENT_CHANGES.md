# Common Agent Changes

Records every change to the shared base so the three strategies (No update, Full
rewrite, Selective patch) stay auditable and comparable. Sections A–C are
observed facts of the current repository; D is what this branch changed. Nothing
here is a paper-original implementation.

## A. Shared execution base (unchanged by this branch; applies to all 3 strategies)

The repository's execution layer (`src/pe6203/runner.py`) is the shared task
executor used by **every** strategy. It is an adapter over the vendor agent
(`vendor/SimpleOpenAIAgent.py`, SHA-256
`609ae74f2d24db045f268a1d3ae969523b87829d6cb4444608e286a64ff96ca2`). Facts
checked, not silently altered:

| Item | Vendor agent | Repository runner (shared) | Uniform across 3 strategies |
| --- | --- | --- | --- |
| Tool-result length | stringified, truncated to first **500** chars (`str(result.content)[:500]`) | full JSON payload via `json.dumps(result.model_dump(...))` — **no truncation** | Yes; not changed by this branch |
| Schema fidelity | `convert_to_openai_tool_strict` drops unsupported JSON-schema keys | `prepare_tools` keeps full `parameters` via `copy.deepcopy`; nothing dropped | Yes |
| `outputSchema` | not loaded at construction | loaded by `transport.snapshot` (`tool.outputSchema`) and appended to the model description | Yes |
| `usage_rules` | no loader | uniform loader: appended to description in `prepare_tools` | Yes |
| History isolation | `self.messages` persists on the instance | `agent_loop` builds a fresh `messages` list each run; one client/instance per run | Yes |
| External deps | imports `custom.utils.*`; needs server map / `_1mcp_` names | replaced by `transport.py` (stdio MCP) + `inventory.py`; single file cannot run the benchmark alone | Yes |

Differences between the vendor file and the repository runner (500-char
truncation, `custom.utils`, `_1mcp_` naming) are pre-existing Group-A
integration decisions. They apply identically to all strategies; this branch did
not give Selective extra rounds, longer context, special error recovery, or extra
reflection.

## B. Changes this branch makes to common code

All are thin dispatch/opt-in additions. Behavior for `no_update` and
`full_rewrite` is unchanged (same outputs, same cost, same validation).

| File | Change | Reason / behavior change | Applied to all 3 |
| --- | --- | --- | --- |
| `src/pe6203/baselines.py` | `adapt(...)` dispatches `strategy == "selective_patch"` to `selective.adapt`; otherwise unchanged | Required so the common `adapt(old, new, strategy, context)` entry serves the third strategy | No-op for the two baselines |
| `src/pe6203/baselines.py` | `write_adaptation(..., context=None)` gains an optional `context` and delegates `selective_patch` to `selective.write_adaptation` | Backward compatible; default arg keeps existing call sites working | No-op for the two baselines |
| `src/pe6203/cli.py` | `pe6203 adapt --strategy` choices add `selective_patch` | Needed to build the third strategy from the CLI | Choice only; baselines unaffected |
| `src/pe6203/cli.py` | optional `--allow-llm-update`, `--updater-config` | Gated inputs for the optional LLM rule updater; ignored unless strategy is `selective_patch` | Ignored for the two baselines |
| `tests/test_baselines.py` | replaced `test_selective_patch_is_not_silently_implemented_as_full_rewrite` with `test_selective_patch_is_distinct_and_keeps_untouched_records` | The old test asserted the strategy was absent; it now verifies real, selective behavior | Test-only |

## C. Selective-specific additions (not changes to common behavior)

- `src/pe6203/selective.py` — diff → impact → patch → validate → save.
- `tests/test_selective.py` — synthetic module tests (explicitly not benchmark scores).
- `configs/updater.template.json` — template for the optional LLM updater; no secrets.
- `vendor/SimpleOpenAIAgent.py` — read-only reference copy of the shared agent (checksum above).
- `contributions/haoqi/` — provenance, sample patch and preliminary report.

## D. Honest limitations

- No live model/MCP task run was executed in this branch; only the **adaptation
  artifact** generation was run against the committed task139 catalogs. Real
  task execution still needs `uv ... bootstrap` and configured agent/judge keys.
- The optional LLM updater is implemented but **never executed** (gated; keys
  and verified model id absent). All committed artifacts are deterministic
  (`formal_llm_rewrite=false`).
- The tracked file `.env copy` predates this branch; it was not read, modified,
  or used, and no new secrets were introduced.

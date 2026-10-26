# PE6203 · Vanilla Agent Experiment Handoff

**Owner:** Liang Luwen  
**Project:** Tool Harness Adaptation under Environment Change (MCPEvol-Bench)  
**Status:** One real-model, real-MCP **development-reference run completed and result.json independently checked**; broader benchmark comparison **not yet completed**  
**Run date:** 20 October 2026 (Singapore local date)  
**Working branch:** `feature/vanilla-agent-liangluwen`  
**Run:** `task139 / early / current_metadata_smoke / seed0`

## 1. Purpose and scope

Verify that the group's existing **Vanilla Tool-Calling Agent** works end-to-end with the current-stage tool catalogue, a real LLM, released MCP servers, and the project judge. This is an **agent execution reference**, **not** a fourth tool-knowledge adaptation strategy.

- **Vanilla reference (`current_metadata_smoke`):** loads a tool-knowledge snapshot matching the selected server stage.
- **No Update:** intentionally retains earlier tool knowledge after an environment change.
- **Full Rewrite / Selective Patch:** construct new knowledge using their respective update rules.

Results from this run must **not** be counted as the group's official No Update / Full Rewrite / Selective Patch comparison, nor as proof that Task 223 (latest papers → webpage) has been completed.

## 2. Setup and fixed run configuration

| Field | Recorded setting |
| --- | --- |
| Benchmark task | MCPEvol-Bench **139**, project management and knowledge graph |
| Tool environment | **Early** |
| Strategy identifier | `current_metadata_smoke` (Vanilla development reference) |
| Seed | `0` (model seed not transmitted by the run config) |
| Agent model | `deepseek/deepseek-v4.1-flash-1017` via OpenRouter |
| Judge model | Same model via OpenRouter |
| Temperature | `0` for Agent and Judge |
| Agent output-token limit | `2048` per completion |
| Judge output-token limit | `4096` per completion |
| Max Agent rounds | `12` |
| Judge evaluations | `5` |
| Tool name policy | `namespaced` |
| Knowledge input | `examples/catalogs/task139/early.json` |
| Local configuration (ignored) | `configs/local.smoke-no-reasoning.json` |
| Local OS | Windows 11; Python 3.12.12; Node.js 24.17.0 |
| Local output directory (ignored) | `results/raw/vanilla-task139-early-win-01` |
| MCP benchmark upstream commit | `888c779a0fe735f612ca62bdd1fdd7c9e6bf8701` |
| Dataset revision | `162e3ffbea1717ac8a20fe9b26465e29117229e4` |
| Knowledge snapshot version | `early` |
| Knowledge SHA-256 | `116f779c8a4f9819c29bc8d169b95bd30ee3be386cfde9e3cf8398d0d2e22791` |
| Run config SHA-256 | `59dcf6edc8f76ac85ae8945284b7141abc62e57b208bb24a8e037a797a0471d0` |
| Protocol SHA-256 | `c2f388a6ba081ab12f590a7b5e272ab5ad8a4c8bcd2353260111a9841c2b7c2c` |

The local `.env` holds endpoint URLs and API keys and must **never** be committed or shared. The Windows run required the process-local setting `PYTHONUTF8=1` to prevent a `UnicodeEncodeError` while writing UTF-8 tool outputs.

### Reproduction (PowerShell, from the repository root)

These commands require the reviewed Early MCP environment, the local config, and privately configured API credentials. **Running the second command consumes model API quota.** Use a **new output directory** for every run.

```powershell
$env:PYTHONUTF8 = "1"
uv run --env-file .env pe6203 run --task-id 139 --version early --strategy current_metadata_smoke --seed 0 --config configs/local.smoke-no-reasoning.json --knowledge examples/catalogs/task139/early.json --output results/raw/vanilla-task139-early-NEW-RUN
```

## 3. Verified observations (one run only)

| Measure | Observed |
| --- | --- |
| Overall result | `evaluated` |
| Execution status | `completed` |
| Judge status | `complete` |
| Task Fulfillment (TF) | **10 / 10** |
| Process Evaluation (PE) | **9.8 / 10** |
| Judge runs | **5**, also confirmed by five `judge_result` events in the visible event-count screenshot |
| Runtime | **56.437 seconds** |
| Recorded start | `2026-10-20T14:42:56.329568+00:00` (22:42:56 Singapore time) |
| Tool-result events | **12** |
| Agent-response events | **6** |
| Tool-result events flagged `isError: true` | **0**, based on a PowerShell query of the recorded event fields |
| Top-level recorded errors | `[]` (from the uploaded JSON; this does not prove every tool call was semantically correct) |
| ECS | **Not computed** (requires cross-stage results) |
| Update cost | `null` / unmeasured for this reference; not comparable to adaptation update-cost measurements |

### Tools actually exercised

| MCP tool | Recorded result events |
| --- | ---: |
| `create_project` | 1 |
| `create_task` | 5 |
| `update_task` | 4 |
| `create_entities` | 1 |
| `create_relations` | 1 |
| **Total** | **12** |

The `isError` query is a narrow mechanical check; absence of flagged errors does **not**, by itself, establish the semantic correctness of each tool action. TF/PE summarize the judge's evaluation for this one run.

### Usage (not billing)

From the **uploaded, machine-read `result.json`**, checked directly:

| Model role | Prompt tokens | Completion tokens | Total tokens |
| --- | ---: | ---: | ---: |
| Agent | 96,780 | 4,047 | **100,827** |
| Judge | 46,731 | 2,025 | **48,756** |
| **Combined** | **143,511** | **6,072** | **149,583** |

**Actual USD cost was not reported** (`cost.usd: null`); update cost fields are also `null`. Token counts are usage evidence, **not** a verified invoice or strategy update cost. Do not extrapolate cost from the model's theoretical maximum token settings.

## 4. Evidence produced locally

`results/raw/vanilla-task139-early-win-01/` contains:

| Item | Evidence purpose |
| --- | --- |
| `result.json` | Status, aggregated scores, configuration fingerprint, timings and token usage |
| `events.jsonl` | Step-level Agent responses, tool results and judge events |
| `raw_trace.json` | Agent/tool execution trajectory |
| `environment-metadata.json` | Discovered MCP tool metadata |
| `knowledge.json` | Exact tool-knowledge snapshot used |
| `ANSWER/139.json` | Captured Agent answer |
| `EVAL/139.json` | Judge evaluation evidence |
| `judge-prompt-1.txt` … `judge-prompt-5.txt` | Reproducibility records of judge requests |
| `mcp.stderr.log` | MCP server diagnostic output |
| `workspace/` | Task artifacts / persistent tool state |

**Data-handling:** These raw files remain on the local E: drive. Before sharing, scan them for credential values, user-specific paths, task contents, and other sensitive information; do not blindly commit `results/raw/`, `workspace/`, `.env`, or `.env copy`. A concise, checked report may be committed to the feature branch as a separate commit, after review.

## 5. Validation and limitations

- **Feature-branch GitHub CI:** Ruff lint and format checks passed; whole-repository offline suite reported **59 passed, 5 skipped, 10 deselected** on the CI environment. These are **repository-wide counts**, not 59 Vanilla-specific tests.
- **Local Windows Vanilla suite:** `uv run pytest -q tests/test_vanilla_agent.py` → **6 passed**.
- **Local Windows repository-wide suite:** **56 passed, 3 failed, 5 skipped, 10 deselected**. Failures were in generic path / symlink tests (`WinError 1314` and a Windows path-format assertion), and are still **unresolved**. They did not cause the six Vanilla tests to fail.
- **Real MCP probe:** Early MCP services were launched; metadata, calls and probe records were written; `persistent_state_verified: true`. The initial Windows attempt failed due to a GBK encoding error; subsequent run succeeded with `PYTHONUTF8=1`.
- **Real LLM and judge:** OpenRouter authentication and one full Task 139 Early run succeeded.
- **Important limitation:** One Early-stage reference run, not repeated seeds, not Middle/Late and not Task 223; therefore no recovery/retention, ECS or strategy ranking can yet be claimed.
- **Baseline comparability:** The group's earlier No Update Task 139 results are separate runs. Do not interpret a numerical difference as an adaptation effect without matching all test conditions, task selection, version, seed and evaluation protocol.
- **Paper reproduction qualification:** The current project shares the paper's basic tool-calling loop, not a demonstrated bit-for-bit reproduction. The group fixes temperature 0, maximum 12 rounds and a workspace-aware prompt; disclose differences from the published setup.

## 6. Handoff to Baseline / Selective Patch teams

1. **Reuse the group's existing runner.** Vanilla is an agent execution reference, not an alternative standalone runner or fourth adaptation method.
2. Keep task, environment stage, model, prompt, maximum rounds, tool-name policy and judge settings comparable. Vary **only** the tool-knowledge update strategy in the official 3-strategy study.
3. Ensure a Vanilla reference uses stage-matched tool metadata. The stage-consistency guard applies only to `current_metadata_smoke`; No Update is permitted to retain historical metadata.
4. For future experiments, archive the exact catalogue/config references and hashes, save complete raw traces privately, and use a fresh output directory per task × stage × strategy × seed.
5. Next experimental priorities: (a) review and install Task 223's fetcher/pages MCP services, (b) agree a fixed benchmark subset and repeat policy, (c) run matching comparison strategies under a frozen protocol, (d) report unchanged-task retention, changed-task recovery, ECS and update cost.

## 7. Evidence provenance and verification status

**Directly verified from the uploaded `result.json`:** task/stage/strategy/seed; `evaluated` / `completed` / `complete` statuses; TF=10; PE=9.8; ECS=`null`; `ecs_inputs.early=10`; top-level `errors=[]`; exact Agent and Judge model IDs/endpoints; protocol settings; five configured judge runs; 56.437 s; per-role token usage; unavailable USD/update costs; exact benchmark/dataset/config/knowledge/protocol identifiers and hashes.

**Based on user-shared PowerShell and GitHub CI screenshots (not independently parsed from raw log files):** 12 `tool_result`, six `agent_response`, five `judge_result` events; breakdown by tools (1 project creation, five task creations, four task updates, one entity creation, one relationship creation); zero `isError: true` flags in the user's PowerShell query; the presence and file sizes of `ANSWER/139.json`, `EVAL/139.json`, `events.jsonl`, and other artifacts; local / CI test counts and MCP Probe success.

**Not independently verified in this handoff:** detailed content of `events.jsonl`, `raw_trace.json`, `ANSWER/139.json`, `EVAL/139.json`, the individual judges' rationale and score spread, exact model billing, and content validity of all generated project/graph objects. These remain local and should be reviewed before any official publication or merging.

**Sharing/security review:** The uploaded `result.json` includes API environment-variable names and endpoint URLs but **does not contain an API key value**. It also includes a machine-specific absolute project path. Prefer this report and the sanitized evidence summary over committing raw run logs; keep `.env`, local `workspace/`, and unreviewed traces out of the repository.

**Source of truth:** `result.json` from `results/raw/vanilla-task139-early-win-01/` (20 October 2026). The original result is preserved locally; this report does not change the data or retroactively modify the execution.

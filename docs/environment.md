# Environment and primary-source audit

## Revisions and entry points

Upstream commit: **888c779a0fe735f612ca62bdd1fdd7c9e6bf8701**. Server dataset revision: **162e3ffbea1717ac8a20fe9b26465e29117229e4**. Complete archive digests are in `configs/benchmark.lock.json` and checked before extraction.

| Concern | Primary source and executable entry |
| --- | --- |
| Installation | [Upstream README](https://github.com/Octobrist/MCPEvol-Bench/blob/888c779a0fe735f612ca62bdd1fdd7c9e6bf8701/README.md) |
| Agent launcher | [tool_level_test.py](https://github.com/Octobrist/MCPEvol-Bench/blob/888c779a0fe735f612ca62bdd1fdd7c9e6bf8701/src/custom/real_mcp/tool_level_test.py), `--step 3` original, `--step 4` evolved |
| Official task selection | [test_utils.py](https://github.com/Octobrist/MCPEvol-Bench/blob/888c779a0fe735f612ca62bdd1fdd7c9e6bf8701/src/custom/utils/test_utils.py), `clean_all_test_cases`, reads `chosen_idx.json` |
| Judge rubric | [eval_error_prompt.py](https://github.com/Octobrist/MCPEvol-Bench/blob/888c779a0fe735f612ca62bdd1fdd7c9e6bf8701/src/custom/prompt/eval_error_prompt.py), `build_mcp_bench_judge_prompt` |
| Judge execution | [evaluation.py](https://github.com/Octobrist/MCPEvol-Bench/blob/888c779a0fe735f612ca62bdd1fdd7c9e6bf8701/src/custom/analysis/answer/evaluation.py), `evaluate_one_five_times`, `aggregate_eval_runs` |
| ECS | [evolutionary_volatility.py](https://github.com/Octobrist/MCPEvol-Bench/blob/888c779a0fe735f612ca62bdd1fdd7c9e6bf8701/src/custom/analysis/answer/evolutionary_volatility.py), `extract_task_fulfillment_score`, `compare_three_dirs`, `_compute_row`, `main` |
| MCP sessions | [Official Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk/tree/v1.25.0), `stdio_client`, `ClientSession` |
| Model tool calls | [Official Chat Completions reference](https://developers.openai.com/api/reference/python/resources/chat/subresources/completions/methods/create) |

The raw task file contains 393 candidate records with reference answers and trajectories. The official runner filters through `chosen_idx.json`, selecting 201 IDs. The adapter applies that selection and exposes only `idx`, `question`, and server/tool mapping. Published answers, reference traces, and historical scores do not enter agent or judge inputs.

## Stage representation

| Version | Released configuration under `servers/1mcp_config/` | Archive | Evolution |
| --- | --- | --- | --- |
| `early` | `original/mcp.json` | `original_servers.zip` | Original |
| `middle` | `iter3/mcp.json` | `iter3_servers.zip` | Three iterations |
| `late` | `iter5/mcp.json` | `iter5_servers.zip` | Five iterations |

This follows the README and paper Table 3. `--version` changes the executable package tree and starts fresh processes. Nested `HYBRID` annotation-directory depth is not treated as a substitute for physical snapshots.

Official task 139 uses `@pimzino/agentic-tools-mcp` 1.8.1 and `@itseasy21/mcp-knowledge-graph` 1.0.7. Evolved bundles retain these version strings: **identify snapshots by stage and archive digest, not package version alone**. Bootstrap resolves 97 bundled dependency paths and roughly 4,700 files per stage, including nested dependencies.

Task 139 is an infrastructure smoke case, not a representative final subset. Server annotations include PARAM, TOOL, and DESC changes across the sequence, but that does not prove the task's actually used tools cover all categories. D/C must validate task-level coverage before freezing experiments.

## Installed environment

Tested: Python **3.12.12**, Node **24.13.0**, uv **0.11.21**, npm **11.17.0**, macOS arm64. `uv.lock` pins Python dependencies; core upstream versions retained are MCP **1.25.0** and OpenAI SDK **2.16.0**. Upstream lists npm 11.6.2; our npm only installs the pinned Node binary, not the released server dependency graph.

Docker client **29.2.0** was installed but the daemon unavailable. This delivery validates native stdio, not a container image. Each run has a fresh directory; `workingDirectory` is restricted to it and graph storage is redirected there. This is application-level containment, not an OS sandbox. Only the two reviewed local servers are enabled. New shell/filesystem/browser/network/database servers need a separate review.

The full upstream requirements include CUDA/NVIDIA dependencies and a wider research environment. That unchanged list is not our Apple Silicon installation path. The adapter installs only its runtime dependencies and retains released Node dependency closures without upgrades.

## Release issues and decisions

1. The agent launcher embeds API placeholders; the generic LLM helper embeds a third-party endpoint. The adapter requires explicit endpoint/key environment variables and never sends keys to that hard-coded endpoint.
2. `evaluation.py` imports missing `custom.analysis.mutation.utils` and connects to fixed `localhost:3050` at import time. The bridge loads the official rubric and unmodified pure formatting functions via AST, avoiding these import-time dependencies. Judge inputs preserve the upstream 1,000-character tool truncation and assistant-text removal. Full original traces remain in logs. Upstream files are not edited.
3. Original configs use unversioned `npx`; the adapter executes archived code directly to avoid substituting newer package versions.
4. Upstream uses 1mcp HTTP, a time/database prompt, repeated final-response nudges, and truncated observations. The adapter uses stdio, a workspace prompt, full observations, and stops on a final answer without tool calls. These are **harness differences**. Keep them fixed across team strategies; do not claim exact reproduction of the paper's leaderboard.
5. The paper names DeepSeek-Chat as judge; released code defaults to `gpt-4o`. Choose and freeze one protocol. The adapter defaults to five calls with seeded rubric order. Unlike upstream, invalid judge responses are logged as incomplete rather than retried until five valid results. Partial TF/PE means must be excluded from formal comparisons or explicitly reported with counts.

## Metrics

TF uses `task_fulfillment_mean`; PE uses `planning_and_efficiency_mean`. Grounding is also preserved. Missing scores remain `null`. `status=evaluated` means grading finished, not perfect task completion.

The [paper's §6.1 and Appendix D.1](https://arxiv.org/html/2607.14642v1) define ECS as the across-task average of mean TF minus standard deviation over three versions. Appendix D.1 uses sample deviation (`N−1`), but released `_compute_row` uses population variance (`N`). For TF `[6,8,10]`, code gives **6.3670068381** and appendix gives **6.0**. The adapter labels both: `upstream_population` and `paper_sample`. D should confirm the course convention before publishing comparisons.

Single-version results have `ECS=null` and `ecs_inputs`. Pair task, strategy, model/config, and repetition across three stages before computing ECS. Upstream aligns filenames and prefers unrounded TF means. Keep filenames stable (`139.json`) and disclose missing triplets rather than silently shrinking the set.

The primary academic source is [Liu et al., arXiv:2607.14642v1 (2026)](https://arxiv.org/abs/2607.14642v1), a preprint rather than a verified journal publication. Executable behavior is grounded in the pinned released source when it differs from the paper.

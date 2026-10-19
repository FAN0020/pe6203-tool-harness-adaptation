# Vanilla Agent reproduction — Liang Luwen (development reference)

## Scope and meaning

My assignment is to verify the paper-style **Vanilla Tool-Calling Agent** against the group's shared runner, rather than build a competing runner. In MCPEvol-Bench, the agent repeatedly receives a task and available tool schemas, chooses tool calls, observes their results, and stops with a final answer or a step limit (paper, Algorithm 1, Appendix H.3). This is an **agent architecture**, not a fourth tool-knowledge update method.

**Crucial distinction:** For the paper-style Vanilla reference at a given server stage, the agent receives the **current stage's** MCP tool knowledge. In **No Update**, the agent deliberately keeps **Early-stage** knowledge when running against Middle/Late tools. Full Rewrite and Selective Patch are alternative methods to construct adapted knowledge. A Vanilla reference result must not be presented as evidence of adaptation or as the group's formal fourth strategy.

## Reuse rather than duplicate

The existing `src/pe6203/runner.py` already performs the relevant loop. No parallel runtime is added, to keep execution conditions the same for B/C/D:

| Paper's Agent stage | Existing repo | Acceptance evidence |
| --- | --- | --- |
| Task + initial agent context | `runner.agent_loop`: initial `system` + `user` messages | `initial_messages` trace |
| Tool discovery / representation | `runner.prepare_tools`: versioned catalogue → model-facing tool definitions and fixed routes | `knowledge.json`, `model_tool_routes` |
| LLM decides tool invocations | `agent_loop`: fixed API `tools` + messages | `agent_response` events |
| Execute via MCP, obtain observations | `agent_loop` → `transport.sessions` → `client.call_tool` | `tool_result` events, `trajectory_messages` |
| Continue until final answer / max rounds | `agent_loop` stop and `max_rounds` | `result.json` execution status |
| Judge final task and trace | `runner.run_async` → official prompt + multi-judge aggregation | `EVAL/`, `result.json` |

Existing teammate contributions remain intact. Tests in `tests/test_vanilla_agent.py` extend evidence for two sequential tool invocations, error observation and recovery, task isolation, and prevention of incorrect stage labels. The only production guard added is for `current_metadata_smoke`: its knowledge envelope **and all tool records** must match the selected stage, preventing an Early snapshot from being mislabeled as a Late Vanilla run. This does not restrict No Update or Selective Patch, whose metadata may legitimately remain old.

## Fixed conditions and deviations

This reference shares the group's model, prompt, maximum rounds, tool-name policy, MCP execution, and judge configuration. It does **not** add memory, reflection, planning modules, or extra recovery prompts. It uses the group's official-task fixtures rather than a new synthetic benchmark.

The paper's described algorithm and prompts are a design basis, **not proof of bit-for-bit reproduction of the published authors' code**. Important project-level differences include the group's fixed `temperature=0` and `max_rounds=12` (as of 19 Oct 2026) rather than the paper's Appendix D.3 evaluation temperature of `0.2`; the group's execution prompt adds workspace safeguards. The group must preserve these differences in the final report and use identical conditions for all adaptation strategies.

## How to execute this reference (real model and MCP)

Run from repo root, after the group's documented `uv sync` and reviewed-server `bootstrap` steps. Prepare a **local, ignored** `configs/local.smoke-no-reasoning.json` using the current README's model settings and a local `.env` containing the required environment variables. Never commit keys.

```bash
uv run --env-file .env pe6203 run \
  --task-id 139 --version early --strategy current_metadata_smoke --seed 0 \
  --config configs/local.smoke-no-reasoning.json \
  --knowledge examples/catalogs/task139/early.json \
  --output results/raw/vanilla-task139-early-unique-run
```

For Middle/Late, change both `--version` and the matching catalogue path to `middle`/`late`; **do not** retain Early metadata for this reference. Use a fresh output directory for every run. Unlike No Update and Full Rewrite, this development reference loads matching metadata directly, without an adaptation artifact. Its update cost should not be compared to the strategy update costs.

The currently selected main demonstration **task 223** (latest papers → webpage) cannot yet run in the group environment because the required fetcher/pages server profiles have not been reviewed and installed. Do not claim completion of task 223 based on a fake or task 139 smoke test. The project's existing task 139 live-model evidence predates this change and uses **No Update**, not the Vanilla development reference.

## Checks and handoff

- Offline: `uv run pytest -q tests/test_vanilla_agent.py tests/test_runner.py` (after installing dependencies); fake LLM and fake MCP boundaries only.
- Integration: invoke the above real smoke command for one official selected task with a stage-matched catalogue; inspect `events.jsonl`, `ANSWER`, `EVAL`, `result.json` for actual tool calls, correct final response, five valid judge scores, or explicit failures.
- Handoff: reuse `run(task_id, version, strategy, seed, config)` with unchanged agent execution, swapping only the tool-knowledge adaptation method in the official 3-strategy comparison. Archive run configurations and hashes.

No benchmark score is claimed from the offline tests in this branch. If the specified Python/Node runtime and released MCP servers are unavailable, report validation as **not run**, never as passing.

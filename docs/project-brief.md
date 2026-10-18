# Project 4 requirements

The current assignment is **Tool Harness Adaptation under Environment Change**, based on the supplied PE6203 Project 4 brief and the team's [shared sprint plan](https://docs.google.com/document/d/1fbhITsq__0Xaxjp85qVaQxIO1kQS6oDF-RFe7G7G5kQ/edit). The course brief governs requirements; the schedule and interfaces are working agreements. Project 2 remains in Git history and no longer defines the scope.

Investigate whether updating affected tool knowledge recovers performance after persistent environment changes while preserving unaffected capabilities. Compare **No Update**, **Full Rewrite**, and a developed **Selective Patch** method. Keep model, inference settings, task subset, and judge fixed. Do not fine-tune the model or modify benchmark labels.

Use MCPEvol-Bench's Early/Middle/Late stages. A fixed documented subset is acceptable, but must represent Tool/Parameter/Description changes and be identical across strategies. Three runs per strategy are preferred; one is acceptable with disclosure.

Deliver code, configurations, commands, raw logs, a report, and a 10-minute presentation with 5 minutes of Q&A. Report TF, PE, ECS, changed-task recovery, unaffected-task retention, update tokens/time/API cost, and at least one real under-update and one real over-update trajectory.

## Group A responsibility

1. Confirm repositories, exact revisions, dependencies, and model/tool services.
2. Install and document environment, startup commands, credentials, and Python/container versions.
3. Identify stage switching and judge/metric entry points.
4. Run a real agent → MCP → judge → logs smoke test.
5. Publish runner adapter, metadata, execution traces, and result format for B/C/D.

This delivery supplies the environment and adapter foundation. Model-backed acceptance remains pending service configuration; it does not claim completion of the full experiment or other teams' methods.

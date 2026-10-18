# Project brief

This document summarizes the selected course assignment, **PE6203 Group Project 2: Safety Approval Policies for Agent Harnesses**. The original supplied Word brief remains the authority for course requirements. The implementation roadmap in the README is a proposed work sequence.

## Problem and decisions

AI agents act through tools that can read data, modify files, invoke APIs, or execute commands. The project investigates an approval policy that balances safe task completion with the attention required from a human reviewer.

The gate must intercept each proposed tool call before execution and select one of three decisions:

- **Auto-approve:** permit the call without human intervention.
- **Auto-deny:** block an unsafe or out-of-scope call automatically.
- **Escalate:** ask a reviewer to approve or deny an ambiguous or high-risk call.

Each task has a maximum of `k` escalations. When that budget is exhausted, any subsequent decision that would require escalation is treated as an auto-denial. A denied call must not execute.

The policy may use information available at decision time, including the tool name and arguments, preceding agent trace, conversation history, task description, and metadata about the call's effects or target resources.

## Evaluation requirements

Integrate the gate into the **AgentDojo** evaluation pipeline. Compare at least one developed policy against both required baselines:

- **Full approve:** auto-approve every call.
- **Full escalate:** escalate every call, subject to the same per-task budget and exhaustion rule.

Use an LLM-simulated human reviewer for online evaluation. Document its design and prompting strategy. Its inputs may include tool-call details and task context but must exclude benchmark ground-truth labels, attack annotations, and other oracle information.

### Main metrics

**TCR@k** is the number of tasks completed successfully without any unauthorized tool execution, divided by the total number of evaluated tasks, with at most `k` escalations per task. Report a curve over a meaningful range of budgets.

**HITL Load** is the total number of escalations across successfully completed tasks. Report the load alongside TCR@k so that a low escalation count can be interpreted together with the number of tasks completed. Any additional escalation metric, such as escalations across all attempted tasks, must be labeled separately.

Report additional API usage or cost by strategy and by component: policy inference, reviewer simulation, and agent execution. Token counts or dollar costs satisfy the brief; if reporting dollars, record the pricing assumptions used.

### Failure analysis

Classify failures into at least these two categories:

| Category | Required interpretation |
| --- | --- |
| Over-conservative | A safe call was auto-denied, or unnecessary escalation of safe calls exhausted the budget and prevented successful completion. |
| Over-permissive | An unsafe call was auto-approved and resulted in an unauthorized action. |

For each category, provide at least one concrete trajectory showing the tool calls, policy decisions, and point of failure. Discuss which call types gain the most from human escalation and which can be safely auto-approved in their task context.

## Submission checklist

### Codebase

- [ ] Approval gate integrated into AgentDojo before tool execution.
- [ ] At least one developed approval policy.
- [ ] Full-approve baseline.
- [ ] Full-escalate baseline.

### Report

- [ ] TCR@k curves for the developed policy and both baselines.
- [ ] HITL Load table.
- [ ] Per-strategy API usage or cost breakdown by component.
- [ ] Failure classification.
- [ ] Representative trajectories for both required failure categories.
- [ ] Escalation-value analysis.
- [ ] Documentation of the simulated reviewer's design and prompts.

### Presentation

Prepare a **10-minute presentation plus 5 minutes of Q&A** covering the policy idea, implementation and AgentDojo integration, experimental comparisons, representative failures, escalation insights, and conclusions.

## Proposed reproducibility records

For each experiment, record the benchmark revision, selected tasks and attacks, agent and reviewer configurations, policy configuration, budget, available random seeds, and run identifier. Keep benchmark ground truth confined to evaluation rather than supplying it to the simulated reviewer.

Log each tool-call decision with the budget before and after the decision, whether execution occurred, and the reviewer result when applicable. Preserve enough context to explain failures, with sensitive values removed before committing artifacts.

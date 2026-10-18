# Safety Approval Policies for Agent Harnesses

PE6203 Group Project 2: design an approval policy that helps an AI agent complete tasks safely while using a limited amount of human attention.

For each proposed tool call, the policy chooses **auto-approve**, **auto-deny**, or **escalate to a human reviewer**. Each task has an escalation budget `k`; once the budget is exhausted, further decisions that require escalation become auto-denials.

**Status:** repository initialized with the project scope and deliverables. The approval gate, policies, benchmark integration, and experiments have not been implemented yet.

## Research objective

Maximize **TCR@k**, the fraction of tasks completed successfully without executing any unauthorized tool call, across different human-review budgets. Evaluate the trade-off between safe completion, human intervention, and API cost.

The project will integrate an approval gate into **AgentDojo** before tool execution and compare a developed policy with two required baselines:

| Strategy | Decision before tool execution |
| --- | --- |
| Full approve | Auto-approve every tool call without human intervention. |
| Full escalate | Send every tool call to the reviewer while budget remains; auto-deny when it is exhausted. |
| Developed policy | Selectively approve, deny, or escalate using information available at decision time. |

Online evaluation will use an LLM to simulate the human reviewer. The reviewer must only receive information reasonably available to a real reviewer; benchmark labels and attack annotations must not be included in its inputs.

## Repository contents

- [Project brief](docs/project-brief.md): requirements, evaluation criteria, and deliverables summarized from the selected course brief.
- `.gitignore`: keeps local course documents, credentials, environments, and generated outputs out of version control.

## Implementation roadmap

- [ ] Select and record an AgentDojo revision, agent model, and evaluation configuration.
- [ ] Define the policy interface and a per-task escalation-budget tracker.
- [ ] Add an approval gate that intercepts tool calls before execution.
- [ ] Implement the full-approve and full-escalate baselines.
- [ ] Implement and document the developed approval policy.
- [ ] Implement an LLM reviewer with documented inputs and prompts.
- [ ] Record decisions, reviewer outcomes, task results, and component-level token usage or cost.
- [ ] Run comparable experiments across a meaningful range of `k` values.
- [ ] Produce the required analysis, report, and presentation.

## Required results

1. TCR@k curves comparing all three strategies.
2. HITL Load: total escalations across successfully completed tasks, reported for each policy and budget.
3. API usage or cost broken down into policy inference, reviewer simulation, and agent execution.
4. Failure classification with representative trajectories for over-conservative and over-permissive behavior.
5. Analysis of which tool calls benefit most from escalation.

The final presentation is 10 minutes, followed by 5 minutes of Q&A.

## Working with this repository

```bash
git clone https://github.com/FAN0020/pe6203-agent-harness-safety.git
cd pe6203-agent-harness-safety
```

Start with the [project brief](docs/project-brief.md). Installation and experiment commands will be added when the implementation is available.

The supplied Word briefs and other topic documents remain local reference material and are ignored by Git. Use synthetic or sanitized examples in committed traces, and keep API keys in local environment variables or ignored environment files.

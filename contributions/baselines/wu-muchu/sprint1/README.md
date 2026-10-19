# PE6203 Project 4 — Sprint 1: Baselines

Contributor: Muchu Wu

## Contents
- baselines.py: No Update and deterministic Full Rewrite.
- baseline_synthetic_validation.json: synthetic validation records.

## Usage
from baselines import build_knowledge, adapt

old_knowledge = build_knowledge(old_metadata)
new_knowledge, diff_log, update_cost = adapt(
    old_knowledge, new_metadata, strategy="full_rewrite"
)

Use strategy="no_update" for the unchanged-knowledge baseline.

## Prototype Format
Metadata is a dictionary containing a complete "tools" list.
Each tool requires a unique, nonempty name within the snapshot.
All supplied tool fields are preserved in the rebuilt knowledge.
The final format must be aligned with the team before integration.

## Costs
Costs cover adaptation only, excluding agent execution and judging.
Neither prototype calls a model; model usage and API cost are zero.
Elapsed time is measured locally.
Update operations count rebuilt tool knowledge blocks.

## Validation
Six synthetic scenarios were tested with both strategies.
Two output-isolation checks and one strategy-rejection check were run.
See the notebook for executable tests and the JSON file for results.

## Limitations
No real benchmark integration or official TF, PE, or ECS evaluation.
Runtime prevention of updated-metadata leakage remains to be checked.
The final rebuild mechanism must be aligned with the shared team design.

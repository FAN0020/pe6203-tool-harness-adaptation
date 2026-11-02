"""Conservative per-rule abstention before unchanged V6 snapshot validation.

Preserve rejected proposals in the audit, withdraw them and publish uncertainty.
Authoritative metadata, required review coverage and final admission stay intact.
"""

from copy import deepcopy

from .rules_v5 import render_rule
from .selective import _dangling_references

WITHHELD = (
    "Proposed usage guidance was withheld because it referred to an unavailable callable. "
    "No replacement behavior is established by that proposal; use the current "
    "authoritative tool definitions and treat the disputed guidance as unknown."
)


def withdraw_retired_proposals(patches, removed, sources):
    result, withdrawals = deepcopy(patches), []
    for patch in result:
        count = len(patch["retain_rule_indices"])
        retained = patch["usage_rules"][:count]
        rendered = patch["usage_rules"][count:]
        if len(rendered) != len(patch["rules"]):
            raise ValueError("Admitted structured and rendered rules do not align")
        keep_structured, keep_rendered = [], []
        rejected = []
        for index, (rule, text) in enumerate(zip(patch["rules"], rendered, strict=True)):
            if _dangling_references({"tools": [{"usage_rules": [text]}]}, removed):
                rejected.append({"tool_id": patch["tool_id"], "proposal_index": index,
                                 "proposed_rule": deepcopy(rule), "rendered_proposal": text,
                                 "resolution": "withdrawn_with_explicit_unknown_not_accepted_guidance"})
            else:
                keep_structured.append(rule)
                keep_rendered.append(text)
        if rejected:
            unknown = {"kind": "unknown", "text": WITHHELD,
                       "evidence_ids": list(patch["evidence_ids"])}
            keep_structured.append(unknown)
            keep_rendered.append(render_rule(unknown, sources))
            patch["rules"] = keep_structured
            patch["usage_rules"] = retained + keep_rendered
            patch["withdrawn_proposed_rules"] = rejected
            withdrawals.extend(rejected)
    return result, withdrawals

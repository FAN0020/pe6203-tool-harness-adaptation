"""Publishing uncertain rules must preserve the original final validator."""

from copy import deepcopy

from pe6203.publication_v6 import withdraw_retired_proposals
from pe6203.selective import _dangling_references


def fixture():
    sources = {"e-current": {"kind": "catalog", "side": "target", "field": "description",
                             "tool_id": "server::current", "value": "Current authoritative interface"}}
    removed = [{"tool_id": "server::retired", "old": {"name": "retired"}}]
    patch = {"tool_id": "server::current", "retain_rule_indices": [0],
             "rules": [{"kind": "guidance", "text": "Call retired before current.", "evidence_ids": ["e-current"]},
                       {"kind": "guidance", "text": "Use numeric inputs.", "evidence_ids": ["e-current"]}],
             "usage_rules": ["Preserve the input units.", "Call retired before current.", "Use numeric inputs."],
             "evidence_ids": ["e-current"], "withdrawn_rules": []}
    return patch, removed, sources


def test_retired_proposal_is_withdrawn_unknown_kept_and_audit_retains_evidence():
    patch, removed, sources = fixture()
    original = deepcopy(patch)
    rows, audit = withdraw_retired_proposals([patch], removed, sources)
    p = rows[0]
    assert patch == original
    assert p["usage_rules"][:2] == ["Preserve the input units.", "Use numeric inputs."]
    assert p["rules"][-1]["kind"] == "unknown"
    assert len(p["usage_rules"]) == 3
    assert not _dangling_references({"tools": [p]}, removed)
    assert audit[0]["proposed_rule"] == original["rules"][0]
    assert audit[0]["rendered_proposal"] == "Call retired before current."


def test_retained_unsafe_rule_is_not_silently_accepted_by_publication_cleanup():
    patch, removed, sources = fixture()
    patch["usage_rules"][0] = "Call retired first."
    rows, _ = withdraw_retired_proposals([patch], removed, sources)
    assert _dangling_references({"tools": rows}, removed)


def test_no_removed_tool_means_all_original_rules_preserved():
    patch, _, sources = fixture()
    rows, audit = withdraw_retired_proposals([patch], [], sources)
    assert rows == [patch] and audit == []

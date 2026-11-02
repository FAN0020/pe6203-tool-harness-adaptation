"""V6 revision transport: merge legitimate scope; never admit fabricated evidence."""

from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator
from test_hybrid_selective import catalogs as catalogs

from pe6203.output_v6 import schema
from pe6203.payload_v6 import detail_packet, prepare, screening_packet, selections


def candidate(identity, basis, *, category="potential", reason="Review affected rule", fields=None):
    return {"tool_id": identity, "category": category, "reason": reason,
            "basis": basis, "fields": fields or []}


def screen(state, rows):
    return {"covered_tool_ids": list(state["records"]), "candidates": rows}


def test_duplicate_candidates_preserve_basis_fields_uncertainty_and_input(catalogs):
    old, target = catalogs
    target["tools"][2]["description"] = "Stores unrelated numeric measurements in grams."
    state = prepare(old, target)
    changes = list(state["changes"])
    assert len(changes) == 2
    root = {"tool_id": "server::fetch_balance", "side": "target", "field": "parameters"}
    leaf = {**root, "pointer": "/properties/amount"}
    response = screen(state, [
        candidate("server::display", changes[:1], fields=[root], reason="Units need review"),
        candidate("server::display", changes[1:], fields=[leaf, root], category="uncertain", reason="Dependency is uncertain"),
        candidate("server::display", changes[:1], fields=[root], reason="Units need review"),
    ])
    original = deepcopy(response)
    chosen = {r["tool_id"]: r for r in selections(response, state)}["server::display"]
    assert chosen["basis"] == sorted(changes)
    assert chosen["category"] == "uncertain"
    assert chosen["fields"] == [{**root, "pointer": ""}, leaf]
    assert chosen["reason"] == "Units need review\nDependency is uncertain"
    assert response == original
    detail_packet(state, [chosen])  # Independent hydration/scope checks still apply.


@pytest.mark.parametrize("bad", [
    {"basis": ["invented-change"]},
    {"fields": [{"tool_id": "server::fetch_balance", "side": "target", "field": "shell", "pointer": ""}]},
    {"fields": [{"tool_id": "server::fetch_balance", "side": "target", "field": "parameters", "pointer": "/missing"}]},
    {"category": "ignore"},
])
def test_invalid_second_occurrence_is_not_dropped(catalogs, bad):
    state = prepare(*catalogs)
    row = candidate("server::display", list(state["changes"]))
    with pytest.raises(ValueError):
        selections(screen(state, [row, {**row, **bad}]), state)


def test_unknown_identity_and_duplicate_coverage_still_fail(catalogs):
    state = prepare(*catalogs)
    with pytest.raises(ValueError, match="Unknown candidate"):
        selections(screen(state, [candidate("server::invented", list(state["changes"]))]), state)
    response = screen(state, [])
    response["covered_tool_ids"].append(response["covered_tool_ids"][0])
    with pytest.raises(ValueError, match="coverage"):
        selections(response, state)


def test_required_candidate_and_basis_cannot_be_removed(catalogs):
    catalogs[0]["tools"][1]["usage_rules"] = ["Use fetch_balance before display."]
    state = prepare(*catalogs)
    assert state["mandatory"]
    selected = {r["tool_id"]: r for r in selections(screen(state, []), state)}
    for identity, basis in state["mandatory"].items():
        assert identity in selected
        assert set(basis) <= set(selected[identity]["basis"])


def test_overlong_merged_reason_fails_explicitly_without_truncating(catalogs):
    state = prepare(*catalogs)
    rows = [candidate("server::display", list(state["changes"]), reason=c * 650) for c in ("A", "B")]
    original = deepcopy(rows)
    with pytest.raises(ValueError, match="Merged candidate reasons exceed.*no truncation"):
        selections(screen(state, rows), state)
    assert rows == original


def local_response(packet):
    return {"patches": [{"tool_id": row["tool_id"], "retain_rule_indices": [],
                          "rules": [{"kind": "guidance", "text": "Review account units",
                                     "evidence_ids": list(packet["evidence_registry"])}],
                          "reason": "Unit description changed", "basis": row["basis"],
                          "evidence_ids": list(packet["evidence_registry"])}
                         for row in packet["selected"]], "need_evidence": []}


def test_local_decoder_uses_only_known_ids_without_loosening_object_contract(catalogs):
    state = prepare(*catalogs)
    rows = selections(screen(state, [candidate("server::display", list(state["changes"]))]), state)
    packet, _ = detail_packet(state, rows)
    contract = schema("local_patch", packet)
    Draft202012Validator.check_schema(contract)
    validator = Draft202012Validator(contract)
    response = local_response(packet)
    assert validator.is_valid(response)
    for path in ("row", "rule", "basis", "tool"):
        bad = deepcopy(response)
        patch = bad["patches"][0]
        if path == "row":
            patch["evidence_ids"].append("e-invented")
        elif path == "rule":
            patch["rules"][0]["evidence_ids"].append("e-invented")
        elif path == "basis":
            patch["basis"].append("invented-change")
        else:
            patch["tool_id"] = "server::invented"
        assert not validator.is_valid(bad), path
    bad = deepcopy(response)
    bad["patches"][0]["citation_scope"] = {}
    assert not validator.is_valid(bad)


def test_decoder_enums_update_when_specific_extra_evidence_is_added(catalogs):
    state = prepare(*catalogs)
    rows = selections(screen(state, [candidate("server::display", list(state["changes"]))]), state)
    packet, _ = detail_packet(state, rows)
    expanded, _ = detail_packet(state, rows, [
        {"tool_id": "server::fetch_balance", "side": "target", "field": "parameters", "pointer": "/properties/amount"}
    ])
    new_ids = set(expanded["evidence_registry"]) - set(packet["evidence_registry"])
    assert new_ids
    response = local_response(expanded)
    assert Draft202012Validator(schema("local_revision", expanded)).is_valid(response)
    assert not Draft202012Validator(schema("local_patch", packet)).is_valid(response)


def test_valid_id_enum_does_not_bypass_program_citation_scope(catalogs):
    from pe6203.rules_v5 import patches

    state = prepare(*catalogs)
    rows = selections(screen(state, [candidate("server::display", list(state["changes"]))]), state)
    packet, sources = detail_packet(state, rows)
    response = local_response(packet)
    ids = {r["tool_id"] for r in rows}
    assert patches({"patches": response["patches"]}, ids, state["changes"], sources, state["records"])
    own_only = [key for key, item in sources.items() if item["tool_id"] == "server::display"]
    assert own_only
    response["patches"][0]["evidence_ids"] = own_only
    response["patches"][0]["rules"][0]["evidence_ids"] = own_only
    assert Draft202012Validator(schema("local_patch", packet)).is_valid(response)
    with pytest.raises(ValueError, match="basis change"):
        patches({"patches": response["patches"]}, ids, state["changes"], sources, state["records"])


def test_global_decoder_does_not_repeat_entire_directory_as_enums(catalogs):
    state = prepare(*catalogs)
    contract = schema("global_screen", screening_packet(state))
    assert contract["properties"]["candidates"]["items"]["properties"]["tool_id"] == {"type": "string"}

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pe6203.selective import adapt_result
from pe6203.verified_coverage import compile_verified, make_inventory, prepare_checks


def fixture():
    cats = json.loads(Path("tests/fixtures/dependency-cut-catalogs.json").read_text())
    old, target = cats["early"], deepcopy(cats["middle"])
    tool = next(t for t in target["tools"] if t["name"] == "sequentialthinking")
    tool["description"] = (
        "Unique purpose.\n- Preserve whitespace.\n- Preserve whitespace.\n- Reject cedar.\n"
    )
    graph = {
        "relations": [
            {"tool_id": tool["tool_id"], "line": 2, "support": [{"kind": "description", "line": 1}]}
        ]
    }
    return old, target, tool["tool_id"], graph


def feedback(missing=None, uncertain=False):
    return {"checks": [{"id": "E001", "missing_claims": missing or [], "uncertain": uncertain}]}


def test_verified_deletion_preserves_all_other_knowledge_and_line_endings():
    old, target, tid, graph = fixture()
    before = deepcopy(target)
    result, report = compile_verified(old, target, graph, feedback())
    tool = next(t for t in result["tools"] if t["tool_id"] == tid)
    assert tool["description"] == "Unique purpose.\n- Preserve whitespace.\n- Reject cedar.\n"
    tool["description"] = next(t for t in target["tools"] if t["tool_id"] == tid)["description"]
    assert result == adapt_result(old, target)["knowledge"] and target == before
    assert report["selected"] == ["E001"]


@pytest.mark.parametrize(
    "fb", [feedback(["Cedar restriction is absent"]), feedback(uncertain=True)]
)
def test_semantic_veto_keeps_original_despite_proposed_coverage(fb):
    old, target, _, graph = fixture()
    graph["relations"][0]["line"] = 3
    result, report = compile_verified(old, target, graph, fb)
    assert result == adapt_result(old, target)["knowledge"] and report["selected"] == []


def test_mutual_coverage_cannot_delete_both_witnesses():
    old, target, tid, graph = fixture()
    graph["relations"].append(
        {"tool_id": tid, "line": 1, "support": [{"kind": "description", "line": 2}]}
    )
    fb = feedback()
    fb["checks"].append({"id": "E002", "missing_claims": [], "uncertain": False})
    result, report = compile_verified(old, target, graph, fb)
    assert result == adapt_result(old, target)["knowledge"] and report["selected"] == []


@pytest.mark.parametrize(
    "bad", ["unique_intro", "self_support", "missing_source", "unchanged_tool", "duplicate_target"]
)
def test_bad_scope_and_provenance_rejected(bad):
    old, target, _, graph = fixture()
    r = graph["relations"][0]
    if bad == "unique_intro":
        r["line"] = 0
    elif bad == "self_support":
        r["support"][0]["line"] = 2
    elif bad == "missing_source":
        r["support"] = [{"kind": "parameters", "path": ["missing"]}]
    elif bad == "unchanged_tool":
        r["tool_id"] = next(t["tool_id"] for t in target["tools"] if t["name"] == "list_projects")
    else:
        graph["relations"].append(deepcopy(r))
    with pytest.raises(ValueError):
        prepare_checks(make_inventory(old, target), graph)


@pytest.mark.parametrize(
    "fb", [{"checks": []}, {"checks": [{"id": "E001", "missing_claims": [], "uncertain": "false"}]}]
)
def test_missing_or_malformed_verification_cannot_authorize_deletion(fb):
    old, target, _, graph = fixture()
    with pytest.raises(ValueError):
        compile_verified(old, target, graph, fb)


def test_checker_receives_original_claims_and_sources_without_producer_opinion():
    old, target, _, graph = fixture()
    checks = prepare_checks(make_inventory(old, target), graph)
    assert set(checks[0]) == {"id", "claim", "evidence"}
    assert checks[0]["claim"] == "- Preserve whitespace."
    assert checks[0]["evidence"] == ["- Preserve whitespace."]


def test_schema_witness_survives_and_hierarchy_parent_cannot_be_removed():
    old, target, tid, graph = fixture()
    tool = next(t for t in target["tools"] if t["tool_id"] == tid)
    tool["parameters"]["properties"]["thought"]["description"] = "Preserve whitespace."
    graph["relations"][0]["support"] = [
        {"kind": "parameters", "path": ["properties", "thought", "description"]}
    ]
    result, report = compile_verified(old, target, graph, feedback())
    assert report["selected"] == ["E001"]
    assert (
        next(t for t in result["tools"] if t["tool_id"] == tid)["parameters"] == tool["parameters"]
    )
    tool["description"] = "Purpose.\n- A parent with options:\n  * Unique option.\n- Other fact."
    graph["relations"][0]["line"] = 1
    with pytest.raises(ValueError):
        prepare_checks(make_inventory(old, target), graph)

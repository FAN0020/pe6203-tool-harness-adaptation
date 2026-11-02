"""Compiler contracts, no model/native calls or benchmark answers."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pe6203.relational_probe_memory import (
    bind_arguments,
    compile_knowledge,
    exported_ids,
    observation_note,
    validate_sequence,
)
from pe6203.selective import adapt_result

ROOT = Path(__file__).resolve().parents[1]
INPUTS = json.loads(
    (ROOT / "results/evidence/active-contract-probing-20261101/updater-inputs.json").read_text()
)
DATA = next(j["data"] for j in INPUTS["jobs"] if j["id"] == "project-middle")
SERVER = DATA["server"]


def proposal():
    return {
        "steps": [
            {
                "id": "P1",
                "tool": "create_project",
                "arguments": {
                    "workingDirectory": "$WORKSPACE",
                    "name": "ProbeRecord",
                    "description": "Synthetic contract record",
                    "tags": ["probe"],
                },
                "question": "Does creation persist the supplied metadata?",
            },
            {
                "id": "P2",
                "tool": "get_project",
                "arguments": {"workingDirectory": "$WORKSPACE", "id": "$P1.project_id"},
                "question": "Can the created identifier retrieve that same record?",
            },
        ]
    }


def rows():
    a = deepcopy(INPUTS["fixture"])
    b = deepcopy(a)
    b["projects"].append(
        {
            "id": "new-project-uuid",
            "name": "ProbeRecord",
            "description": "Synthetic contract record",
            "createdAt": "2026-01-02T00:00:00.000Z",
        }
    )
    return [
        dict(
            id="P1",
            before_state=a,
            after_state=b,
            result={"content": [{"type": "text", "text": "created new-project-uuid"}]},
        ),
        dict(
            id="P2",
            before_state=b,
            after_state=b,
            result={"content": [{"type": "text", "text": "record new-project-uuid"}]},
        ),
    ]


def test_connected_sequence_and_binding():
    assert len(validate_sequence(DATA, proposal())) == 2
    assert bind_arguments({"id": "$P1.project_id"}, {"$P1.project_id": "actual"}) == {
        "id": "actual"
    }
    with pytest.raises(ValueError, match="Unbound"):
        bind_arguments({"id": "$P1.project_id"}, {})


@pytest.mark.parametrize(
    "mutation", ["forward", "unconnected", "wrong_root", "extra_key", "workspace", "overlong"]
)
def test_reject_invalid_sequence(mutation):
    p = proposal()
    if mutation == "forward":
        p["steps"][1]["arguments"]["id"] = "$P3.project_id"
    if mutation == "unconnected":
        p["steps"][1]["arguments"]["id"] = "guessed-id"
    if mutation == "wrong_root":
        p["steps"][0]["tool"] = "list_projects"
    if mutation == "extra_key":
        p["steps"][0]["arguments"]["invented"] = True
    if mutation == "workspace":
        p["steps"][0]["arguments"]["workingDirectory"] = "/tmp/shared"
    if mutation == "overlong":
        p["steps"] = p["steps"] * 3
    with pytest.raises(ValueError):
        validate_sequence(DATA, p)


def test_exports_require_unambiguous_persisted_record_and_receipt():
    r = rows()[0]
    assert exported_ids("P1", r) == {"$P1.project_id": "new-project-uuid"}
    r["result"]["content"][0]["text"] = "no receipt"
    assert exported_ids("P1", r) == {}
    r = rows()[0]
    r["after_state"]["projects"].append({"id": "second"})
    assert exported_ids("P1", r) == {}


def test_note_keeps_sequence_and_effects_without_incidental_identifiers():
    note = observation_note(DATA, proposal(), rows())
    assert "new-project-uuid" not in note and "$P1.project_id" in note
    assert "createdAt" not in note and "Synthetic contract record" in note
    assert "tags" in note and "observations" in note
    r = rows()
    r[1]["before_state"] = {}
    with pytest.raises(ValueError, match="continuity"):
        observation_note(DATA, proposal(), r)


def certificate():
    return [
        {
            "stage": "middle",
            "server": SERVER,
            "result": {
                "kind": "relational_native_memory_v1",
                "semantic_review": "accepted",
                "inventory": DATA,
                "proposal": proposal(),
                "observations": rows(),
            },
        }
    ]


def test_only_changed_root_usage_rules_can_change():
    base = adapt_result(DATA["old"], DATA["target"])
    before = deepcopy(base)
    knowledge, edits = compile_knowledge(base, DATA["target"], certificate())
    assert base == before and len(edits) == 1
    root = SERVER + "::create_project"
    for old, new in zip(base["knowledge"]["tools"], knowledge["tools"], strict=True):
        if old["tool_id"] == root:
            assert len(new["usage_rules"]) == len(old["usage_rules"]) + 1
            patched = deepcopy(new)
            patched["usage_rules"] = old["usage_rules"]
            assert patched == old
        else:
            assert new == old
    bad = certificate()
    bad[0]["result"]["semantic_review"] = "rejected"
    with pytest.raises(ValueError):
        compile_knowledge(base, DATA["target"], bad)
    with pytest.raises(ValueError):
        compile_knowledge(base, DATA["target"], [])


def test_other_hosts_identical_to_sp():
    data = next(j["data"] for j in INPUTS["jobs"] if j["id"] == "math-middle")
    base = adapt_result(data["old"], data["target"])
    assert compile_knowledge(base, data["target"], []) == (base["knowledge"], [])


def test_incidental_native_locale_timestamps_removed_but_due_date_retained():
    evidence = rows()
    evidence[0]["result"]["content"][0]["text"] += "\nCreated: 11/2/2026, 2:41:25 AM"
    plan = proposal()
    plan["steps"][0]["arguments"]["description"] = "Target date 2026-02-02"
    note = observation_note(DATA, plan, evidence)
    assert "11/2/2026, 2:41:25 AM" not in note
    assert "2026-02-02" in note

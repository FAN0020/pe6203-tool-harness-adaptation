"""Synthetic V6-r2 decoder boundaries; no real model or benchmark scores."""

from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator

from pe6203.output_v6 import schema


def packet():
    return {
        "selected": [{"tool_id": "server::empty", "rules": [], "basis": ["c1"]},
                     {"tool_id": "server::existing", "rules": ["Keep units", "Keep route"], "basis": ["c2"]}],
        "changes": [{"change_id": "c1", "tool_id": "server::empty"},
                    {"change_id": "c2", "tool_id": "server::existing"}],
        "evidence_registry": {"e-empty": {}, "e-existing": {}},
    }


def response(identity="server::empty", retain=None):
    return {"patches": [{"tool_id": identity, "retain_rule_indices": retain or [],
                          "rules": [], "reason": "Preserve verified rule scope",
                          "basis": ["c1"], "evidence_ids": ["e-empty"]}],
            "need_evidence": []}


def test_empty_record_has_no_retainable_position_from_other_record():
    validator = Draft202012Validator(schema("local_patch", packet()))
    assert validator.is_valid(response())
    assert not validator.is_valid(response(retain=[0]))
    assert validator.is_valid(response("server::existing", [0]))
    assert validator.is_valid(response("server::existing", [0, 1]))
    assert not validator.is_valid(response("server::existing", [2]))
    assert not validator.is_valid(response("server::existing", [-1]))
    assert not validator.is_valid(response("server::existing", [True]))


def test_all_empty_records_force_empty_arrays_without_empty_enum():
    p = packet()
    for record in p["selected"]:
        record["rules"] = []
    contract = schema("local_revision", p)
    Draft202012Validator.check_schema(contract)
    validator = Draft202012Validator(contract)
    assert validator.is_valid(response("server::existing"))
    assert not validator.is_valid(response("server::existing", [0]))
    for branch in contract["properties"]["patches"]["items"]["anyOf"]:
        retained = branch["properties"]["retain_rule_indices"]
        assert retained["maxItems"] == 0
        assert "enum" not in retained["items"]


@pytest.mark.parametrize("field,value", [
    ("tool_id", "server::unknown"), ("basis", ["unknown-change"]),
    ("evidence_ids", ["e-invented"]),
])
def test_existing_identity_and_evidence_bounds_remain_strict(field, value):
    validator = Draft202012Validator(schema("local_patch", packet()))
    bad = response()
    bad["patches"][0][field] = value
    assert not validator.is_valid(bad)


def test_per_record_schema_does_not_mutate_packet():
    p = packet()
    old = deepcopy(p)
    contract = schema("local_patch", p)
    Draft202012Validator.check_schema(contract)
    assert p == old
    assert contract["additionalProperties"] is False
    assert all(branch["additionalProperties"] is False
               for branch in contract["properties"]["patches"]["items"]["anyOf"])


def test_candidate_local_field_read_accepts_root_not_prompt_or_invented_pointer():
    validator = Draft202012Validator(schema("local_revision", packet()))
    read = {"patches": [], "need_evidence": [{"tool_id": "server::empty",
             "side": "old", "field": "usage_rules", "pointer": ""}]}
    assert validator.is_valid(read)
    for pointer in ("/selected/rules", "/0", "/properties/query"):
        bad = deepcopy(read)
        bad["need_evidence"][0]["pointer"] = pointer
        assert not validator.is_valid(bad)
    bad = deepcopy(read)
    bad["need_evidence"][0]["tool_id"] = "server::unrelated"
    assert not validator.is_valid(bad)
    bad = deepcopy(read)
    bad["need_evidence"][0]["field"] = "shell"
    assert not validator.is_valid(bad)


def test_global_screen_retains_precise_optional_selector_support():
    contract = schema("global_screen", {"catalog": []})
    pointer = contract["properties"]["candidates"]["items"]["properties"]["fields"]["items"]["properties"]["pointer"]
    assert pointer == {"type": "string"}

import importlib.util
from copy import deepcopy
from pathlib import Path

import pytest


def decoder():
    p = Path("results/evidence/active-contract-probing-20261101/recovery/decode_references.py")
    spec = importlib.util.spec_from_file_location("probe_references", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.decode_references


def test_only_reference_changes_and_exact_root_is_protected():
    payload = {
        "probes": [
            {
                "id": "P1",
                "basis": "exact changed tool_id",
                "tool_id": "s::new",
                "arguments": {"x": 3},
                "question": "Contract?",
            }
        ]
    }
    original = deepcopy(payload)
    result = decoder()({"changed_ids": ["s::new", "s::other"]}, payload)
    assert result["probes"][0]["basis"] == "s::new" and payload == original
    result["probes"][0]["basis"] = "exact changed tool_id"
    assert result == original


@pytest.mark.parametrize(
    "basis", ["arbitrary explanation", "s::one or s::two", "exact changed tool_id"]
)
def test_ambiguous_or_unsupported_reference_fails_closed(basis):
    payload = {"probes": [{"basis": basis, "tool_id": "s::peer"}]}
    with pytest.raises(ValueError):
        decoder()({"changed_ids": ["s::one", "s::two"]}, payload)


def test_literal_id_in_annotation_can_be_uniquely_decoded():
    payload = {"probes": [{"basis": "exact changed tool_id s::one (new)", "tool_id": "s::one"}]}
    assert (
        decoder()({"changed_ids": ["s::one", "s::two"]}, payload)["probes"][0]["basis"] == "s::one"
    )


def test_single_root_for_peer_is_unique_without_editing_peer_identity():
    payload = {"probes": [{"basis": "exact changed tool_id", "tool_id": "s::peer"}]}
    result = decoder()({"changed_ids": ["s::one"]}, payload)
    assert result["probes"][0] == {"basis": "s::one", "tool_id": "s::peer"}

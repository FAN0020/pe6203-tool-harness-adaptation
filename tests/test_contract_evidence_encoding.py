import copy
import json
from pathlib import Path

import pytest

from pe6203.contract_evidence_encoding import decode, encode, compile_knowledge, normalize
from pe6203.selective import adapt_result

ROOT = Path(__file__).resolve().parents[1]
OBS = json.loads((ROOT / "experiments/observed-contract-probes-v1.json").read_text())["observations"]


@pytest.mark.parametrize("stage", ["middle", "late"])
@pytest.mark.parametrize("layout", ["dictionary", "contrastive"])
def test_exact_roundtrip_of_all_original_probe_evidence(stage, layout):
    values = [normalize(o) for o in OBS if o["stage"] == stage]
    packed = encode(values, layout)
    assert decode(packed) == values
    if layout == "dictionary":
        assert len(json.dumps(packed)) < len(json.dumps(values))


def test_missing_response_reference_fails_closed():
    packed = encode([normalize(OBS[0])], "dictionary")
    packed["rows"][0]["result"] = "nonexistent"
    with pytest.raises(ValueError):
        decode(packed)


def test_conflicting_probe_fields_fail_instead_of_silent_drop():
    observation = copy.deepcopy(OBS[0])
    observation["question"] = "not allowed"
    with pytest.raises(ValueError):
        normalize(observation)


def test_only_changed_observed_host_can_receive_encoded_evidence():
    folder = ROOT / "results/raw/observed-contract-pilot-20261031/catalogs/133"
    old = json.loads((folder / "early.json").read_text())
    target = json.loads((folder / "late.json").read_text())
    base = adapt_result(old, target)
    knowledge, changes = compile_knowledge(base, target, OBS, "dictionary")
    before = {t["tool_id"]: t for t in base["knowledge"]["tools"]}
    after = {t["tool_id"]: t for t in knowledge["tools"]}
    assert [k for k in before if before[k] != after[k]] == ["math-mcp::validate_syntax"]
    assert len(changes) == 1
    restored = copy.deepcopy(knowledge)
    next(t for t in restored["tools"] if t["tool_id"] == "math-mcp::validate_syntax")["usage_rules"] = []
    assert restored == base["knowledge"]

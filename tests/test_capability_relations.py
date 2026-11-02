import importlib
import importlib.util

import pytest


def implementation():
    assert importlib.util.find_spec("pe6203.capability_relations") is not None, "Missing relation compiler"
    return importlib.import_module("pe6203.capability_relations")


def envelope(text, error=False):
    return {"content": [{"type": "text", "text": text}], "isError": error}


def test_native_invalid_syntax_is_not_promoted_by_successful_envelope():
    result = implementation().classify(envelope("Syntax errors:\nLine 1: Expected expression"), "syntax")
    assert result["envelope_success"] is True
    assert result["syntax_valid"] is False
    assert result["evaluated"] is False


def test_syntax_success_cannot_claim_evaluation_or_numeric_result():
    result = implementation().classify(envelope("Expression is syntactically valid."), "validate_only")
    assert result["syntax_valid"] is True
    assert result["evaluated"] is False
    assert result["numeric_value"] is False


@pytest.mark.parametrize("value,kind,want", [(5, "number", True), (None, "number", False), (True, "boolean", False), ("blue", "string", False)])
def test_numeric_evaluation_requires_a_finite_number(value, kind, want):
    import json
    result = implementation().classify(envelope(json.dumps({"expression": "probe", "result": value, "type": kind})), "evaluate")
    assert result["evaluated"] is True
    assert result["numeric_value"] is want


def test_unknown_response_fails_closed_instead_of_fabricating_a_predicate():
    with pytest.raises(ValueError, match="Unrecognized"):
        implementation().classify(envelope("A different server response"), "syntax")


def test_counterexample_refutes_only_observed_implication_not_its_reverse():
    rows = [
        {"expression": "a", "syntax_envelope": True, "syntax_valid": True, "evaluated": False, "numeric_value": False},
        {"expression": "b", "syntax_envelope": True, "syntax_valid": True, "evaluated": True, "numeric_value": True},
        {"expression": "c", "syntax_envelope": True, "syntax_valid": False, "evaluated": False, "numeric_value": False},
    ]
    relations = {(r["if"], r["then"]): r for r in implementation().infer_relations(rows)}
    assert relations[("syntax_valid", "evaluated")]["counterexamples"] == ["a"]
    assert relations[("syntax_envelope", "syntax_valid")]["counterexamples"] == ["c"]
    assert relations[("evaluated", "syntax_valid")]["status"] == "not_falsified_on_these_inputs"
    assert len(relations) == 12

"""Source layout constraints are format guards, not Python correctness tests."""

from jsonschema import Draft202012Validator

from pe6203.execution_control_v6 import SYSTEM_RULE, VERSION, artifact_response_format


def payload(source):
    return {"artifact": {"path": "artifact.py", "language": "python", "source": source},
            "summary": "Runtime behavior has not been verified."}


def validator():
    return Draft202012Validator(artifact_response_format()["json_schema"]["schema"])


def test_rejects_explanatory_prose_or_comment_without_a_real_line_break():
    check = validator()
    assert not check.is_valid(payload("This is a complete implementation."))
    assert not check.is_valid(payload("# implementation follows def compute(value): return value"))
    assert not check.is_valid(payload(r"def compute(value):\n    return value + 1"))


def test_accepts_multiline_python_with_preserved_indentation():
    check = validator()
    source = "def compute(value):\n    return value + 1\n"
    assert check.is_valid(payload(source))
    field = artifact_response_format()["json_schema"]["schema"]["properties"]["artifact"]["properties"]["source"]
    assert "runnable Python" in field["description"]
    assert "top-level summary" in field["description"]


def test_newline_pattern_does_not_claim_python_correctness_or_interface_presence():
    # A format guard accepts these strings; the existing parser and finite tests
    # remain responsible for rejecting bad Python or missing task interfaces.
    check = validator()
    assert check.is_valid(payload("# only a comment\n# still a comment\n"))
    assert check.is_valid(payload("def broken(:\n    pass\n"))


def test_existing_object_contract_and_version_are_not_relaxed():
    check = validator()
    good = payload("pass\n")
    assert check.is_valid(good)
    assert not check.is_valid({**good, "invented_validation": "passed"})
    assert not check.is_valid({"artifact": {**good["artifact"], "summary": "nested"}})
    assert VERSION == "v6-execution-control-1"
    assert "When an artifact output contract is active" in SYSTEM_RULE

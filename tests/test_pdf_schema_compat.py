from copy import deepcopy

import pytest
from jsonschema import Draft4Validator, Draft202012Validator

from pe6203.transport import compatible_input_schema


@pytest.mark.parametrize("exclusive", [True, False])
def test_pdf_page_bound_preserves_validation_and_source(exclusive):
    bound = {"type": "integer", "minimum": 0, "exclusiveMinimum": exclusive}
    schema = {
        "type": "object",
        "properties": {
            "sources": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "pages": {"anyOf": [{"type": "array", "items": bound}, {"type": "string"}]}
                    },
                },
            }
        },
        "examples": [{"exclusiveMinimum": True, "minimum": 0}],
    }
    before = deepcopy(schema)
    modern, audit = compatible_input_schema("@sylphlab/pdf-reader-mcp", "read_pdf", schema)
    Draft202012Validator.check_schema(modern)
    for value in [-1, 0, 1, 2.5, "1-3"]:
        args = {"sources": [{"pages": value if isinstance(value, str) else [value]}]}
        assert Draft4Validator(schema).is_valid(args) == Draft202012Validator(modern).is_valid(args)
    assert schema == before
    assert modern["examples"] == before["examples"]
    assert audit["original"] == bound
    untouched, audit = compatible_input_schema("other", "read_pdf", schema)
    assert untouched == schema and audit is None


def test_modern_or_unknown_pdf_schema_is_not_reinterpreted():
    for schema in ({"type": "object"}, {"type": "number", "exclusiveMinimum": 0}):
        result, audit = compatible_input_schema("@sylphlab/pdf-reader-mcp", "read_pdf", schema)
        assert result == schema and audit is None

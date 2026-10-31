"""Frozen, candidate-only reconciliation of contradicted descriptive annotations.

Schema constraints and original Selective Patch validation remain unchanged.
"""

from copy import deepcopy

from .selective import validate_adaptation

TOOL_ID = "math-mcp::validate_syntax"
ANNOTATIONS = {
    "description": "Check only the native mathematical grammar and return a plain-text syntax "
    "verdict. Read that text: syntax errors can be returned with isError=false. "
    "This does not evaluate the expression, validate Python source, or establish "
    "secure execution. The native grammar accepts ^ for exponentiation and "
    "rejects Python **.",
    "parameters.properties.detailed.description": "Compatibility flag accepted by this version. "
    "The handler ignores it and returns the same "
    "plain-text syntax verdict, without "
    "additional detail.",
    "parameters.properties.allow_variables.description": "Boolean compatibility argument. The "
    "handler ignores its value; variable "
    "references remain syntactically valid "
    "even when false. It does not enforce "
    "a variable restriction.",
    "parameters.properties.show_ast.description": "Boolean compatibility argument. The handler "
    "ignores it and returns a plain-text syntax "
    "verdict without an AST.",
    "parameters.properties.check_balanced.description": "Boolean compatibility argument. The "
    "handler does not use it to enable or "
    "disable extra balancing checks. "
    "Ordinary native grammar parsing still "
    "applies.",
    "parameters.properties.max_depth.description": "Integer compatibility argument. The "
    "dispatcher requires an integer from 1 "
    "through 100 when supplied, but the handler "
    "ignores it and does not enforce a "
    "nesting-depth limit.",
}
ORIGINAL = {
    "middle": {
        "description": "Validate mathematical expression syntax against grammar",
        "parameters.properties.detailed.description": "If true, return a more detailed "
        "validation result when supported",
        "parameters.properties.allow_variables.description": "If true, allow variable "
        "references during "
        "validation when supported",
    },
    "late": {
        "description": "Validate mathematical expression syntax against grammar",
        "parameters.properties.detailed.description": "If true, return a more detailed "
        "validation result when supported",
        "parameters.properties.allow_variables.description": "Explicitly specify whether "
        "variable references are "
        "allowed during validation",
        "parameters.properties.show_ast.description": "If true, include the abstract "
        "syntax tree (AST) structure in the "
        "validation result",
        "parameters.properties.check_balanced.description": "If true, perform additional "
        "validation to ensure all "
        "brackets and parentheses are "
        "properly balanced",
        "parameters.properties.max_depth.description": "Maximum allowed nesting depth for "
        "expressions (e.g., nested "
        "parentheses or function calls). If "
        "specified, validation fails if "
        "depth exceeds this limit",
    },
}


def expected_reconciliation(base, target, feedback):
    """Return the only allowed candidate and a field-level provenance log."""
    knowledge = deepcopy(base["knowledge"])
    changes = {c["tool_id"]: c for c in base["diff"]["changed"] + base["diff"]["added"]}
    if TOOL_ID not in changes:
        return knowledge, []
    stage = target["version"]
    verified = [
        o
        for o in feedback
        if o.get("stage") == stage
        and o.get("server") == "math-mcp"
        and o.get("tool") == "validate_syntax"
    ]
    facts = {
        "kind": "contract_reconcile_v1",
        "handler_reads_expression_only": True,
        "syntax_error_is_error_false": True,
        "caret_accepted_python_power_rejected": True,
    }
    if stage not in ORIGINAL or len(verified) != 1 or verified[0].get("result") != facts:
        raise ValueError("Missing verified annotation reconciliation evidence")
    tool = next(t for t in knowledge["tools"] if t["tool_id"] == TOOL_ID)
    log = []
    for path, before in ORIGINAL[stage].items():
        node = tool
        parts = path.split(".")
        try:
            for key in parts[:-1]:
                node = node[key]
            if node[parts[-1]] != before:
                raise ValueError("Unverified native description: " + path)
        except (KeyError, TypeError) as exc:
            raise ValueError("Unverified native annotation path: " + path) from exc
        node[parts[-1]] = ANNOTATIONS[path]
        log.append(
            {
                "operation": "reconcile_annotation",
                "tool_id": TOOL_ID,
                "basis": [changes[TOOL_ID]["change_id"]],
                "path": path,
                "before": before,
                "after": ANNOTATIONS[path],
                "evidence": "frozen_16_synthetic_probes_and_expression_only_handler",
            }
        )
    return knowledge, log


def validate_reconciliation(candidate, old, target, base, feedback):
    """Fail closed for all changes except the frozen descriptive substitutions."""
    expected, log = expected_reconciliation(base, target, feedback)
    if candidate != expected:
        return {
            "errors": ["Candidate differs from exact verified annotation allowlist"],
            "checks": {"annotation_count": len(log)},
        }
    projection = deepcopy(candidate)
    by_id = {t["tool_id"]: t for t in projection["tools"]}
    for entry in log:
        node = by_id[entry["tool_id"]]
        parts = entry["path"].split(".")
        for key in parts[:-1]:
            node = node[key]
        node[parts[-1]] = entry["before"]
    result = validate_adaptation(projection, old, target, base["diff"])
    result["checks"]["annotation_count"] = len(log)
    return result

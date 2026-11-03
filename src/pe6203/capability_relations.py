"""Finite cross-operation evidence; no benchmark inputs or runtime changes."""

import hashlib
import itertools
import json
import math
from copy import deepcopy

from .selective import canonical

PREDICATES = ("syntax_envelope", "syntax_valid", "evaluated", "numeric_value")
APPROVED_OBSERVATIONS_SHA = "3ab9f0792e0786fb6bb2c81024986d3d942a1ed82391d3c690250a150e87bb22"
HOST = "math-mcp::validate_syntax"


def classify(result, mode):
    if mode not in {"syntax", "validate_only", "evaluate"}:
        raise ValueError("Unknown operation mode")
    content = result.get("content", [])
    if len(content) != 1 or content[0].get("type") != "text" or "diagnostic_exception" in result:
        raise ValueError("Unrecognized native envelope")
    text = content[0]["text"]
    out = dict(
        envelope_success=not result.get("isError", False),
        syntax_valid=False,
        evaluated=False,
        numeric_value=False,
        text=text,
    )
    if (
        text == "Expression is syntactically valid."
        and mode != "evaluate"
        and out["envelope_success"]
    ):
        out["syntax_valid"] = True
    elif text.startswith("Syntax errors:"):
        pass
    elif (
        mode == "evaluate" and text.startswith("Evaluation error:") and not out["envelope_success"]
    ):
        out["syntax_valid"] = True
    elif mode == "evaluate" and out["envelope_success"]:
        try:
            value = json.loads(text)
            if set(value) != {"expression", "result", "type"}:
                raise ValueError()
        except (ValueError, TypeError):
            raise ValueError("Unrecognized evaluation response") from None
        out.update(syntax_valid=True, evaluated=True)
        number = value["result"]
        out["numeric_value"] = (
            value["type"] == "number" and type(number) in (int, float) and math.isfinite(number)
        )
    else:
        raise ValueError("Unrecognized native response")
    return out


def infer_relations(rows):
    if not rows or len({r["expression"] for r in rows}) != len(rows):
        raise ValueError("Distinct complete witness rows required")
    if any(type(r.get(key)) is not bool for r in rows for key in PREDICATES):
        raise ValueError("Predicates must be observed booleans")
    edges = []
    for left, right in itertools.permutations(PREDICATES, 2):
        counter = [r["expression"] for r in rows if r[left] and not r[right]]
        edges.append(
            {
                "if": left,
                "then": right,
                "status": "falsified" if counter else "not_falsified_on_these_inputs",
                "counterexamples": counter,
            }
        )
    return edges


def compile_knowledge(base, target, feedback):
    knowledge = deepcopy(base["knowledge"])
    changed = {r["tool_id"] for r in base["diff"]["changed"] + base["diff"]["added"]}
    if HOST not in changed:
        return knowledge, []
    if hashlib.sha256(canonical(feedback).encode()).hexdigest() != APPROVED_OBSERVATIONS_SHA:
        raise ValueError("Unreviewed cross-operation evidence")
    certs = [r["result"] for r in feedback if r["stage"] == target["version"]]
    if len(certs) != 1 or certs[0]["semantic_review"] != "accepted":
        raise ValueError("Missing accepted stage certificate")
    cert = certs[0]
    native = {t["tool_id"]: t for t in target["tools"]}
    for identity, expected in cert["catalog_hashes"].items():
        if (
            identity not in native
            or hashlib.sha256(canonical(native[identity]).encode()).hexdigest() != expected
        ):
            raise ValueError("Native contract drift")
    if infer_relations(cert["rows"]) != cert["relations"]:
        raise ValueError("Unsupported implication inference")
    note = {
        "kind": "finite_cross_operation_contract_relations",
        "operations": cert["argument_domain"],
        "predicates": {
            "syntax_envelope": "validate_syntax outer isError is false",
            "syntax_valid": "validate_syntax text explicitly accepts syntax",
            "evaluated": "normal evaluate returned a result JSON",
            "numeric_value": "normal evaluate returned a finite JSON number, not boolean/string/array/null",
        },
        "paired_observations": cert["rows"],
        "relations": cert["relations"],
        "validation_only_mode": "evaluate(validate_only=true) matched validate_syntax on all these inputs; both interfaces remain available.",
        "sequence_state_receipts": cert["sequence_effects"],
        "scope": "Finite native-language observations, not a universal grammar or security certificate. A falsified implication has a concrete counterexample; not_falsified_on_these_inputs is not a theorem. No observation verifies another implementation or runtime. Sequence effects cover this complete ordered probe sequence only.",
    }
    tool = next(t for t in knowledge["tools"] if t["tool_id"] == HOST)
    before = deepcopy(tool["usage_rules"])
    tool["usage_rules"].append(
        "Cross-operation evidence: " + json.dumps(note, ensure_ascii=False, separators=(",", ":"))
    )
    return knowledge, [
        {
            "tool_id": HOST,
            "field": "usage_rules",
            "before": before,
            "after": deepcopy(tool["usage_rules"]),
            "reason": "native counterexample-supported finite capability relations",
        }
    ]

"""Finite cross-operation evidence; no benchmark inputs or runtime changes."""

import itertools
import json
import math

PREDICATES = ("syntax_envelope", "syntax_valid", "evaluated", "numeric_value")


def classify(result, mode):
    if mode not in {"syntax", "validate_only", "evaluate"}:
        raise ValueError("Unknown operation mode")
    content = result.get("content", [])
    if len(content) != 1 or content[0].get("type") != "text" or "diagnostic_exception" in result:
        raise ValueError("Unrecognized native envelope")
    text = content[0]["text"]
    out = dict(envelope_success=not result.get("isError", False), syntax_valid=False,
               evaluated=False, numeric_value=False, text=text)
    if text == "Expression is syntactically valid." and mode != "evaluate" and out["envelope_success"]:
        out["syntax_valid"] = True
    elif text.startswith("Syntax errors:"):
        pass
    elif mode == "evaluate" and text.startswith("Evaluation error:") and not out["envelope_success"]:
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
        out["numeric_value"] = value["type"] == "number" and type(number) in (int, float) and math.isfinite(number)
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
        edges.append({"if": left, "then": right,
                      "status": "falsified" if counter else "not_falsified_on_these_inputs",
                      "counterexamples": counter})
    return edges

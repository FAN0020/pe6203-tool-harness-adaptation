"""Compile all frozen native modes after the explicit required-argument repair."""
import hashlib
import json
from pathlib import Path

from pe6203.capability_relations import classify, infer_relations
from pe6203.selective import canonical

E = Path(__file__).resolve().parent
ROOT = E.parents[2]


def main():
    read = lambda p: json.loads(p.read_text())
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    plan = read(E / "native-plan.json")
    repair = read(E / "required-argument-repair-plan.json")
    original = read(E / "native-result.json")["records"]
    fixed = read(E / "repair-result.json")["records"]
    assert len(original) == 72 and len(fixed) == 12
    records = [r for r in original if r["run"] != "late-syntax"] + fixed
    observations = []
    for stage in ["middle", "late"]:
        modes = {}
        for mode in ["syntax", "validate_only", "evaluate"]:
            identity = stage + "-" + mode
            rows = [r for r in records if r["run"] == identity]
            expected = next(r for r in (repair if identity == "late-syntax" else plan)["runs"] if r["id"] == identity)["calls"]
            assert [{k: r[k] for k in ["tool", "arguments"]} for r in rows] == expected
            assert len(rows) == 12
            modes[mode] = rows
        matrix = []
        for i, expression in enumerate(plan["expressions"], 1):
            classified = {m: classify(modes[m][i]["result"], m) for m in modes}
            assert modes["syntax"][i]["result"] == modes["validate_only"][i]["result"]
            matrix.append({
                "expression": expression,
                "syntax_envelope": classified["syntax"]["envelope_success"],
                "syntax_valid": classified["syntax"]["syntax_valid"],
                "evaluated": classified["evaluate"]["evaluated"],
                "numeric_value": classified["evaluate"]["numeric_value"],
                "native_text": {m: v["text"] for m, v in classified.items()},
            })
        relations = infer_relations(matrix)
        for pair in [("syntax_envelope", "syntax_valid"), ("syntax_valid", "evaluated")]:
            assert next(r for r in relations if (r["if"], r["then"]) == pair)["status"] == "falsified"
        catalog = read(ROOT / f"results/raw/evidence-contrastive-pilot-ready-20261102/catalogs/133/{stage}.json")
        cert = {
            "kind": "capability_relation_matrix_v1", "stage": stage, "semantic_review": "accepted",
            "rows": matrix, "relations": relations,
            "sequence_effects": {m: {"before": v[0]["result"], "after": v[-1]["result"]} for m, v in modes.items()},
            "native_sources": {name: sha(E / name) for name in ["native-result.json", "repair-result.json"]},
            "catalog_hashes": {t["tool_id"]: hashlib.sha256(canonical(t).encode()).hexdigest() for t in catalog["tools"] if t["server_id"] == "math-mcp"},
            "source_hashes": plan["files"],
            "argument_domain": {"validate_syntax": "expression string; " + ("allow_variables=false explicitly" if stage == "late" else "allow_variables omitted, dispatcher default false") + "; other flags absent", "evaluate_validate_only": "same expression, validate_only=true", "evaluate": "same expression, validate_only omitted/false"},
        }
        observations.append({"stage": stage, "server": "math-mcp", "result": cert})
    feedback = {"kind": "task_free_cross_operation_relations", "observations": observations}
    (ROOT / "experiments/capability-relation-matrix-feedback-v1.json").write_text(json.dumps(feedback, ensure_ascii=False, indent=2) + "\n")
    review = {
        "accepted": True, "native_calls_total": 84, "native_calls_selected": 72, "catalog_calls_total": 7,
        "original_failure_retained": "10 invalid syntax calls plus 2 state reads in original late-syntax sequence; repair changes the missing required argument, not a stochastic rerun.",
        "checks": ["Every selected response recognized; both required counterexample relations exist in each stage.", "All10 syntax/validate_only responses match per stage; all interfaces retained.", "JSON null with type number is not a finite numeric value.", "State difference covers the whole fixed sequence, not arbitrarily attributed to a single call."],
        "source": "Released handlers parse first; syntax-only returns validity; normal mode runs evaluator.",
        "not_claimed": ["universal implication", "security", "Python correctness", "benchmark success"],
        "observations_sha256": hashlib.sha256(canonical(observations).encode()).hexdigest(),
        "goal_complete": False,
    }
    (E / "semantic-review.json").write_text(json.dumps(review, indent=2) + "\n")
    print(json.dumps({k: review[k] for k in ["accepted", "native_calls_total", "observations_sha256"]}))


if __name__ == "__main__":
    main()

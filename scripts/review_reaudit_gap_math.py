"""Static supplemental math review. Never executes generated code."""

import ast
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "results/evidence/unified-reaudit-20261102/historical-products"
NOTES = {
    "task133-late-selective_patch-r0": (
        ["fail", "pass", "pass"],
        [
            "Sample numeric results agree, but unsupported ** rejection is presented as deliberate exponent-DoS protection and tools as exactly the secure allowlist pattern. Syntax acceptance is not a security proof; no probe establishes that general restriction.",
            "Usable AST/operator allowlist, process/resource limits, generic error handling and OWASP mapping; ignored flags not claimed as enforcement.",
            "Static review finds declared no-variable/no-Pow allowlist, length/node caps and shown benign tests consistent. Arithmetic exceptions are explicitly listed for caller handling; no claim code was run. This is limited rubric conformance, not security certification.",
        ],
    ),
    "task133-late-sufficiency_feedback-r0": (
        ["pass", "pass", "fail"],
        [
            "Paired variable flags and all returned examples support syntax/security distinction; unsupported ** does not by itself establish absence of every exponent syntax.",
            "Actionable AST allowlist and bounded arithmetic, isolation/logging/error guidance; explicitly rejects treating ignored variable flag as enforcement.",
            "Own reject test fullwidth digits １ + ２ is accepted after NFKC normalization to ASCII 1 + 2. This contradicts declared rejection/test; no execution needed to establish normalization path.",
        ],
    ),
    "task133-middle-selective_patch-r0": (
        ["fail", "pass", "fail"],
        [
            "Python 2 ^ 3 ^ 2 is3, not512; null is attributed to resource/overflow guards without evidence. Useful syntax-vs-security distinction does not rescue incorrect interpretation.",
            "Actionable allowlist, quotas, resource, error and OWASP guidance.",
            "Magnitude checked only after evaluation: repeated permitted constant-exponent Pow nodes can perform unbounded intermediate work first. Numeric symbol values not checked; arithmetic exceptions not normalized to declared ExprRejected. No generated code executed.",
        ],
    ),
    "task133-middle-sufficiency_feedback-r0": (
        ["pass", "fail", "fail"],
        [
            "Sample syntax/evaluation results match including null for division by zero; distinguishes syntax acceptance and evaluator namespace.",
            "Useful AST advice is undermined by suggesting parse_expr with empty global_dict/evaluate=False as untrusted-input alternative. Official SymPy1.14 docs warn parse_expr uses eval; evaluate=False suppresses simplification, not execution.",
            "Root numeric constant and function-return branches bypass declared magnitude/finite checks; 1e309 returns Infinity directly, and abs(1e309) also bypasses bound. Function domain/arity errors escape declared ExpressionError.",
        ],
    ),
}


def main():
    folder = P / "selective-search-v2.1-development-20261031"
    for cell, (states, notes) in NOTES.items():
        f = folder / (cell + ".json")
        d = json.loads(f.read_text())
        props = dict(zip(["validation", "guidance", "implementation_consistency"], states))
        parsed = []
        for code in re.findall(r"```python\n(.*?)```", d["answer"], re.S):
            try:
                ast.parse(code)
                parsed.append(True)
            except SyntaxError as exc:
                parsed.append({"syntax_error": str(exc)})
        r = {
            "cell_id": cell,
            "task_id": 133,
            "input_sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
            "trace_sha256": d["trace_sha256"],
            "properties": props,
            "core_pass": all(v == "pass" for v in props.values()),
            "evidence": dict(zip(props, notes)),
            "python_blocks_parse": parsed,
            "generated_code_executed": False,
            "review_phase": "supplemental_posthoc_scores_exposed",
            "review_source": "scripts/review_reaudit_gap_math.py",
            "limitations": [
                "Static inspection only; no exhaustive security proof.",
                "Same coordinator with scores exposed; not independent validation.",
            ],
        }
        if cell == "task133-middle-sufficiency_feedback-r0":
            r["primary_source"] = (
                "https://docs.sympy.org/1.14.0/modules/parsing.html#sympy.parsing.sympy_parser.parse_expr"
            )
        (folder / "reviews" / f.name).write_text(json.dumps(r, ensure_ascii=False, indent=2) + "\n")
    folder = P / "selective-search-confirmation-r2-20261031"
    f = folder / "task133-late-selective_patch-r0.json"
    d = json.loads(f.read_text())
    assert not d["answer"] and not d["calls"]
    r = {
        "cell_id": f.stem,
        "task_id": 133,
        "input_sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
        "trace_sha256": d["trace_sha256"],
        "properties": dict.fromkeys(
            ["validation", "guidance", "implementation_consistency"], "unknown"
        ),
        "core_pass": False,
        "evidence": "No visible answer or tool result after failed execution. Unknown product properties, not an inferred code bug.",
        "review_phase": "supplemental_posthoc_scores_exposed",
        "review_source": "scripts/review_reaudit_gap_math.py",
    }
    (folder / "reviews" / f.name).write_text(json.dumps(r, indent=2) + "\n")
    print("5 supplemental math reviews")


if __name__ == "__main__":
    main()

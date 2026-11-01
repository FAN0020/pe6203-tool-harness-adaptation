"""Replay dated, post-hoc math product judgments without executing generated code.

Notes were adjudicated against visible answers and native observations. AST
parsing checks syntax only; it never establishes behavioral/security correctness.
"""
import ast
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'results/evidence/unified-reaudit-20261102/historical-products/selective-search-confirmation-r1-20261031'

# validation, guidance, implementation, and concrete evidence for each property.
NOTES = {
    'early-selective_patch-r0': ('fail', 'pass', 'fail',
        'Recorded individual probes correct, but claims parser rejects everything except pure arithmetic; finite rejection probes do not establish that and native grammar accepts names/calls/strings.',
        'Actionable allowlist, OWASP mapping, input/resource controls and logging.',
        'Main safe_eval still maps Pow to unguarded operator.pow; separate guard_pow is never connected. Its own rejection test expects power bomb rejection, and handle catches ValueError but not division errors.'),
    'early-selective_patch-r1': ('pass', 'pass', 'fail',
        'Native arithmetic, syntax-valid eval spelling, null division and attribute rejection match observations; separates parse from semantic control.',
        'Usable Python AST, resource and OWASP recommendations.',
        'Own test requires SafeMathError for1/0, but evaluator propagates ZeroDivisionError. Later advice to catch it is not implemented in the advertised code/test pair.'),
    'early-selective_patch-r2': ('pass', 'pass', 'fail',
        'Three displayed benign/malicious probes match native observations; no generated-Python execution established.',
        'Usable AST/resource/OWASP advice; library suggestions not independently certified.',
        'Advertised generic error wrapper catches only ValueError;1/0 escapes as ZeroDivisionError. MAX_ABS_VALUE bounds constants only, so expressions exceed declared magnitude ceiling.'),
    'early-sufficiency_feedback-r0': ('fail', 'pass', 'fail',
        'Correct null/dialect observations, but attributes rejected by syntax do not establish claimed non-registry call blocking; undefined argument does not establish typed name-binding security.',
        'Actionable three-layer allowlist/name/resource advice and OWASP links before truncation.',
        'Reference implementation ends inside UnaryOp handling; no completed evaluator/entry point. Open Python fence preserved, not mistaken for absent code.'),
    'early-sufficiency_feedback-r1': ('pass', 'pass', 'fail',
        'Displayed probe outcomes and dialect/null distinctions match;10 nested parentheses is finite evidence, not proof of unlimited parser depth.',
        'Usable OWASP, AST, numeric bounds and process-isolation recommendations.',
        'Own rejected case50 pairs of parentheses around1 has length101 and same shallow AST as1, so it is accepted. AST-depth cap does not implement claimed raw-parenthesis rejection.'),
    'early-sufficiency_feedback-r2': ('pass', 'pass', 'fail',
        'Separates syntactic acceptance of named calls from evaluation allowlist; null/precedence/associativity observations supported.',
        'Usable Python allowlist, resources, OWASP and service error boundary.',
        'Own benign test uses2^3 but Python AST is BitXor, absent BINOPS, so expected32.25 cannot pass. Root literal bypasses MAX_ABS_VALUE; Decimal floor division also has different negative semantics.'),
    'middle-selective_patch-r0': ('fail', 'pass', 'fail',
        'Claims identifiers/arbitrary calls all killed at tokenizer despite accepted named expressions and sqrt; confuses grammar coverage with security.',
        'Useful allowlist, finite result, resource and OWASP guidance, with contradictions captured in other properties.',
        'Walk tests ast.Pow then reads n.right, but operator node has no right attribute. Benign power fails; own test2^10 also unsupported, and1+1 returnsint despite requiredfloat.'),
    'middle-selective_patch-r1': ('fail', 'pass', 'fail',
        'Measured native results mostly match, but2^100 is an exactly representable binary power: scientific notation alone does not prove asserted precision loss.',
        'Usable Python AST/Decimal/resource/OWASP controls.',
        'Allowed round with2arguments converts ndigits tofloat, causing uncaught TypeError. abs ignores extra arguments; declared MathExprError boundary does not cover these failures.'),
    'middle-selective_patch-r2': ('fail', 'pass', 'fail',
        'Claims sqrt(16) rejected/no functions, but only compound2**3+sqrt(16) was rejected; cannot attribute rejection to sqrt. Arithmetic/null/modulo observations otherwise match.',
        'Actionable allowlist, numeric/resource and OWASP recommendations.',
        'Main code has illegal assignment expression to budget[0], a SyntaxError; auxiliary Decimal snippet references unimported InvalidOperation.'),
    'middle-sufficiency_feedback-r0': ('unknown', 'unknown', 'unknown',
        'No final answer; native probes alone do not deliver interpreted validation.',
        'No final user-facing guidance.', 'No final implementation or actionable substitute; empty answer is not pass.'),
    'middle-sufficiency_feedback-r1': ('pass', 'pass', 'fail',
        'Native lambda acceptance, corrected power dialect, null and specific nesting observations match; finite nesting probe does not establish unlimited depth.',
        'Usable default-deny AST and explicit resource limits in delivered text; no complete security certification.',
        'Unclosed main reference ends at left = _eval(node: syntactically incomplete and unusable. Short closed example is explicitly unsafe, not the delivered evaluator.'),
    'middle-sufficiency_feedback-r2': ('pass', 'pass', 'fail',
        'Two displayed observations match; explicitly distinguishes syntax check from Python safety.',
        'Usable OWASP, AST/resource/error handling recommendations.',
        'Root numeric literal1e309 returns DecimalInfinity without finite/magnitude check; unary path also bypasses bounds. DecimalOverflow is not caught by OverflowError.'),
    'late-selective_patch-r0': ('fail', 'pass', 'fail',
        'Depth-flag contrasts and null/modulo results match, but unsupported** is described as no exponent support; alternative^ not ruled out. One quoted open-chain diagnostic differs from actual text.',
        'Usable deny-by-default AST, resource and numeric controls; OWASP linkage before truncated tail.',
        'Advertised isolation wrapper ends at if proc.returncode != and is invalid Python; complete lower-level evaluator does not make this recommended wrapper usable.'),
    'late-selective_patch-r1': ('pass', 'pass', 'fail',
        'Displayed syntax and arithmetic probes match; rejected payload is not proof of complete grammar safety.',
        'Usable Python AST/resource/OWASP recommendations.',
        'Allowed exp has no post-call bound, so exp(30) exceeds declared1e12 ceiling. Oversize-input test expects SafeExpressionError but grammar raises base ValueError.'),
    'late-selective_patch-r2': ('pass', 'pass', 'fail',
        'Displayed string/call/depth/null outcomes match; unbounded nesting is overgeneralized from one finite probe.',
        'Actionable allowlist, resource and OWASP guidance.',
        '1/0 and sqrt(-1) raise native exceptions outside ExpressionRejected; shown service catches only ExpressionRejected.100 pairs of parentheses pass although listed REJECT; timer only detects after execution.'),
    'late-sufficiency_feedback-r0': ('unknown', 'pass', 'pass',
        'Single benign syntax probe delivered correctly, but parenthetical variables-disallowed is not established by ignored flag; no contrast validates that asserted boundary.',
        'Actionable allowlist, length/depth/exponent and OWASP advice.',
        'Under stated numeric-only literal/operator interface, listed benign and rejection cases are consistent with code. Missing optional production controls remain limitations, not invented acceptance requirements.'),
    'late-sufficiency_feedback-r1': ('fail', 'fail', 'pass',
        'Claims variables permitted only when explicitly enabled; no contrasting evidence and flag is ignored. Named formula itself contradicts broad identifiers-rejected language.',
        'Useful AST advice, but explicitly treats observed variable flag as an enforced security boundary, contrary to frozen guidance requirement.',
        'Name branch exists and resolves supplied variables; own arithmetic/variable/rejection cases consistent. No additional numeric ceiling promised in code; not full security certification.'),
    'late-sufficiency_feedback-r2': ('pass', 'pass', 'fail',
        'Matched true/false control observation supports ignored allow_variables; depth/null/dialect distinctions reflect calls.',
        'Actionable AST and length/depth/node/exponent recommendations with OWASP attribution before truncated tail.',
        'Constant case returns1e309 asinf without _guard; all top-level literal bounds bypassed. Allowed min(1) raises TypeError, contradicting stated1argument signature.'),
}


def main():
    for stem, (v, g, i, vn, gn, inn) in NOTES.items():
        f = FOLDER / f'task133-{stem}.json'
        d = json.loads(f.read_text())
        answer = d.get('answer') or ''
        blocks = []
        for match in re.finditer(r'```python\n(.*?)(?:```|\Z)', answer, re.S):
            code = match.group(1)
            try:
                ast.parse(code)
                result = {'parses': True}
            except SyntaxError as exc:
                result = {'parses': False, 'line': exc.lineno, 'error': exc.msg}
            result['closed_fence'] = match.group(0).endswith('```')
            result['sha256'] = hashlib.sha256(code.encode()).hexdigest()
            blocks.append(result)
        props = dict(validation=v, guidance=g, implementation_consistency=i)
        review = {'cell_id': f.stem, 'task_id': 133,
                  'input_sha256': hashlib.sha256(f.read_bytes()).hexdigest(),
                  'trace_sha256': d['trace_sha256'], 'properties': props,
                  'core_pass': all(x == 'pass' for x in props.values()),
                  'evidence': dict(validation=vn, guidance=gn, implementation_consistency=inn),
                  'python_blocks_static_parse': blocks, 'generated_code_executed': False,
                  'review_phase': 'supplemental_posthoc_scores_exposed',
                  'review_source': 'scripts/review_confirmation_math.py',
                  'limitations': ['Static consistency review, not exhaustive security certification.',
                                 'Original scores/labels exposed; not independent validation.',
                                 'New dated supplement; original conclusions preserved.']}
        (FOLDER / 'reviews' / f.name).write_text(json.dumps(review, ensure_ascii=False, indent=2)+'\n')
    print('18 supplemental math reviews recomputed; generated code not executed')


if __name__ == '__main__':
    main()

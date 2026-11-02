"""Final visible-code/contract review; static only, never execute generated code."""

import ast
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "results/evidence/unified-reaudit-20261102/historical-products"
CASES = {
    "selective-search-v1.1-development-20261031": {
        "task133-middle-delta_notes-r0": (
            ("fail", "pass", "fail"),
            "Generalizes math.sqrt rejection to allfunctioncalls andnulloutput to fail-closedsecurity; nativegrammar allowsbarefunctions.",
            "ASTallowlist andlength/node/integer/exponentlimits areactionable.",
            "MAX_INT_BITS describedasmaximumsizeofanyinteger, butappliedonlyafterpower/multiplication allocation. Powmayallocate resultfarabovecapbeforechecking; outputcanalso becomplexdespiteint|floatcontract.",
        ),
        "task133-middle-linked_notes-r0": (
            ("fail", "fail", "unknown"),
            "Claims arbitraryidentifiers rejected beforeevaluation fromlimitedprobes; releasedgrammar admitsnames.",
            "Sympyparse_expr evaluate=False/restrictedlocal_dict presentedas safeparseralternative, butuses eval; flags do not establishuntrustedinputsafety.",
            "Benignprovidedtests staticallyconsistent; subprocess-I imports safe_eval fromunspecifiedinstalledmodule context, soend-to-endisolationexample notverified. No execution claimed.",
        ),
        "task133-middle-feedback_notes-r0": (
            ("fail", "pass", "fail"),
            "Claims actualvalidatoronlypermitsdigits/operators/whitespace; releasedgrammaralsoacceptsname/function/string forms.",
            "Allowlist, noeval andexplicitresourceguard checklistuseful.",
            "Powexecutes withnoguard; ownrejectiontest9**9**9 cannotraiseUnsafeExpression bypolicybeforehugecomputation. SyntaxError/ZeroDivisionError escape genericerrorwrapper.",
        ),
        "task133-late-delta_notes-r0": (
            ("pass", "pass", "fail"),
            "Ignoredflags,batchhandlererror andsyntax/evaluationdifference accuratelyreported.",
            "IndependentASTallowlist/resourcebounds andOWASP controlsuseful.",
            "Own test50nestedparenthesesexpectsdepthrejection, butPythonASTdiscardsparentheses; inputlength101<256 andconstantASTdepth1 passes. NaNvariables alsobypass abs(value)>MAX_ABS_VALUE. No dangerousexpressionexecuted.",
        ),
        "task133-late-linked_notes-r0": (
            ("pass", "fail", "fail"),
            "Actualbenignmalicious/mathresultsreported; no coderuntimevalidation claimed.",
            "Recommends sympify/parse_expr evaluate=False+namespace restriction aslibrarysafeoption without adequateuntrusted-inputqualification.",
            "Referenceuses math.sqrt/log/exp without importingmath, failingdefinition; unguardedPowcontradictsownmaliciousrejecttests. Missingimportsnot soleevidence.",
        ),
        "task133-late-feedback_notes-r0": (
            ("pass", "pass", "fail"),
            "Flagsandnull-as-number outcomes accuratelydistinguished; completecontractdiagnostics retained.",
            "Noeval,ASTallowlist,limits anderror/loggingguidanceusable.",
            "ClaimsDecimalavoidsfloatprecisionloss, butast.Constant alreadyconverteddecimallexeme tobinaryfloat beforeDecimal(str(...));0.10000000000000001 losesdigits. Infinityliteral1e309 alsoaccepted; claimednumericintegritynotestablished.",
        ),
        "task133-middle-selective_patch-r0": (
            ("pass", "fail", "fail"),
            "Twoactualsyntaxresults correctlyreported; no Pythonexecutionproven.",
            "Restrictedlocal/globaldict+parse_expr evaluate=False offeredas remediation despiteeval-basedparser; safervalidatedtokenalternative alsooffered butdoesnotrepairunsafeoption.",
            "Genericerrorhandlingexample re-raises detailedValueError includingparsertext; doesnotimplement itsown promisedgenericclienterror. Exponentcap alone doesnotbound repeatedleft-associatedpowers.",
        ),
        "task133-late-selective_patch-r0": (
            ("fail", "pass", "unknown"),
            "Claimtokenizertweak reopensRCE isunsupported:semanticfunctionallowlist remains. Printeddecimalrepresentation of2^64 alone doesnotprove underlying384unit arithmeticerror.",
            "ASTallowlist,Decimal andresourcebounds areactionable recommendations.",
            "Answerends afterimports/constants; promisedsafe_calc implementationnotdelivered. Missing required propertyunknown,notpass.",
        ),
    },
    "selective-search-v2.1-development-20261031": {
        "task133-middle-sufficiency_notes-r0": (
            ("fail", "pass", "fail"),
            "Claims onlyarithmeticpermitted mirrorsnativebehavior, whichalsoadmitssyntaxstring/functionforms; limitedbenignvalidationdoesnotproveclaimedsecurityboundary.",
            "Noeval,ASTallowlist,variablevalidation andresourcechecks useful.",
            "Onlyper-exponent1000cap; left-associated repeatedpowersgrowwithoutresultbound withinlength/nodecaps, underminingclaimedDoSprevention. Variables returnedwithouttype/rangecheck despite recommendedcontrols.",
        ),
        "task133-late-sufficiency_notes-r0": (
            ("fail", "pass", "fail"),
            "Recommendsallow_variablesfalse astrustable purearithmeticpolicy thoughnativeflagignored; mathresult5itselfcorrect.",
            "Independentallowlist andresource/error recommendationsusable.",
            "MAX_ABS_VALUE appliedonlybinaryresults; standalone1e101 andunary-1e101 bypass declaredmagnitudeceiling. Decimalstr usesalreadyroundedASTfloat.Production-ready claimunsupported.",
        ),
    },
}


def main():
    count = 0
    for co, cases in CASES.items():
        for cell, (statuses, validation, guidance, implementation) in cases.items():
            p = P / co / (cell + ".json")
            d = json.loads(p.read_text())
            props = dict(
                zip(["validation", "guidance", "implementation_consistency"], statuses, strict=True)
            )
            syntax = []
            for i, code in enumerate(
                re.findall(r"```python\s*\n(.*?)(?:```|\Z)", d["answer"] or "", re.S), 1
            ):
                try:
                    ast.parse(code)
                    status = "parses_as_AST"
                except SyntaxError as exc:
                    status = f"SyntaxErrorline{exc.lineno}: {exc.msg};snippetcontextmaymatter"
                syntax.append({"block": i, "status": status, "executed": False})
            r = {
                "cell_id": cell,
                "cohort": d["cohort"],
                "task_id": 133,
                "input_sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                "trace_sha256": d["trace_sha256"],
                "properties": props,
                "core_pass": all(v == "pass" for v in props.values()),
                "evidence": {
                    "validation": validation,
                    "guidance": guidance,
                    "implementation_consistency": implementation,
                },
                "static_syntax": syntax,
                "source_limits": [
                    "Sympyofficialparsingdocumentation1.14.0 saysparse_expruseseval;evaluate=False suppressesautomatic simplification,notexecution.",
                    "PythonAST discards redundantparentheses and parsesdecimalfloats before evaluator.",
                    "No generatedcode or hostilepayload executed.",
                ],
                "review_phase": "supplemental_posthoc_scores_exposed",
                "review_source": "scripts/review_registry_math.py",
                "limitations": [
                    "Samecoordinator;originalscores exposed,notindependentvalidation.",
                    "Securityexamples criticizedonlywhen recommended,notwhen explicitlylabelledunsafe.",
                    "Static evidence isnotruntimeverification; unknown remainsnotpass.",
                ],
            }
            (p.parent / "reviews" / p.name).write_text(
                json.dumps(r, ensure_ascii=False, indent=2) + "\n"
            )
            count += 1
    print(count, "remaining registry/SP mathematicalproductreviews")


if __name__ == "__main__":
    main()

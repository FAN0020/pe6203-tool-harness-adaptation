"""Static evidence only. Parse generated examples; never execute their Python code."""

import ast
import json
import re
from pathlib import Path

from raw_cell_verifier import archive_files

HERE = Path(__file__).resolve().parent


def main():
    files, manifest = archive_files(HERE)
    prefix = manifest["prefix"] + "/"
    sample_classes = [type(n).__name__ for n in ast.walk(ast.parse("1+1", mode="eval"))]
    assert sample_classes == ["Expression", "BinOp", "Constant", "Add", "Constant"]
    checks = []
    for cell_id in ("cell-003", "cell-004"):
        member = prefix + f"cells/{cell_id}/run/raw_trace.json"
        trace = json.loads(files[member])
        blocks = re.findall(r"```python\s*\n(.*?)```", trace["answer"], re.S)
        trees = [ast.parse(block) for block in blocks]
        if cell_id == "cell-003":
            assignment = next(
                n for tree in trees for n in ast.walk(tree)
                if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "_ALLOWED_NODES" for t in n.targets)
            )
            allowed = [x.attr for x in assignment.value.elts]
            assert allowed == ["Expression", "BinOp", "UnaryOp", "Call", "Name", "Load", "Constant"]
            function = next(n for tree in trees for n in ast.walk(tree)
                            if isinstance(n, ast.FunctionDef) and n.name == "compile_safe")
            traversal = "ast.iter_child_nodes"
        else:
            function = next(n for tree in trees for n in ast.walk(tree)
                            if isinstance(n, ast.FunctionDef) and n.name == "_check")
            allowed = [n.args[1].attr for n in ast.walk(function)
                       if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                       and n.func.id == "isinstance" and len(n.args) == 2
                       and isinstance(n.args[0], ast.Name) and n.args[0].id == "node"
                       and isinstance(n.args[1], ast.Attribute)
                       and isinstance(n.args[1].value, ast.Name) and n.args[1].value.id == "ast"]
            assert set(allowed) == {"Expression", "BinOp", "UnaryOp", "Constant"}
            traversal = "ast.walk"
        source = ast.unparse(function)
        assert traversal in source and "raise UnsafeExpression" in source and "Add" not in allowed
        checks.append({
            "cell_id": cell_id, "trajectory_member": member,
            "allowed_node_types": allowed, "function_source": source,
            "sample": "1+1", "sample_ast_types": sample_classes,
            "unsupported_reachable_operator_node": "Add",
            "conclusion": "Recorded validator rejects the Add node reached by its traversal; the supplied arithmetic example does not work as advertised.",
            "evidence_type": "static control-flow inspection plus standard-library AST characterization; no generated code executed",
        })
    print(json.dumps({"checks": checks, "new_model_calls": 0,
                      "generated_code_executed": False,
                      "limit": "Narrow functional defect proof; not a complete security audit."}, indent=2))


if __name__ == "__main__":
    main()

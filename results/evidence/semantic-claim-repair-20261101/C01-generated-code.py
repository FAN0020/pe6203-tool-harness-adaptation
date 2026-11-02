import ast, math

ALLOWED_FUNCS = {"sin": math.sin, "cos": math.cos, "sqrt": math.sqrt,
                 "log": math.log, "abs": abs, "exp": math.exp}
ALLOWED_CONSTS = {"pi": math.pi, "e": math.e}
ALLOWED_NODES = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
                 ast.Call, ast.Name, ast.Load,
                 ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub, ast.UAdd)

MAX_LEN, MAX_DEPTH, MAX_MAGNITUDE = 200, 20, 1e12

def _depth(node, d=0):
    return max([d] + [_depth(c, d + 1) for c in ast.iter_child_nodes(node)])

def safe_eval(expr: str) -> float:
    if not isinstance(expr, str) or len(expr) > MAX_LEN:
        raise ValueError("expression too long")

    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        raise ValueError("invalid syntax")

    if _depth(tree) > MAX_DEPTH:
        raise ValueError("expression too complex")

    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_NODES):
            raise ValueError("disallowed construct")          # blocks Attribute, Subscript, Lambda, etc.
        if isinstance(node, ast.Name):
            if node.id not in (ALLOWED_FUNCS | ALLOWED_CONSTS):  # blocks eval, __import__, open...
                raise ValueError("disallowed name")
        if isinstance(node, ast.Call) and not (
            isinstance(node.func, ast.Name) and node.func.id in ALLOWED_FUNCS
        ):
            raise ValueError("disallowed call")

    # Evaluate with NO builtins and ONLY allowlisted names in scope
    result = eval(compile(tree, "<expr>", "eval"), {"__builtins__": {}}, {**ALLOWED_CONSTS, **ALLOWED_FUNCS})

    if not isinstance(result, (int, float)) or not math.isfinite(result):
        raise ValueError("non-finite or non-numeric result")
    if abs(result) > MAX_MAGNITUDE:
        raise ValueError("result out of range")
    return result


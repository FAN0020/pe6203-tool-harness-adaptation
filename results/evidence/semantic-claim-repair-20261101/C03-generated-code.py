import ast
import math
import operator as op

# ---- Guardrails (DoS bounds) ----
MAX_EXPR_LEN   = 500     # characters
MAX_AST_NODES  = 200     # structural complexity
MAX_POW_EXP    = 1000    # prevents 9**9**9 / 2**10**9 blow-ups
MAX_RESULT_BITS = 1 << 20  # optional: cap integer result size (~1M bits)

BIN_OPS = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
           ast.Div: op.truediv, ast.FloorDiv: op.floordiv,
           ast.Mod: op.mod, ast.Pow: op.pow}
UNARY_OPS = {ast.UAdd: op.pos, ast.USub: op.neg}
ALLOWED_FUNCS = {"abs": abs, "min": min, "max": max, "round": round,
                 "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos,
                 "log": math.log}

class UnsafeExpressionError(ValueError):
    """Raised on any validation failure (message is safe to log/show)."""

def validate_expression(expr: str) -> ast.Expression:
    if not isinstance(expr, str):
        raise UnsafeExpressionError("Expression must be a string.")
    if len(expr) > MAX_EXPR_LEN:
        raise UnsafeExpressionError("Expression too long.")
    try:
        tree = ast.parse(expr, mode="eval")        # no statements/suites
    except SyntaxError:
        raise UnsafeExpressionError("Invalid syntax.") from None
    if sum(1 for _ in ast.walk(tree)) > MAX_AST_NODES:
        raise UnsafeExpressionError("Expression too complex.")
    _check(tree)
    return tree

def _check(node):
    if isinstance(node, ast.Expression):
        _check(node.body)
    elif isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise UnsafeExpressionError("Only numeric constants allowed.")
    elif isinstance(node, ast.BinOp):
        if type(node.op) not in BIN_OPS:
            raise UnsafeExpressionError("Operator not allowed.")
        if isinstance(node.op, ast.Pow):
            _check_pow(node)
        _check(node.left); _check(node.right)
    elif isinstance(node, ast.UnaryOp):
        if type(node.op) not in UNARY_OPS:
            raise UnsafeExpressionError("Unary operator not allowed.")
        _check(node.operand)
    elif isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in ALLOWED_FUNCS:
            raise UnsafeExpressionError("Function not allowed.")
        if node.keywords:
            raise UnsafeExpressionError("Keyword arguments not allowed.")
        for a in node.args:
            _check(a)
    else:
        # Rejects Name, Attribute, Subscript, Lambda, comprehensions, etc.
        raise UnsafeExpressionError(f"Disallowed construct: {type(node).__name__}.")

def _check_pow(node):
    e = node.right
    if not isinstance(e, ast.Constant) or not isinstance(e.value, int):
        raise UnsafeExpressionError("Exponent must be an integer literal.")
    if not (0 <= e.value <= MAX_POW_EXP):
        raise UnsafeExpressionError("Exponent out of safe range.")

def _eval(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp):
        return BIN_OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp):
        return UNARY_OPS[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.Call):
        return ALLOWED_FUNCS[node.func.id](*(_eval(a) for a in node.args))
    raise UnsafeExpressionError("Unsafe node reached evaluator.")

def safe_evaluate(expr: str):
    tree = validate_expression(expr)   # validate first...
    return _eval(tree.body)            # ...then evaluate only allow-listed nodes


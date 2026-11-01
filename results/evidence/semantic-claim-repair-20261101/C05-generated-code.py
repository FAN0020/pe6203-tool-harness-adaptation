from __future__ import annotations
import ast, logging, math
from dataclasses import dataclass

log = logging.getLogger("math.eval")

MAX_LEN, MAX_NODES, MAX_DEPTH, MAX_POW_EXP = 256, 64, 12, 32

ALLOWED_FUNCS = {"abs": abs, "min": min, "max": max, "round": round, "sqrt": math.sqrt}
ALLOWED_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)
ALLOWED_UNARY = (ast.UAdd, ast.USub)


class Rejected(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class Result:
    ok: bool
    value: float | None = None
    error: str | None = None          # error is explicit — never None-on-success


def _walk(node, depth: int, budget: list[int], names: dict[str, float]) -> None:
    budget[0] += 1
    if budget[0] > MAX_NODES:
        raise Rejected("E_TOO_COMPLEX")
    if depth > MAX_DEPTH:
        raise Rejected("E_TOO_DEEP")

    match node:
        case ast.Expression():
            _walk(node.body, depth + 1, budget, names)

        case ast.Constant():
            # type() is exact: rejects bool (an int subclass), str, bytes, None, complex
            if type(node.value) not in (int, float):
                raise Rejected("E_BAD_LITERAL")

        case ast.Name():
            if node.id not in names:
                raise Rejected("E_UNKNOWN_NAME")

        case ast.BinOp():
            if not isinstance(node.op, ALLOWED_BINOPS):
                raise Rejected("E_BAD_OPERATOR")
            if isinstance(node.op, ast.Pow):
                exp = node.right
                if not (isinstance(exp, ast.Constant)
                        and type(exp.value) is int
                        and abs(exp.value) <= MAX_POW_EXP):
                    raise Rejected("E_BAD_EXPONENT")   # blocks 10**10**10
            _walk(node.left, depth + 1, budget, names)
            _walk(node.right, depth + 1, budget, names)

        case ast.UnaryOp():
            if not isinstance(node.op, ALLOWED_UNARY):
                raise Rejected("E_BAD_OPERATOR")
            _walk(node.operand, depth + 1, budget, names)

        case ast.Call():
            if not isinstance(node.func, ast.Name) or node.func.id not in ALLOWED_FUNCS:
                raise Rejected("E_FORBIDDEN_CALL")
            if node.keywords or any(isinstance(a, ast.Starred) for a in node.args):
                raise Rejected("E_FORBIDDEN_CALL")
            for arg in node.args:
                _walk(arg, depth + 1, budget, names)

        case _:
            # Attribute, Subscript, Lambda, comprehension, JoinedStr, Dict/List/Set...
            raise Rejected("E_FORBIDDEN_SYNTAX")


def safe_eval(expression: str, names: dict[str, float] | None = None,
              request_id: str = "-") -> Result:
    names = {k: v for k, v in (names or {}).items() if isinstance(v, (int, float))}

    if not isinstance(expression, str) or len(expression) > MAX_LEN:
        _reject("E_TOO_LONG", request_id)
        return Result(False, error="E_TOO_LONG")

    try:
        tree = ast.parse(expression, mode="eval")     # mode="eval" ⇒ statements impossible
        _walk(tree, 0, [0], names)
    except Rejected as r:
        _reject(r.code, request_id)
        return Result(False, error=r.code)
    except SyntaxError:
        _reject("E_SYNTAX", request_id)
        return Result(False, error="E_SYNTAX")

    # AST allowlist is the real control; empty builtins is defense-in-depth only.
    try:
        value = eval(compile(tree, "<expr>", "eval"), {"__builtins__": {}}, dict(names))
    except ZeroDivisionError:
        _reject("E_DIV_ZERO", request_id); return Result(False, error="E_DIV_ZERO")
    except (OverflowError, ValueError):
        _reject("E_DOMAIN", request_id);    return Result(False, error="E_DOMAIN")
    except Exception:
        _reject("E_INTERNAL", request_id);  return Result(False, error="E_INTERNAL")

    if type(value) not in (int, float) or (isinstance(value, float) and not math.isfinite(value)):
        _reject("E_BAD_RESULT_TYPE", request_id)
        return Result(False, error="E_BAD_RESULT_TYPE")
    return Result(True, value=float(value))


def _reject(code: str, request_id: str) -> None:
    log.warning("expr_rejected", extra={"code": code, "request_id": request_id})


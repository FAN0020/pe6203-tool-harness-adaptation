"""Reproduce narrow product facts without executing any generated code."""
import ast
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    rows = []
    for path in sorted((HERE / "blind-inputs").glob("*.json")):
        packet = json.loads(path.read_text())
        row = {"review_id": packet["review_id"], "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        blocks = re.findall(r"```python\n(.*?)(?:```|\Z)", packet.get("answer") or "", re.S)
        if blocks:
            row["static_python"] = []
            for index, code in enumerate(blocks):
                item = {"block": index, "generated_code_executed": False}
                try:
                    tree = ast.parse(code)
                    item["parse"] = "valid"
                    item["except_types"] = [ast.unparse(n.type) if n.type else "bare" for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler)]
                    item["functions"] = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
                except SyntaxError as exc:
                    item.update(parse="invalid", line=exc.lineno, error=exc.msg)
                row["static_python"].append(item)
        charts = [c for c in packet["calls"] if c["tool"].startswith("generate_")]
        if charts:
            row["charts"] = []
            for call in charts:
                spec = call["result"].get("meta", {}).get("spec", {})
                item = {"type": spec.get("type"), "error": call["result"].get("isError", False)}
                if spec.get("type") == "area":
                    item["sum_millions"] = str(sum(Decimal(str(x["value"])) for x in spec["data"]))
                    item["ordered_values"] = [x["value"] for x in spec["data"]]
                    assert item["ordered_values"] == [1.2, 1.1, 1.4, 1.6, 1.8, 2.1, 2.3, 2.2, 2.5, 2.7, 3.0, 3.5]
                row["charts"].append(item)
        if blocks or charts:
            rows.append(row)
    print(json.dumps({"scope": "Static syntax and supplied chart values only; property judgments remain human/coordinator reviews.", "generated_code_executed": False, "rows": rows}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

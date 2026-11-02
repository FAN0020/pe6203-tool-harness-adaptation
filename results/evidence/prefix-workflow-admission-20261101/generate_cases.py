"""Deterministic synthetic admission data; never a benchmark task replacement."""
import hashlib
import json
import random
from pathlib import Path


def generate():
    rng = random.Random(84620)
    result = {}
    for name, n in (("train", 4), ("heldout", 5)):
        values = [rng.randrange(100000, 999999) for _ in range(n)]
        bodies = [
            f"# {name.title()} Document\n\nCANARY_{name.upper()}_0={values[0]}\n\nIndependent synthetic document.",
            f"# Inventory\n\n- First item\n- Second item\n\nCANARY_{name.upper()}_1={values[1]}",
            f"# Measurements\n\n| Item | State |\n| :--- | :--- |\n| Alpha | ready |\n| Beta | stable |\n\nCANARY_{name.upper()}_2={values[2]}",
            f"# Local sample\n\n```js\nconst message = 'preserve this';\n```\n\nCANARY_{name.upper()}_3={values[3]}",
        ]
        if n == 5:
            bodies.append(f"# Unicode transfer\n\n中文摘要 · café · Δ\n\n**Content remains intact.**\n\nCANARY_HELDOUT_4={values[4]}")
        result[name] = [{"index": i, "body": body, "layout": "cover" if i == 0 else "default",
                         "sha256": hashlib.sha256(body.encode()).hexdigest()}
                        for i, body in enumerate(bodies)]
    return result


if __name__ == "__main__":
    dest = Path(__file__).with_name("cases.json")
    assert not dest.exists(), "Never overwrite frozen inputs"
    dest.write_text(json.dumps(generate(), ensure_ascii=False, indent=2) + "\n")

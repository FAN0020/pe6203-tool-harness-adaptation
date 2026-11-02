"""Run the frozen task-free omission experiment once; never call a model."""

import asyncio
import hashlib
import json
import tempfile
from pathlib import Path

from pe6203.transport import sessions

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def save(name, data):
    (HERE / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


async def main():
    if (HERE / "native-results.json").exists():
        raise ValueError("Already attempted; preserve outcomes, no reruns")
    for row in json.loads((HERE / "source-manifest.json").read_text()):
        assert hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest() == row["sha256"]
    plan = json.loads((HERE / "native-plan.json").read_text())
    audit = {"status": "started", "calls": [], "model_calls": 0, "usd": "0"}
    save("native-results.json", audit)
    try:
        for stage in ("middle", "late"):
            with tempfile.TemporaryDirectory(prefix="pe6203-optional-probe-") as tmp:
                async with sessions(
                    ROOT, stage, ["math-mcp"], Path(tmp), HERE / "native.stderr.log"
                ) as clients:
                    for case in plan["cases"]:
                        if case["stage"] != stage:
                            continue
                        result = await clients["math-mcp"].call_tool(case["tool"], case["args"])
                        audit["calls"].append(
                            {**case, "result": result.model_dump(mode="json", exclude_none=True)}
                        )
                        save("native-results.json", audit)
        groups = {}
        checks = []
        for row in audit["calls"]:
            result = row["result"]
            message = "\n".join(c.get("text", "") for c in result.get("content", []))
            if row.get("expected_error"):
                checks.append(bool(result.get("isError")))
                continue
            checks.append(not result.get("isError", False))
            checks.append(
                ("Expression is syntactically valid." in message)
                if row["expected_valid"]
                else message.startswith("Syntax errors:")
            )
            groups.setdefault(row["group"], []).append(result)
        checks += [len(v) == 3 and v[0] == v[1] == v[2] for v in groups.values()]
        passed = len(audit["calls"]) == plan["calls"] and len(groups) == 6 and all(checks)
        audit.update(status="passed" if passed else "rejected", checks=checks, groups=len(groups))
    except Exception as exc:
        audit.update(status="failed", failure=repr(exc))
        raise
    finally:
        save("native-results.json", audit)
    print(json.dumps({"status": audit["status"], "calls": len(audit["calls"]), "model_calls": 0}))
    if audit["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())

"""Confirm original environment-check tool sees the pinned local renderer."""
import asyncio
import json
from pathlib import Path

from pe6203.experiment import configure_runtime
from pe6203.transport import sessions

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "path-readiness"


async def main():
    configure_runtime(ROOT)
    OUT.mkdir(exist_ok=False)
    rows = []
    for stage in ("early", "middle", "late"):
        workspace = OUT / stage / "workspace"
        workspace.mkdir(parents=True)
        async with sessions(ROOT, stage, ["slidev-mcp"], workspace,
                            OUT / f"{stage}-stderr.log") as clients:
            result = (await clients["slidev-mcp"].call_tool("check_environment", {})).model_dump(
                mode="json", by_alias=True, exclude_none=True)
        row = {"stage": stage, "tool": "check_environment", "arguments": {}, "result": result}
        (OUT / f"{stage}.json").write_text(json.dumps(row, indent=2) + "\n")
        payload = json.loads(result["content"][0]["text"])
        assert payload["success"] is True and "53.0.0" in payload["output"]
        assert not (workspace / ".npm-global").exists()
        assert not (workspace / ".npm-cache").exists()
        rows.append({"stage": stage, "success": True, "cli_output": payload["output"]})
    (OUT / "verification.json").write_text(json.dumps(rows, indent=2) + "\n")
    print(json.dumps(rows))


if __name__ == "__main__":
    asyncio.run(main())

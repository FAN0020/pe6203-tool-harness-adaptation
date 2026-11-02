"""Snapshot archived MCP catalogs and public read-only tool availability; no model calls."""

import asyncio
import hashlib
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from pe6203.benchmark import source
from pe6203.experiment import configure_runtime
from pe6203.transport import sessions, snapshot

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[2]
SERVERS = ["swiftipedia-mcp-server", "wikipedia-mcp"]


async def main():
    configure_runtime(ROOT)
    lock, _ = source(ROOT)
    observations = []
    for stage in ("early", "middle", "late"):
        target = FOLDER / f"{stage}-catalog.json"
        if target.exists():
            raise ValueError("Never overwrite an existing snapshot")
        with tempfile.TemporaryDirectory(prefix="pe6203-catalog-") as workspace:
            async with sessions(
                ROOT, stage, SERVERS, workspace, FOLDER / f"{stage}.stderr.log", 20
            ) as clients:
                data = await snapshot(clients, stage, lock["commit"])
                target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
                print(stage, "catalog", len(data["tools"]), flush=True)
                # Metadata-independent generic queries, not task430's answer or judge.
                calls = [
                    ("wikipedia-mcp", "search", {"query": "computer programming"}),
                    ("swiftipedia-mcp-server", "browse_module", {"module": "swiftui", "limit": 2}),
                ]
                for server, tool, args in calls:
                    row = {
                        "stage": stage,
                        "server": server,
                        "tool": tool,
                        "arguments": args,
                        "time": datetime.now(UTC).isoformat(),
                    }
                    try:
                        result = await asyncio.wait_for(clients[server].call_tool(tool, args), 20)
                        row["result"] = result.model_dump(mode="json", exclude_none=True)
                    except Exception as exc:
                        row["exception"] = f"{type(exc).__name__}: {exc}"
                    observations.append(row)
                    (FOLDER / "public-read-probes.json").write_text(
                        json.dumps(
                            {"new_model_calls": 0, "observations": observations},
                            ensure_ascii=False,
                            indent=2,
                        )
                        + "\n"
                    )
                    print(
                        stage,
                        server,
                        tool,
                        "returned" if "result" in row else row["exception"],
                        flush=True,
                    )
    manifest = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in FOLDER.glob("*-catalog.json")
    }
    (FOLDER / "catalog-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    asyncio.run(main())

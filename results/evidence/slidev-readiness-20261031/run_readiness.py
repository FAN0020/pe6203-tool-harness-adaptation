"""Read only published paper fixtures through the original released MCP servers."""
import asyncio
import hashlib
import json
import os
import shutil
from contextlib import AsyncExitStack
from datetime import timedelta
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[2]
PLAN = ROOT / "experiments/slidev-readiness-v1.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


async def main():
    plan = json.loads(PLAN.read_text())
    assert not (FOLDER / "results.json").exists()
    source = ROOT / plan["fixture_source"]
    dest = ROOT / plan["fixture_destination"]
    dest.mkdir(parents=True, exist_ok=False)
    for path in sorted(source.glob("*.pdf")):
        shutil.copyfile(path, dest / path.name)
    assert len(list(dest.glob("*.pdf"))) == 3
    manifest = [{"path": "pdf/embodied_ai_papers/" + p.name, "sha256": sha(p)} for p in sorted(dest.glob("*.pdf"))]
    save(FOLDER / "fixture-manifest.json", manifest)
    observations = []
    for stage, release in (("early", "original"), ("middle", "iter3"), ("late", "iter5")):
        work = FOLDER / "workspaces" / stage
        shutil.copytree(dest.parent.parent, work)
        (work / ".home").mkdir()
        with (FOLDER / f"{stage}-stderr.log").open("w") as stderr:
            async with AsyncExitStack() as stack:
                for server, entry in plan["servers"].items():
                    path = ROOT / ".cache/mcpevol" / release / "node_modules" / server / entry
                    params = StdioServerParameters(command=str(ROOT / ".cache/node-runtime/node_modules/node/bin/node"),
                        args=[str(path)], cwd=str(work), env={"PATH": os.environ.get("PATH", ""),
                        "HOME": str(work / ".home"), "TMPDIR": str(work)})
                    read, write = await stack.enter_async_context(stdio_client(params, errlog=stderr))
                    client = await stack.enter_async_context(ClientSession(read, write, read_timeout_seconds=timedelta(seconds=30)))
                    await client.initialize()
                    catalog = await client.list_tools()
                    server_name = "pdf" if "pdf-reader" in server else "slidev"
                    save(FOLDER / f"{stage}-{server_name}-catalog.json", catalog.model_dump(mode="json", by_alias=True, exclude_none=True))
                    if server_name == "pdf":
                        args = {"sources": [{"path": f["path"], "pages": "1-3"} for f in manifest],
                                "include_metadata": True, "include_page_count": True}
                        result = await client.call_tool("read_pdf", args)
                        row = {"stage": stage, "tool": "read_pdf", "arguments": args,
                               "result": result.model_dump(mode="json", by_alias=True, exclude_none=True)}
                        save(FOLDER / f"{stage}-read_pdf.json", row)
                        observations.append(row)
    save(FOLDER / "results.json", observations)
    print(json.dumps({"tool_calls": len(observations), "isError": [r['result'].get('isError') for r in observations], "model_calls": 0}))


if __name__ == "__main__":
    asyncio.run(main())

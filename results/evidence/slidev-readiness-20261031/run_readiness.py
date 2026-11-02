"""Read only published paper fixtures through the original released MCP servers."""
import asyncio
import functools
import hashlib
import http.server
import json
import os
import shutil
import sys
import threading
from contextlib import AsyncExitStack
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[2]
PLAN = ROOT / "experiments/slidev-readiness-v1.json"
ATTEMPT = (FOLDER / "loopback-url-attempt" if "--loopback-url" in sys.argv else
           FOLDER / "native-runtime-attempt" if "--native-runtime" in sys.argv else FOLDER)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


async def main():
    plan = json.loads(PLAN.read_text())
    assert not (ATTEMPT / "results.json").exists()
    ATTEMPT.mkdir(exist_ok=True)
    source = ROOT / plan["fixture_source"]
    dest = ROOT / plan["fixture_destination"]
    dest.mkdir(parents=True, exist_ok=True)
    for path in sorted(source.glob("*.pdf")):
        if (dest / path.name).exists():
            assert sha(path) == sha(dest / path.name)
        else:
            shutil.copyfile(path, dest / path.name)
    assert len(list(dest.glob("*.pdf"))) == 3
    manifest = [{"path": "pdf/embodied_ai_papers/" + p.name, "sha256": sha(p)} for p in sorted(dest.glob("*.pdf"))]
    save(ATTEMPT / "fixture-manifest.json", manifest)
    native = json.loads((FOLDER / "native-runtime.json").read_text()) if ATTEMPT != FOLDER else None
    if native:
        for name, digest in native["files"].items():
            assert sha(ROOT / name) == digest
    fixture_http = None
    if "--loopback-url" in sys.argv:
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(dest.parent.parent))
        fixture_http = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=fixture_http.serve_forever, daemon=True).start()
        save(ATTEMPT / "fixture-http.json", {"origin": f"http://127.0.0.1:{fixture_http.server_port}",
             "root": str(dest.parent.parent), "scope": "Read-only loopback copies of same published PDF bytes; URL branch avoids local Buffer incompatibility. No public hosting."})
    observations = []
    for stage, release in (("early", "original"), ("middle", "iter3"), ("late", "iter5")):
        work = ATTEMPT / "workspaces" / stage
        shutil.copytree(dest.parent.parent, work)
        (work / ".home").mkdir()
        with (ATTEMPT / f"{stage}-stderr.log").open("w") as stderr:
            async with AsyncExitStack() as stack:
                for server, entry in plan["servers"].items():
                    path = ROOT / ".cache/mcpevol" / release / "node_modules" / server / entry
                    env = {"PATH": os.environ.get("PATH", ""), "HOME": str(work / ".home"), "TMPDIR": str(work)}
                    if native:
                        env["NAPI_RS_NATIVE_LIBRARY_PATH"] = str(ROOT / native["native_library"])
                    params = StdioServerParameters(command=str(ROOT / ".cache/node-runtime/node_modules/node/bin/node"),
                        args=[str(path)], cwd=str(work), env=env)
                    read, write = await stack.enter_async_context(stdio_client(params, errlog=stderr))
                    client = await stack.enter_async_context(ClientSession(read, write, read_timeout_seconds=timedelta(seconds=30)))
                    await client.initialize()
                    catalog = await client.list_tools()
                    server_name = "pdf" if "pdf-reader" in server else "slidev"
                    save(ATTEMPT / f"{stage}-{server_name}-catalog.json", catalog.model_dump(mode="json", by_alias=True, exclude_none=True))
                    if server_name == "pdf":
                        args = {"sources": [{"path": f["path"], "pages": "1-3"} for f in manifest],
                                "include_metadata": True, "include_page_count": True}
                        if fixture_http:
                            args["sources"] = [{"url": f"http://127.0.0.1:{fixture_http.server_port}/" + quote(f["path"]),
                                                "pages": "1-3"} for f in manifest]
                        result = await client.call_tool("read_pdf", args)
                        row = {"stage": stage, "tool": "read_pdf", "arguments": args,
                               "result": result.model_dump(mode="json", by_alias=True, exclude_none=True)}
                        save(ATTEMPT / f"{stage}-read_pdf.json", row)
                        observations.append(row)
    save(ATTEMPT / "results.json", observations)
    if fixture_http:
        fixture_http.shutdown()
        fixture_http.server_close()
    print(json.dumps({"tool_calls": len(observations), "isError": [r['result'].get('isError') for r in observations], "model_calls": 0}))


if __name__ == "__main__":
    asyncio.run(main())

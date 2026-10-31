"""Run only the frozen synthetic artifact probes; no model or network tools."""
import asyncio
import hashlib
import json
import os
import time
from contextlib import AsyncExitStack
from datetime import timedelta
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[2]
PLAN = ROOT / "experiments/slidev-artifact-probes-v1.json"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


async def main():
    plan = json.loads(PLAN.read_text())
    assert not (FOLDER / "observations.json").exists(), "Existing run must not be overwritten."
    source_files = {}
    for stage in ("iter3", "iter5"):
        for name in ("index.js", "slidev-manager.js", "slide-generator.js", "slide-templates.js", "utils.js"):
            p = ROOT / ".cache/mcpevol" / stage / "node_modules/slidev-mcp/dist" / name
            source_files[str(p.relative_to(ROOT))] = sha(p.read_bytes())
    save(FOLDER / "preexecution.json", {"plan_sha256": sha(PLAN.read_bytes()), "source_files": source_files,
                                       "model_calls": 0, "network_tool_calls": 0})
    rows = []
    for version, release in (("middle", "iter3"), ("late", "iter5")):
        work = FOLDER / "workspaces" / version
        work.mkdir(parents=True, exist_ok=False)
        home = work / ".home"
        home.mkdir()
        entry = ROOT / ".cache/mcpevol" / release / "node_modules/slidev-mcp/dist/index.js"
        params = StdioServerParameters(command=str(ROOT / ".cache/node-runtime/node_modules/node/bin/node"),
            args=[str(entry)], cwd=str(work), env={"PATH": os.environ.get("PATH", ""),
            "HOME": str(home), "TMPDIR": str(work)})
        with (FOLDER / f"{version}-stderr.log").open("w") as errlog:
            async with AsyncExitStack() as stack:
                read, write = await stack.enter_async_context(stdio_client(params, errlog=errlog))
                session = await stack.enter_async_context(ClientSession(read, write, read_timeout_seconds=timedelta(seconds=30)))
                await session.initialize()
                catalog = await session.list_tools()
                save(FOLDER / f"{version}-catalog.json", catalog.model_dump(mode="json", by_alias=True, exclude_none=True))
                for case in plan["cases"]:
                    dest = FOLDER / version / case
                    dest.mkdir(parents=True, exist_ok=False)
                    deck = work / case
                    content = plan["synthetic_content"]
                    bulk = {"topic": content["topic"], "slideCount": 6, "style": "minimal",
                            "includeAnimations": False, "includeImages": False,
                            "customInstructions": "Include exactly this requested factual text: " + content["requested_content_canary"],
                            "preserveCover": case == "preserve_cover"}
                    if version == "late":
                        bulk["clearExistingSlides"] = True
                    calls = [
                        ("create_slidev", {"path": str(deck), "title": "Synthetic cover", "author": "Contract probe"}),
                        ("add_page", {"content": content["old_page_canary"], "layout": "default"}),
                        ("apply_theme", {"themeName": "dark"}),
                        ("create_bulk_slides", bulk), ("get_all_slides", {}),
                        ("create_bulk_slides", bulk), ("get_all_slides", {}),
                        ("set_page", {"index": 1, "content": content["repair_canary"], "layout": "default"}),
                        ("get_all_slides", {}),
                    ]
                    for index, (name, args) in enumerate(calls, 1):
                        start = time.monotonic()
                        result = await session.call_tool(name, args)
                        elapsed = time.monotonic() - start
                        result = result.model_dump(mode="json", by_alias=True, exclude_none=True)
                        artifact = deck / "slides.md"
                        saved = artifact.read_bytes() if artifact.exists() else b""
                        snapshot = dest / f"{index:02d}-slides.md"
                        snapshot.write_bytes(saved)
                        row = {"stage": version, "case": case, "index": index, "tool": name,
                               "arguments": args, "result": result, "elapsed_seconds": elapsed,
                               "artifact_sha256": sha(saved), "artifact_snapshot": str(snapshot.relative_to(FOLDER)),
                               "old_canary_present": content["old_page_canary"] in saved.decode(),
                               "requested_canary_present": content["requested_content_canary"] in saved.decode(),
                               "repair_canary_present": content["repair_canary"] in saved.decode()}
                        save(dest / f"{index:02d}-{name}.json", row)
                        rows.append(row)
    assert len(rows) == plan["planned_tool_calls"]
    save(FOLDER / "observations.json", rows)
    save(FOLDER / "manifest.json", {"plan_sha256": sha(PLAN.read_bytes()), "source_files": source_files,
         "tool_calls": len(rows), "catalog_calls": 2, "model_calls": 0, "model_usd": 0,
         "elapsed_seconds_sum": sum(r["elapsed_seconds"] for r in rows),
         "observation_sha256": sha((FOLDER / "observations.json").read_bytes())})
    print(json.dumps({"completed_tool_calls": len(rows), "model_calls": 0}))


if __name__ == "__main__":
    asyncio.run(main())

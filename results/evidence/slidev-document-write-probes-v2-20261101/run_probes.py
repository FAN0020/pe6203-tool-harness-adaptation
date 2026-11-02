"""Execute the frozen synthetic document serialization probes, without model calls."""
import asyncio
import hashlib
import json
from pathlib import Path

from pe6203.experiment import configure_runtime
from pe6203.transport import sessions

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[2]
PLAN = ROOT / "experiments/slidev-document-write-probes-v2.json"


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def main():
    assert not (FOLDER / "observations.json").exists()
    plan = json.loads(PLAN.read_text())
    configure_runtime(ROOT)
    source = {}
    for release in ("iter3", "iter5"):
        for name in ("index.js", "slidev-manager.js", "utils.js", "slide-templates.js"):
            p = ROOT / ".cache/mcpevol" / release / "node_modules/slidev-mcp/dist" / name
            source[str(p.relative_to(ROOT))] = sha(p)
    save(FOLDER / "preexecution.json", {"plan_sha256": sha(PLAN), "source": source,
                                        "model_calls": 0})
    rows = []
    for stage in plan["stages"]:
        work = FOLDER / "workspaces" / stage
        work.mkdir(parents=True, exist_ok=False)
        async with sessions(ROOT, stage, ["slidev-mcp"], work,
                            FOLDER / f"{stage}-stderr.log") as clients:
            client = clients["slidev-mcp"]
            catalog = await client.list_tools()
            save(FOLDER / f"{stage}-catalog.json", catalog.model_dump(mode="json", by_alias=True))
            for case, content in plan["cases"].items():
                deck = work / case
                dest = FOLDER / stage / case
                dest.mkdir(parents=True)
                calls = [
                    ("create_slidev", {"path": str(deck), "title": "Synthetic seed", "author": "Probe"}),
                    ("set_page", {"index": 0, "layout": "cover", "content": content}),
                    ("load_slidev", {"path": str(deck)}),
                    ("apply_theme", {"themeName": "dark"}),
                    ("get_all_slides", {}),
                    ("load_slidev", {"path": str(deck)}),
                    ("get_all_slides", {}),
                ]
                for index, (tool, args) in enumerate(calls, 1):
                    result = (await client.call_tool(tool, args)).model_dump(
                        mode="json", by_alias=True, exclude_none=True)
                    artifact = deck / "slides.md"
                    snapshot = dest / f"{index:02d}-slides.md"
                    snapshot.write_bytes(artifact.read_bytes())
                    row = {"stage": stage, "case": case, "index": index, "tool": tool,
                           "arguments": args, "result": result, "artifact_sha256": sha(artifact),
                           "snapshot": str(snapshot.relative_to(FOLDER))}
                    save(dest / f"{index:02d}-{tool}.json", row)
                    rows.append(row)
    assert len(rows) == plan["planned_tool_calls"]
    save(FOLDER / "observations.json", rows)
    print(json.dumps({"tool_calls": len(rows), "catalog_calls": 2, "model_calls": 0}))


if __name__ == "__main__":
    asyncio.run(main())

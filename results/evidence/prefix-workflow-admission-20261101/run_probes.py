"""Execute the immutable 40-call native schedule once, with no model calls."""
import asyncio
import hashlib
import json
from pathlib import Path

from checks import check_document, check_records, unpack
from pe6203.experiment import configure_runtime
from pe6203.transport import sessions

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[2]
PLAN = ROOT / "experiments/prefix-workflow-admission-v1.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


async def main():
    assert not (FOLDER / "observations.json").exists()
    frozen = json.loads((FOLDER / "preexecution.json").read_text())
    for path, expected in frozen["files"].items():
        assert sha(ROOT / path) == expected, path
    plan = json.loads(PLAN.read_text())
    cases = json.loads((FOLDER / "cases.json").read_text())
    configure_runtime(ROOT)
    rows = []
    errors = []
    for stage in plan["stages"]:
        work = FOLDER / "workspaces" / stage
        work.mkdir(parents=True, exist_ok=False)
        async with sessions(ROOT, stage, ["slidev-mcp"], work,
                            FOLDER / f"{stage}-stderr.log") as clients:
            client = clients["slidev-mcp"]
            catalog = await client.list_tools()
            save(FOLDER / f"{stage}-catalog.json", catalog.model_dump(mode="json", by_alias=True))
            for case, pages in cases.items():
                deck = work / case
                dest = FOLDER / stage / case
                dest.mkdir(parents=True, exist_ok=False)
                calls = [("create_slidev", {"path": str(deck), "title": "Synthetic seed", "author": "Probe"}, 0),
                         ("set_page", {"index": 0, "layout": "cover", "content": pages[0]["body"]}, 1)]
                for page in pages[1:]:
                    calls.append(("add_page", {"layout": page["layout"], "content": page["body"]}, page["index"] + 1))
                    if case == "heldout" and page["index"] == 1:
                        calls.append(("load_slidev", {"path": str(deck)}, 2))
                calls.extend((tool, args, len(pages)) for tool, args in [
                    ("apply_theme", {"themeName": "dark"}), ("get_all_slides", {}),
                    ("load_slidev", {"path": str(deck)}), ("get_all_slides", {})])
                dark = False
                previous = None
                for index, (tool, args, count) in enumerate(calls, 1):
                    entry_errors = []
                    try:
                        result = (await asyncio.wait_for(client.call_tool(tool, args), 30)).model_dump(
                            mode="json", by_alias=True, exclude_none=True)
                        inner = unpack(result)
                        if tool in ("set_page", "add_page") and inner.get("output") != count - 1:
                            entry_errors.append("Returned page index mismatch")
                    except Exception as exc:
                        result = {"exception_type": type(exc).__name__, "exception": str(exc)}
                        entry_errors.append("Native call unsuccessful")
                    artifact = deck / "slides.md"
                    data = artifact.read_bytes() if artifact.exists() else b""
                    snapshot = dest / f"{index:02d}-slides.md"
                    snapshot.write_bytes(data)
                    dark = dark or tool == "apply_theme"
                    entry_errors.extend(check_document(data.decode(), pages[:count], dark=dark))
                    if tool == "load_slidev" and data != previous:
                        entry_errors.append("Load mutated persisted bytes")
                    if tool == "get_all_slides":
                        entry_errors.extend(check_records(result, pages))
                    row = {"stage": stage, "case": case, "index": index, "tool": tool,
                           "arguments": args, "result": result, "artifact_sha256": sha(snapshot),
                           "snapshot": str(snapshot.relative_to(FOLDER)), "checks": entry_errors}
                    save(dest / f"{index:02d}-{tool}.json", row)
                    rows.append(row)
                    errors.extend({"stage": stage, "case": case, "index": index, "error": error} for error in entry_errors)
                    previous = data
    assert len(rows) == plan["schedule"]["native_calls"]
    save(FOLDER / "observations.json", rows)
    save(FOLDER / "native-decision.json", {"native_pass": not errors, "errors": errors, "tool_calls": len(rows),
                                           "catalog_calls": 2, "model_calls": 0, "render": "pending"})
    print(json.dumps({"tool_calls": len(rows), "native_pass": not errors, "errors": errors, "model_calls": 0}))


if __name__ == "__main__":
    asyncio.run(main())

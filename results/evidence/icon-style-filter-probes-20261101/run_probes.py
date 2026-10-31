"""Frozen native icon search/style probes; never retry or replace a failed case."""
import asyncio
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from pe6203.experiment import configure_runtime
from pe6203.transport import sessions

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[2]
PLAN = ROOT / "experiments/icon-style-filter-probes-v1.json"


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decoded(row):
    if "exception" in row or row.get("result", {}).get("isError"):
        raise ValueError("Native call failed")
    return json.loads("\n".join(c.get("text", "")
                                for c in row["result"].get("content", [])))


async def main():
    assert not (FOLDER / "preexecution.json").exists(), "No repeat execution"
    plan = json.loads(PLAN.read_text())
    for item in plan["source"]:
        assert sha(ROOT / item["path"]) == item["sha256"]
    configure_runtime(ROOT)
    save(FOLDER / "preexecution.json", {
        "plan_sha256": sha(PLAN), "collector_sha256": sha(Path(__file__)),
        "freeze_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "started_utc": datetime.now(UTC).isoformat(), "model_calls": 0,
    })
    rows, catalogs = [], 0
    terminal, stopping = "completed_requires_review", None
    for stage in plan["stages"]:
        work = FOLDER / "workspaces" / stage
        work.mkdir(parents=True, exist_ok=False)
        try:
            async with sessions(ROOT, stage, [plan["server"]], work,
                                FOLDER / f"{stage}-stderr.log", timeout=45) as clients:
                client = clients[plan["server"]]
                catalog = (await client.list_tools()).model_dump(mode="json", by_alias=True)
                save(FOLDER / f"{stage}-catalog.json", catalog)
                catalogs += 1
                names = {tool["name"] for tool in catalog["tools"]}
                icon = None
                for index, kind in enumerate(plan["schedule"][stage], 1):
                    if kind == "glyph_by_style":
                        assert icon
                        tool = "get_icon_glyph_by_style"
                        args = {"icon_name": icon, "style": plan["style"]}
                    else:
                        tool, args = "search_icons", {"query": plan["synthetic_query"]}
                        if kind == "search_style":
                            args["style"] = plan["style"]
                    assert tool in names
                    row = {"stage": stage, "index": index, "kind": kind, "tool": tool,
                           "arguments": args, "started_utc": datetime.now(UTC).isoformat()}
                    try:
                        result = await asyncio.wait_for(client.call_tool(tool, args), 30)
                        row["result"] = result.model_dump(
                            mode="json", by_alias=True, exclude_none=True)
                    except Exception as error:
                        row["exception"] = {"type": type(error).__name__, "message": str(error)}
                    row["ended_utc"] = datetime.now(UTC).isoformat()
                    save(FOLDER / f"{stage}-{index:02d}.json", row)
                    rows.append(row)
                    save(FOLDER / "observations.json", rows)
                    print(json.dumps({"stage": stage, "index": index, "kind": kind,
                                      "exception_type": row.get("exception", {}).get("type")}),
                          flush=True)
                    if kind == "search_default":
                        data = decoded(row)
                        if not isinstance(data, list) or not data:
                            raise ValueError("Default search readiness requires nonempty JSON list")
                        icon = data[0]["name"]
                        assert isinstance(icon, str) and icon.strip()
                    elif kind == "glyph_by_style":
                        if not decoded(row):
                            raise ValueError("Fixed native glyph alternative returned empty data")
        except Exception as error:
            terminal = "stopped_readiness_unestablished"
            stopping = {"stage": stage, "type": type(error).__name__, "message": str(error)}
            break
    for item in plan["source"]:
        assert sha(ROOT / item["path"]) == item["sha256"]
    save(FOLDER / "execution.json", {
        "status": terminal, "stopping": stopping, "tool_calls": len(rows),
        "catalog_calls": catalogs, "model_calls": 0, "model_usd": 0,
        "ended_utc": datetime.now(UTC).isoformat(),
    })
    print(json.dumps({"status": terminal, "tool_calls": len(rows),
                      "catalog_calls": catalogs, "stopping_type": stopping and stopping["type"]}),
          flush=True)


if __name__ == "__main__":
    asyncio.run(main())

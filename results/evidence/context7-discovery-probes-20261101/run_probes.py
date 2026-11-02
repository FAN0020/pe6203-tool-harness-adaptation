"""Execute the frozen Context7 discovery/readiness schedule once; no model calls."""

import asyncio
import hashlib
import json
import re
import subprocess
from contextlib import AsyncExitStack
from datetime import UTC, datetime
from pathlib import Path

from pe6203.experiment import configure_runtime
from pe6203.transport import sessions

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[2]
PLAN = ROOT / "experiments/context7-discovery-probes-v1.json"


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def response_text(row):
    if "exception" in row or row.get("result", {}).get("isError"):
        raise ValueError("Native transport/tool failure")
    return "\n".join(c.get("text", "") for c in row["result"].get("content", []))


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
    rows, catalog_count, clients, names, library_ids = [], 0, {}, {}, {}
    terminal, stopping, step = "completed_requires_review", None, None
    try:
        async with AsyncExitStack() as stack:
            for step in plan["schedule"]:
                stage, tool = step["stage"], step["tool"]
                if stage not in clients:
                    work = FOLDER / "workspaces" / stage
                    work.mkdir(parents=True, exist_ok=False)
                    opened = await stack.enter_async_context(sessions(
                        ROOT, stage, [plan["server"]], work,
                        FOLDER / f"{stage}-stderr.log", timeout=45))
                    clients[stage] = opened[plan["server"]]
                    catalog = (await clients[stage].list_tools()).model_dump(
                        mode="json", by_alias=True)
                    save(FOLDER / f"{stage}-catalog.json", catalog)
                    catalog_count += 1
                    names[stage] = {t["name"] for t in catalog["tools"]}
                assert tool in names[stage]
                args = dict(step["arguments"])
                if step["kind"] == "documentation":
                    args["libraryId"] = library_ids[stage]
                row = {"stage": stage, "index": len(rows) + 1, "kind": step["kind"],
                       "tool": tool, "arguments": args,
                       "started_utc": datetime.now(UTC).isoformat()}
                try:
                    result = await asyncio.wait_for(clients[stage].call_tool(tool, args), 30)
                    row["result"] = result.model_dump(
                        mode="json", by_alias=True, exclude_none=True)
                except Exception as error:
                    row["exception"] = {"type": type(error).__name__, "message": str(error)}
                row["ended_utc"] = datetime.now(UTC).isoformat()
                save(FOLDER / f"call-{row['index']:02d}.json", row)
                rows.append(row)
                save(FOLDER / "observations.json", rows)
                print(json.dumps({"stage": stage, "index": row["index"],
                                  "kind": step["kind"],
                                  "exception_type": row.get("exception", {}).get("type")}),
                      flush=True)
                value = response_text(row)
                if step["kind"] == "discovery":
                    if "CONTEXT7_API_BASE_URL is not defined" not in value:
                        raise ValueError("Predicted discovery failure not observed; stop for review")
                elif step["kind"] == "resolve":
                    found = re.search(r"Context7-compatible library ID:\s*(/[^\s]+)", value)
                    if not found:
                        raise ValueError("No library ID from fixed search; alternative unavailable")
                    library_ids[stage] = found.group(1)
                elif step["kind"] == "documentation":
                    if not value.strip() or any(marker in value.lower() for marker in (
                        "invalid api key", "rate limit", "error fetching", "request failed",
                        "documentation not found", "quota exceeded", "unauthorized",
                    )):
                        raise ValueError("Fixed documentation retrieval unavailable")
    except Exception as error:
        terminal = "stopped_readiness_unestablished"
        stopping = {"step": step, "type": type(error).__name__, "message": str(error)}
    for item in plan["source"]:
        assert sha(ROOT / item["path"]) == item["sha256"]
    save(FOLDER / "execution.json", {
        "status": terminal, "stopping": stopping, "tool_calls": len(rows),
        "catalog_calls": catalog_count, "library_ids": library_ids,
        "model_calls": 0, "model_usd": 0, "ended_utc": datetime.now(UTC).isoformat(),
    })
    print(json.dumps({"status": terminal, "tool_calls": len(rows),
                      "catalog_calls": catalog_count,
                      "stopping_type": stopping and stopping["type"]}), flush=True)


if __name__ == "__main__":
    asyncio.run(main())

"""Run the predeclared native MagicUI routing schedule once, without models."""

import asyncio
import hashlib
import json
import subprocess
from contextlib import AsyncExitStack
from datetime import UTC, datetime
from pathlib import Path

from pe6203.experiment import configure_runtime
from pe6203.transport import sessions

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[2]
PLAN = ROOT / "experiments/magicui-argument-routing-probes-v1.json"


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def main():
    assert not (FOLDER / "preexecution.json").exists(), "Do not repeat executed probes"
    plan = json.loads(PLAN.read_text())
    for entry in plan["source"]:
        assert sha(ROOT / entry["path"]) == entry["sha256"]
    configure_runtime(ROOT)
    save(FOLDER / "preexecution.json", {
        "plan_sha256": sha(PLAN), "collector_sha256": sha(Path(__file__)),
        "freeze_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "started_utc": datetime.now(UTC).isoformat(), "model_calls": 0,
    })
    clients, rows, catalogs = {}, [], {}
    status, stopping, step = "completed_requires_review", None, None
    try:
        async with AsyncExitStack() as stack:
            for step in plan["schedule"]:
                stage, tool = step["stage"], step["tool"]
                if stage not in clients:
                    workspace = FOLDER / "workspaces" / stage
                    workspace.mkdir(parents=True, exist_ok=False)
                    opened = await stack.enter_async_context(sessions(
                        ROOT, stage, [plan["server"]], workspace,
                        FOLDER / f"{stage}-stderr.log", timeout=45))
                    clients[stage] = opened[plan["server"]]
                    catalog = (await clients[stage].list_tools()).model_dump(mode="json", by_alias=True)
                    save(FOLDER / f"{stage}-catalog.json", catalog)
                    catalogs[stage] = {t["name"]: t for t in catalog["tools"]}
                assert tool in catalogs[stage], f"Missing native tool: {tool}"
                row = {"index": len(rows) + 1, **step, "started_utc": datetime.now(UTC).isoformat()}
                try:
                    response = await asyncio.wait_for(clients[stage].call_tool(tool, step["arguments"]), 30)
                    row["result"] = response.model_dump(mode="json", by_alias=True, exclude_none=True)
                except Exception as exc:
                    row["exception"] = {"type": type(exc).__name__, "message": str(exc)}
                row["ended_utc"] = datetime.now(UTC).isoformat()
                save(FOLDER / f"call-{row['index']:02d}.json", row)
                rows.append(row)
                save(FOLDER / "observations.json", rows)
                print(json.dumps({"stage": stage, "index": row["index"], "kind": step["kind"],
                                  "exception_type": row.get("exception", {}).get("type")}), flush=True)
                assert "exception" not in row, "Native transport failure; stop without retry"
                result = row["result"]
                text = "\n".join(c.get("text", "") for c in result.get("content", []))
                kind = step["kind"]
                if kind in ("details_argument_loss", "batch_argument_loss", "search_argument_loss"):
                    schema = catalogs[stage][tool]["inputSchema"]
                    assert schema.get("properties", {}) == {} and not schema.get("required"), "Expected empty native schema not observed"
                if kind == "details_argument_loss":
                    assert result.get("isError") and 'Component "undefined" not found' in text
                elif kind == "batch_argument_loss":
                    assert result.get("isError") and "No valid component names" in text
                else:
                    assert not result.get("isError"), "Unexpected tool failure; stop without alternate calls"
                    value = json.loads(text)
                    if kind == "registry":
                        assert any(c and c.get("name") == plan["canary_component"] for c in value), "Fixed canary unavailable"
                    elif kind == "index":
                        assert any(c.get("name") == plan["canary_component"] for group in value["categories"] for c in group["components"])
                    elif kind == "category":
                        assert any(c.get("name") == plan["canary_component"] and c.get("content") for c in value), "No actual code from unchanged category path"
                    elif kind == "search_argument_loss":
                        assert value.get("query") is None and value.get("category") is None
                        assert value["resultCount"] > 1 and any(c["name"] != plan["canary_component"] for c in value["results"])
    except Exception as exc:
        status = "stopped_readiness_unestablished"
        stopping = {"step": step, "type": type(exc).__name__, "message": str(exc)}
    for entry in plan["source"]:
        assert sha(ROOT / entry["path"]) == entry["sha256"]
    save(FOLDER / "execution.json", {
        "status": status, "stopping": stopping, "tool_calls": len(rows), "catalog_calls": len(catalogs),
        "model_calls": 0, "model_usd": 0, "ended_utc": datetime.now(UTC).isoformat(),
    })
    print(json.dumps({"status": status, "tool_calls": len(rows), "catalog_calls": len(catalogs),
                      "stopping_type": stopping and stopping["type"]}), flush=True)


if __name__ == "__main__":
    asyncio.run(main())

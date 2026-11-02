"""Frozen public native city/station filter probes. No retries or model calls."""
import asyncio
import hashlib
import json
import subprocess
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from pe6203.experiment import configure_runtime
from pe6203.transport import sessions

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[2]
PLAN = ROOT / "experiments/city-station-filter-probes-v2.json"


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def content(row):
    if "exception" in row or row.get("result", {}).get("isError"):
        raise ValueError("Native call failed")
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
    rows, catalogs, target_date = [], 0, None
    terminal = "completed_requires_review"
    stopping = None
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
                names = {t["name"] for t in catalog["tools"]}
                codes = None
                for index, kind in enumerate(plan["schedule"][stage], 1):
                    tool = kind.split(":")[0]
                    assert tool in names
                    if tool == "get-current-date":
                        arguments = {}
                    elif tool == "get-station-code-of-citys":
                        route = plan["synthetic_route"]
                        arguments = {"citys": route["from_city"] + "|" + route["to_city"]}
                    else:
                        assert target_date and codes
                        arguments = {**plan["ticket_arguments"], "date": target_date,
                                     "fromStation": codes[0], "toStation": codes[1]}
                        if "directOnly=true" in kind:
                            arguments["directOnly"] = True
                        if "stationExactMatch=true" in kind:
                            arguments["stationExactMatch"] = True
                    row = {"stage": stage, "index": index, "kind": kind, "tool": tool,
                           "arguments": arguments, "started_utc": datetime.now(UTC).isoformat()}
                    try:
                        result = await asyncio.wait_for(client.call_tool(tool, arguments), 30)
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
                    if tool == "get-current-date":
                        target_date = (date.fromisoformat(content(row).strip())
                                       + timedelta(days=3)).isoformat()
                    elif tool == "get-station-code-of-citys":
                        answer = json.loads(content(row))
                        route = plan["synthetic_route"]
                        codes = [answer[route[key]]["station_code"]
                                 for key in ("from_city", "to_city")]
                        assert all(isinstance(c, str) and c for c in codes)
                    elif kind == "get-tickets:default":
                        answer = json.loads(content(row))
                        if not isinstance(answer, list) or not answer:
                            raise ValueError("Default ticket readiness requires nonempty JSON list")
        except Exception as error:
            terminal = "stopped_readiness_unestablished"
            stopping = {"stage": stage, "type": type(error).__name__, "message": str(error)}
            break
    for item in plan["source"]:
        assert sha(ROOT / item["path"]) == item["sha256"]
    save(FOLDER / "execution.json", {
        "status": terminal, "stopping": stopping, "tool_calls": len(rows),
        "catalog_calls": catalogs, "model_calls": 0, "model_usd": 0,
        "target_date": target_date, "ended_utc": datetime.now(UTC).isoformat(),
    })
    print(json.dumps({"status": terminal, "tool_calls": len(rows),
                      "catalog_calls": catalogs, "stopping_type": stopping and stopping["type"]}),
          flush=True)


if __name__ == "__main__":
    asyncio.run(main())

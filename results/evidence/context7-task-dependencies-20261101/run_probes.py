"""One isolated synthetic memory round trip per stage, never retried."""

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
PLAN = ROOT / "experiments/context7-task-dependencies-v1.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


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
    rows, catalogs, states = [], 0, []
    status, stopping = "completed_requires_review", None
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
                assert not (work / "memory.jsonl").exists()
                for index, step in enumerate(plan["schedule"], 1):
                    assert step["tool"] in names
                    row = {"stage": stage, "index": index, **step,
                           "started_utc": datetime.now(UTC).isoformat()}
                    try:
                        result = await asyncio.wait_for(
                            client.call_tool(step["tool"], step["arguments"]), 30)
                        row["result"] = result.model_dump(
                            mode="json", by_alias=True, exclude_none=True)
                    except Exception as error:
                        row["exception"] = {"type": type(error).__name__, "message": str(error)}
                    row["ended_utc"] = datetime.now(UTC).isoformat()
                    save(FOLDER / f"{stage}-{index:02d}.json", row)
                    rows.append(row)
                    save(FOLDER / "observations.json", rows)
                    if "exception" in row or row["result"].get("isError"):
                        raise ValueError("Native memory call failed")
                    data = json.loads("\n".join(
                        c.get("text", "") for c in row["result"]["content"]))
                    expected = plan["entity"]
                    assert data == ([expected] if index == 1 else
                                    {"entities": [expected], "relations": []})
                raw = (work / "memory.jsonl").read_bytes()
                records = [json.loads(line) for line in raw.splitlines()]
                assert records == [{"type": "entity", **plan["entity"]}]
                (FOLDER / f"{stage}-memory.jsonl").write_bytes(raw)
                states.append({"stage": stage, "sha256": sha(work / "memory.jsonl"),
                               "records": records})
                save(FOLDER / "state-checks.json", states)
                print(json.dumps({"stage": stage, "round_trip": True}), flush=True)
        except Exception as error:
            status = "stopped_readiness_unestablished"
            stopping = {"stage": stage, "type": type(error).__name__, "message": str(error)}
            break
    for item in plan["source"]:
        assert sha(ROOT / item["path"]) == item["sha256"]
    save(FOLDER / "execution.json", {
        "status": status, "stopping": stopping, "tool_calls": len(rows),
        "catalog_calls": catalogs, "model_calls": 0, "model_usd": 0,
        "ended_utc": datetime.now(UTC).isoformat(),
    })
    print(json.dumps({"status": status, "tool_calls": len(rows),
                      "catalog_calls": catalogs}), flush=True)


if __name__ == "__main__":
    asyncio.run(main())

"""Frozen native weather provenance/readiness probes; no model calls or retries."""
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
PLAN = ROOT / "experiments/weather-provenance-probes-v1.json"


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def main():
    assert not (FOLDER / "preexecution.json").exists(), "No repeat execution"
    plan = json.loads(PLAN.read_text())
    for source in plan["source"]:
        assert sha(ROOT / source["path"]) == source["sha256"]
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    configure_runtime(ROOT)
    save(FOLDER / "preexecution.json", {
        "plan_sha256": sha(PLAN), "collector_sha256": sha(Path(__file__)),
        "freeze_commit": commit, "model_calls": 0,
        "started_utc": datetime.now(UTC).isoformat(),
    })
    rows = []
    for stage in plan["stages"]:
        work = FOLDER / "workspaces" / stage
        work.mkdir(parents=True, exist_ok=False)
        server = plan["server"]
        async with sessions(ROOT, stage, [server], work,
                            FOLDER / f"{stage}-stderr.log", timeout=30) as clients:
            client = clients[server]
            catalog = (await client.list_tools()).model_dump(mode="json", by_alias=True)
            save(FOLDER / f"{stage}-catalog.json", catalog)
            names = {tool["name"] for tool in catalog["tools"]}
            assert ("get-weather-advice" in names) == (stage != "early")
            for index, call in enumerate(plan["calls"][stage], 1):
                assert call["tool"] in names
                row = {"stage": stage, "index": index, **call,
                       "started_utc": datetime.now(UTC).isoformat()}
                try:
                    result = await client.call_tool(call["tool"], call["arguments"])
                    row["result"] = result.model_dump(
                        mode="json", by_alias=True, exclude_none=True)
                except Exception as error:
                    row["exception"] = {"type": type(error).__name__, "message": str(error)}
                row["ended_utc"] = datetime.now(UTC).isoformat()
                save(FOLDER / f"{stage}-{index:02d}.json", row)
                rows.append(row)
                save(FOLDER / "observations.json", rows)
                print(json.dumps({"stage": stage, "index": index, "kind": call["kind"],
                                  "exception": row.get("exception")}), flush=True)
    for source in plan["source"]:
        assert sha(ROOT / source["path"]) == source["sha256"]
    assert len(rows) == plan["tool_calls"]
    save(FOLDER / "execution.json", {
        "status": "finished_calls_require_review", "tool_calls": len(rows),
        "catalog_calls": 3, "model_calls": 0, "model_usd": 0,
        "ended_utc": datetime.now(UTC).isoformat(),
    })


if __name__ == "__main__":
    asyncio.run(main())

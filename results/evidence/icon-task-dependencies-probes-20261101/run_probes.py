"""Fixed native dependency readiness; stop on failure without retry."""
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
PLAN = ROOT / "experiments/icon-task-dependencies-probes-v1.json"


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    status, stopping = "completed_requires_review", None
    for stage in plan["stages"]:
        work = FOLDER / "workspaces" / stage
        work.mkdir(parents=True, exist_ok=False)
        try:
            servers = list(dict.fromkeys(x["server"] for x in plan["schedule"]))
            async with sessions(ROOT, stage, servers, work,
                                FOLDER / f"{stage}-stderr.log", timeout=45) as clients:
                for index, server in enumerate(servers):
                    catalog = (await clients[server].list_tools()).model_dump(
                        mode="json", by_alias=True)
                    save(FOLDER / f"{stage}-catalog-{index}.json", catalog)
                    catalogs += 1
                for index, case in enumerate(plan["schedule"], 1):
                    row = {"stage": stage, "index": index, **case,
                           "started_utc": datetime.now(UTC).isoformat()}
                    try:
                        result = await asyncio.wait_for(clients[case["server"]].call_tool(
                            case["tool"], case["arguments"]), 30)
                        row["result"] = result.model_dump(
                            mode="json", by_alias=True, exclude_none=True)
                    except Exception as error:
                        row["exception"] = {"type": type(error).__name__, "message": str(error)}
                    row["ended_utc"] = datetime.now(UTC).isoformat()
                    save(FOLDER / f"{stage}-{index:02d}.json", row)
                    rows.append(row)
                    save(FOLDER / "observations.json", rows)
                    print(json.dumps({"stage": stage, "index": index,
                                      "exception": row.get("exception", {}).get("type")}),
                          flush=True)
                    assert "exception" not in row, "Native call exception"
                    assert not row["result"].get("isError"), "Native tool error"
                    content = "\n".join(c.get("text", "")
                                        for c in row["result"].get("content", []))
                    if index < 3:
                        assert "Button" in content
                        assert ("API" if index == 1 else "import") in content
                    else:
                        assert json.loads(content).get("success") is True
                        assert (work / "probe.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
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
                      "catalog_calls": catalogs, "stopping": stopping}), flush=True)


if __name__ == "__main__":
    asyncio.run(main())

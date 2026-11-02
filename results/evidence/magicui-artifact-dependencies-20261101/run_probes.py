"""One-shot isolated dependency readiness, never a substitute for task377 logs."""

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
PLAN = ROOT / "experiments/magicui-artifact-dependencies-v1.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


async def main():
    assert not (FOLDER / "preexecution.json").exists(), "Do not repeat executed probes"
    plan = json.loads(PLAN.read_text())
    for item in plan["source"]:
        assert sha(ROOT / item["path"]) == item["sha256"]
    configure_runtime(ROOT)
    save(FOLDER / "preexecution.json", {
        "plan_sha256": sha(PLAN), "collector_sha256": sha(Path(__file__)),
        "freeze_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "started_utc": datetime.now(UTC).isoformat(),
    })
    status, stopping, rows, catalog_count, step = "completed_requires_review", None, [], 0, None
    try:
        for index, step in enumerate(plan["schedule"], 1):
            workspace = FOLDER / "workspaces" / step["kind"]
            workspace.mkdir(parents=True, exist_ok=False)
            if step["kind"] == "file_roundtrip":
                (workspace / "probe-input.txt").write_text(plan["canary_text"])
            async with sessions(ROOT, "late", [step["server"]], workspace,
                                FOLDER / f"{step['kind']}-stderr.log", timeout=30) as opened:
                client = opened[step["server"]]
                catalog = (await client.list_tools()).model_dump(mode="json", by_alias=True)
                save(FOLDER / f"{step['kind']}-catalog.json", catalog)
                catalog_count += 1
                assert step["tool"] in {x["name"] for x in catalog["tools"]}
                row = {"index": index, **step, "started_utc": datetime.now(UTC).isoformat()}
                try:
                    result = await asyncio.wait_for(client.call_tool(step["tool"], step["arguments"]), 30)
                    row["result"] = result.model_dump(mode="json", by_alias=True, exclude_none=True)
                except Exception as exc:
                    row["exception"] = {"type": type(exc).__name__, "message": str(exc)}
                row["ended_utc"] = datetime.now(UTC).isoformat()
                rows.append(row)
                save(FOLDER / f"call-{index:02d}.json", row)
                save(FOLDER / "observations.json", rows)
                assert "exception" not in row and not row["result"].get("isError")
                text = "\n".join(x.get("text", "") for x in row["result"]["content"])
                data = json.loads(text)
                if step["kind"] == "file_roundtrip":
                    assert data["input"] == plan["canary_text"]
                    assert Path(data["cwd"]) == workspace.resolve()
                    artifact = json.loads((workspace / "probe-output.json").read_text())
                    assert artifact == {"received": plan["canary_text"]}
                    assert (workspace / "probe-page.html").read_text() == plan["canary_html"]
                else:
                    assert any(x["name"] == plan["canary_component"] and x.get("content") for x in data)
                print(json.dumps({"index": index, "kind": step["kind"], "status": "recorded"}), flush=True)
    except Exception as exc:
        status = "stopped_readiness_unestablished"
        stopping = {"step": step, "type": type(exc).__name__, "message": str(exc)}
    for item in plan["source"]:
        assert sha(ROOT / item["path"]) == item["sha256"]
    save(FOLDER / "execution.json", {
        "status": status, "stopping": stopping, "tool_calls": len(rows), "catalog_calls": catalog_count,
        "model_calls": 0, "model_usd": 0, "ended_utc": datetime.now(UTC).isoformat(),
    })
    print(json.dumps({"status": status, "tool_calls": len(rows), "catalog_calls": catalog_count}), flush=True)


if __name__ == "__main__":
    asyncio.run(main())

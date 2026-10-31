"""Native schema-compatible path termination and unchanged CSV preview readiness."""
import asyncio
import hashlib
import json
from pathlib import Path

from pe6203.experiment import configure_runtime
from pe6203.transport import sessions

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[2]
PLAN = ROOT / "experiments/thinking-contract-probes-v2.json"


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def main():
    assert not (FOLDER / "preexecution.json").exists()
    plan = json.loads(PLAN.read_text())
    for source in plan["source"]:
        assert sha(ROOT / source["path"]) == source["sha256"]
    configure_runtime(ROOT)
    save(FOLDER / "preexecution.json", {"plan_sha256": sha(PLAN),
         "freeze_commit": "f2adb7b", "profile_sha256": sha(ROOT / "configs/server-profiles.json"),
         "model_calls": 0})
    rows = []
    for stage, calls in plan["notebook_calls"].items():
        work = FOLDER / "workspaces" / f"{stage}-notebook"
        work.mkdir(parents=True, exist_ok=False)
        server = "@modelcontextprotocol/server-sequential-thinking"
        async with sessions(ROOT, stage, [server], work,
                            FOLDER / f"{stage}-notebook-stderr.log") as clients:
            client = clients[server]
            save(FOLDER / f"{stage}-notebook-catalog.json",
                 (await client.list_tools()).model_dump(mode="json", by_alias=True))
            for index, call in enumerate(calls, 1):
                result = (await client.call_tool(call["tool"], call["arguments"])).model_dump(
                    mode="json", by_alias=True, exclude_none=True)
                row = {"stage": stage, "kind": "notebook", "index": index, **call, "result": result}
                save(FOLDER / f"{stage}-notebook-{index:02d}.json", row)
                rows.append(row)
                assert not result.get("isError")
                state = result["structuredContent"]
                assert state["pathId"] == "synthetic_one"
                assert state["pathStatus"] == call["arguments"]["pathStatus"]
                assert state["activePaths"] == (["synthetic_one"] if index == 1 else [])
                assert "synthesisReady" not in state and "pathsSummary" not in state
    readiness = plan["csv_readiness"]
    original = ROOT / readiness["fixture"]
    assert sha(original) == readiness["fixture_sha256"]
    preview = "\n".join(original.read_text().splitlines()[:4])
    for stage in readiness["stages"]:
        work = FOLDER / "workspaces" / f"{stage}-csv"
        target = work / readiness["destination"]
        target.parent.mkdir(parents=True, exist_ok=False)
        target.write_bytes(original.read_bytes())
        server = readiness["server"]
        async with sessions(ROOT, stage, [server], work,
                            FOLDER / f"{stage}-csv-stderr.log") as clients:
            client = clients[server]
            save(FOLDER / f"{stage}-csv-catalog.json",
                 (await client.list_tools()).model_dump(mode="json", by_alias=True))
            args = dict(readiness["arguments"], cwd=str(work))
            result = (await client.call_tool("run_process", args)).model_dump(
                mode="json", by_alias=True, exclude_none=True)
            row = {"stage": stage, "kind": "csv", "tool": "run_process",
                   "arguments": args, "result": result, "fixture_sha256": sha(target)}
            save(FOLDER / f"{stage}-csv.json", row)
            rows.append(row)
            assert not result.get("isError")
            texts = "\n".join(c.get("text", "") for c in result["content"])
            assert preview in texts.replace("\r\n", "\n")
            assert sha(target) == readiness["fixture_sha256"]
    assert len(rows) == plan["tool_calls"]
    for source in plan["source"]:
        assert sha(ROOT / source["path"]) == source["sha256"]
    save(FOLDER / "observations.json", rows)
    print(json.dumps({"tool_calls": 7, "catalog_calls": 5, "model_calls": 0,
                      "notebook_terminal_pass": True, "original_csv_preview_pass": True}))


if __name__ == "__main__":
    asyncio.run(main())

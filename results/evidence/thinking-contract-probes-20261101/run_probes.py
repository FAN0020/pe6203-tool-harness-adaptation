"""Fixed native notebook probes; no model calls, no modified upstream code."""
import asyncio
import hashlib
import json
from pathlib import Path

from pe6203.experiment import configure_runtime
from pe6203.transport import sessions

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[2]
PLAN = ROOT / "experiments/thinking-contract-probes-v1.json"


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def main():
    assert not (FOLDER / "preexecution.json").exists(), "Never rerun completed calls"
    plan = json.loads(PLAN.read_text())
    for source in plan["source"]:
        assert sha(ROOT / source["path"]) == source["sha256"]
    configure_runtime(ROOT)
    save(FOLDER / "preexecution.json", {"plan_sha256": sha(PLAN),
         "freeze_commit": "3ccebd3", "source": plan["source"], "model_calls": 0})
    rows = []
    for stage in plan["stages"]:
        work = FOLDER / "workspaces" / stage
        work.mkdir(parents=True, exist_ok=False)
        async with sessions(ROOT, stage, [plan["server"]], work,
                            FOLDER / f"{stage}-stderr.log") as clients:
            client = clients[plan["server"]]
            catalog = (await client.list_tools()).model_dump(mode="json", by_alias=True)
            save(FOLDER / f"{stage}-catalog.json", catalog)
            available = {tool["name"] for tool in catalog["tools"]}
            for index, call in enumerate(plan["calls"][stage], 1):
                assert call["tool"] in available
                result = (await client.call_tool(call["tool"], call["arguments"])).model_dump(
                    mode="json", by_alias=True, exclude_none=True)
                row = {"stage": stage, "index": index, **call, "result": result}
                save(FOLDER / stage / f"{index:02d}-{call['tool']}.json", row)
                rows.append(row)
    assert len(rows) == plan["planned_tool_calls"]
    for source in plan["source"]:
        assert sha(ROOT / source["path"]) == source["sha256"]
    save(FOLDER / "observations.json", rows)
    print(json.dumps({"tool_calls": len(rows), "catalog_calls": 3,
                      "model_calls": 0, "errors": sum(bool(r["result"].get("isError")) for r in rows)}))


if __name__ == "__main__":
    asyncio.run(main())

"""One frozen native-tool build, without agent calls or changing native implementations."""
import asyncio
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess

from pe6203.experiment import configure_runtime
from pe6203.transport import sessions

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
OUT = ROOT / "results/evidence/program-memory-runtime-20261101"


def save(name, value):
    (OUT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n")


async def main():
    path=BASE/"native-build-probe.json"
    plan=json.loads(path.read_text())
    assert not (OUT/"native-preexecution.json").exists(), "Already attempted; do not repeat"
    for name,expected in plan["source_hashes"].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected, name
    save("native-preexecution.json", {"plan_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
        "collector_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "utc":datetime.now(UTC).isoformat()})
    configure_runtime(ROOT)
    workspace=ROOT/plan["workspace"]
    async with sessions(ROOT,"late",[plan["server"]],workspace,OUT/"native-stderr.log",timeout=30) as opened:
        client=opened[plan["server"]]
        save("native-catalog.json",(await client.list_tools()).model_dump(mode="json",by_alias=True))
        result=await asyncio.wait_for(client.call_tool(plan["tool"],plan["arguments"]),30)
        raw=result.model_dump(mode="json",by_alias=True,exclude_none=True)
        save("native-result.json",raw)
        assert not raw.get("isError"), "Native tool build failed"
    assert all((workspace/p).stat().st_size>0 for p in ["public/app.js","public/styles.css"])
    save("native-build-result.json", {"tool_calls":1,"catalog_calls":1,"model_calls":0,
         "usd":0,"build_succeeded":True,"rendering":"pending_same_frozen_checks"})
    print("Native build completed; rendering still requires verification")


if __name__=="__main__":
    asyncio.run(main())

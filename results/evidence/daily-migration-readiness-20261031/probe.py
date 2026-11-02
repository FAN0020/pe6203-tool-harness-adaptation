"""Read-only feasibility audit; no model calls and no production profile changes."""

import asyncio
import hashlib
import json
import tempfile
from contextlib import AsyncExitStack
from datetime import UTC, datetime, timedelta
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import stdio_client

from pe6203.benchmark import source
from pe6203.experiment import configure_runtime
from pe6203.transport import launch_parameters, snapshot

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PROFILES = {
    "ygocdb-mcp-server": {"entry": "dist/index.js", "env": {"TRANSPORT": "stdio"}},
    "@jinzcdev/leetcode-mcp-server": {"entry": "build/index.js", "args": ["--site", "global"]},
}


def write(name, data):
    (HERE / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


async def main():
    if (HERE / "plan.json").exists():
        raise ValueError("Historical readiness output exists; never overwrite it")
    configure_runtime(ROOT)
    lock, _ = source(ROOT)
    plan = {
        "created_at": datetime.now(UTC).isoformat(),
        "new_model_calls": 0,
        "intent": "Check service readiness and task90 modality before selecting any experiment.",
        "selection_basis": "Released get_daily_challenge removal and get_problem(daily=true) migration.",
        "task_status": "Task90 previously exposed development; no protected-test claim.",
        "profiles": PROFILES,
        "calls": "Snapshot all three stages; generic card search and daily problem read in Early/Late only.",
        "credentials": "None inherited or supplied; global public site, no session cookie.",
        "production_changes": False,
        "stop_rule": "Record unavailable services without retries or substituting sites/data. No model run.",
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    write("plan.json", plan)
    observations = []
    for version in ("early", "middle", "late"):
        stage = lock["stages"][version]["directory"]
        with tempfile.TemporaryDirectory(prefix="pe6203-daily-readiness-") as workspace:
            with (HERE / f"{version}.stderr.log").open("w") as stderr:
                async with AsyncExitStack() as stack:
                    clients = {}
                    for server, profile in PROFILES.items():
                        parameters = launch_parameters(ROOT, stage, server, workspace, profile)
                        read, out = await stack.enter_async_context(
                            stdio_client(parameters, errlog=stderr)
                        )
                        client = await stack.enter_async_context(
                            ClientSession(read, out, read_timeout_seconds=timedelta(seconds=20))
                        )
                        await asyncio.wait_for(client.initialize(), 20)
                        clients[server] = client
                    catalog = await snapshot(clients, version, lock["commit"])
                    write(f"{version}-catalog.json", catalog)
                    print(version, "catalog", len(catalog["tools"]), flush=True)
                    if version == "middle":
                        continue
                    calls = [
                        ("ygocdb-mcp-server", "search_cards", {"query": "黑魔术师"}),
                        (
                            "@jinzcdev/leetcode-mcp-server",
                            "get_daily_challenge" if version == "early" else "get_problem",
                            {} if version == "early" else {"daily": True},
                        ),
                    ]
                    for server, tool, args in calls:
                        row = {
                            "version": version,
                            "server": server,
                            "tool": tool,
                            "arguments": args,
                            "time": datetime.now(UTC).isoformat(),
                        }
                        try:
                            result = await asyncio.wait_for(
                                clients[server].call_tool(tool, args), 20
                            )
                            row["result"] = result.model_dump(mode="json", exclude_none=True)
                        except Exception as exc:
                            row["exception"] = f"{type(exc).__name__}: {exc}"
                        observations.append(row)
                        write("observations.json", observations)
                        print(
                            version,
                            tool,
                            "returned" if "result" in row else row["exception"],
                            flush=True,
                        )
    write(
        "manifest.json",
        {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in HERE.iterdir()
            if p.is_file() and p.name != "manifest.json"
        },
    )


if __name__ == "__main__":
    asyncio.run(main())

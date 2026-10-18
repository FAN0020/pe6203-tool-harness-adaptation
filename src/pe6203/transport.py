import asyncio
import os
from contextlib import AsyncExitStack, asynccontextmanager
from datetime import timedelta
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .benchmark import source


def check_arguments(arguments, workspace):
    if "workingDirectory" in arguments:
        value = arguments["workingDirectory"]
        if not isinstance(value, str) or Path(value).resolve() != Path(workspace).resolve():
            raise ValueError("workingDirectory must equal the isolated run workspace")


@asynccontextmanager
async def sessions(root, version, server_ids, workspace, stderr_path, timeout=30):
    lock, _ = source(root)
    stage = lock["stages"][version]["directory"]
    workspace = Path(workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    with Path(stderr_path).open("a") as stderr:
        async with AsyncExitStack() as stack:
            clients = {}
            for server in server_ids:
                if server not in lock["servers"]:
                    raise ValueError(
                        f"Server {server} is not in the reviewed smoke-server manifest"
                    )
                entry = (
                    Path(root)
                    / ".cache/mcpevol"
                    / stage
                    / "node_modules"
                    / server
                    / lock["servers"][server]
                ).resolve()
                if not entry.is_file():
                    raise FileNotFoundError(f"Run pe6203 bootstrap --stages {version} first")
                # No API credentials are inherited by the local MCP children.
                parameters = StdioServerParameters(
                    command=os.environ.get("MCPEVOL_NODE", "node"),
                    args=[str(entry)],
                    cwd=str(workspace),
                    env={
                        "PATH": os.environ.get("PATH", ""),
                        "MEMORY_FILE_PATH": str(workspace / "knowledge.jsonl"),
                    },
                )
                read, write = await stack.enter_async_context(
                    stdio_client(parameters, errlog=stderr)
                )
                client = await stack.enter_async_context(
                    ClientSession(read, write, read_timeout_seconds=timedelta(seconds=timeout))
                )
                await asyncio.wait_for(client.initialize(), timeout)
                clients[server] = client
            yield clients


async def snapshot(clients, version, commit):
    records = []
    for server, client in clients.items():
        cursor = None
        while True:
            page = await client.list_tools(cursor=cursor)
            for tool in page.tools:
                records.append(
                    {
                        "tool_id": f"{server}::{tool.name}",
                        "server_id": server,
                        "version": version,
                        "name": tool.name,
                        "parameters": tool.inputSchema,
                        "description": tool.description or "",
                        "usage_rules": [],
                        "output_schema": tool.outputSchema,
                        "routing": {"server_id": server, "tool_name": tool.name},
                    }
                )
            cursor = page.nextCursor
            if not cursor:
                break
    return {
        "schema_version": "1.0",
        "benchmark_commit": commit,
        "version": version,
        "source": "live_released_mcp_servers",
        "tools": records,
    }

import asyncio
import os
from contextlib import AsyncExitStack, asynccontextmanager
from copy import deepcopy
from datetime import timedelta
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .benchmark import read_json, source


def check_arguments(arguments, workspace):
    workspace = Path(workspace).resolve()
    for field in ("workingDirectory", "workspace"):
        if field in arguments:
            value = arguments[field]
            if not isinstance(value, str) or Path(value).resolve() != workspace:
                raise ValueError(f"{field} must equal the isolated run workspace")
    if "source_path" in arguments:
        value = arguments["source_path"]
        if not isinstance(value, str) or not (workspace / value).resolve().is_relative_to(
            workspace
        ):
            raise ValueError("source_path must stay inside the isolated run workspace")


def server_profiles(root, lock):
    path = Path(root) / "configs/server-profiles.json"
    if path.exists():
        manifest = read_json(path)
        if manifest["benchmark_commit"] != lock["commit"]:
            raise ValueError("Server profiles benchmark commit mismatch")
        return manifest["servers"]
    return {
        sid: {"entry": entry, "env": {"MEMORY_FILE_PATH": "{workspace}/knowledge.jsonl"}}
        for sid, entry in lock["servers"].items()
    }


def launch_parameters(root, stage, server, workspace, profile):
    workspace = Path(workspace).resolve()
    package = (Path(root) / ".cache/mcpevol" / stage / "node_modules" / server).resolve()
    entry = (package / profile["entry"]).resolve()
    if not entry.is_relative_to(package):
        raise ValueError("Server entry must stay inside its archived package")
    if not entry.is_file():
        raise FileNotFoundError(
            f"Archived server entry missing: {server}; run bootstrap --scope all"
        )
    home = workspace / ".home"
    home.mkdir(parents=True, exist_ok=True)
    env = {"PATH": os.environ.get("PATH", ""), "HOME": str(home), "TMPDIR": str(workspace)}
    env.update(
        {
            k: v.replace("{workspace}", str(workspace)).replace("{root}", str(Path(root).resolve()))
            for k, v in profile.get("env", {}).items()
        }
    )
    return StdioServerParameters(
        command=os.environ.get("MCPEVOL_NODE", "node"),
        args=[
            str(entry),
            *[a.replace("{workspace}", str(workspace)) for a in profile.get("args", [])],
        ],
        cwd=str(workspace),
        env=env,
    )


@asynccontextmanager
async def sessions(root, version, server_ids, workspace, stderr_path, timeout=30):
    lock, _ = source(root)
    stage = lock["stages"][version]["directory"]
    profiles = server_profiles(root, lock)
    workspace = Path(workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    with Path(stderr_path).open("a") as stderr:
        async with AsyncExitStack() as stack:
            clients = {}
            for server in server_ids:
                if server not in profiles:
                    raise ValueError(
                        f"Server {server} has no reviewed runtime profile; see benchmark inventory"
                    )
                # No API credentials are inherited by the local MCP children.
                parameters = launch_parameters(root, stage, server, workspace, profiles[server])
                read, write = await stack.enter_async_context(
                    stdio_client(parameters, errlog=stderr)
                )
                client = await stack.enter_async_context(
                    ClientSession(read, write, read_timeout_seconds=timedelta(seconds=timeout))
                )
                await asyncio.wait_for(client.initialize(), timeout)
                clients[server] = client
            yield clients


def compatible_input_schema(server, tool, schema):
    """Translate the released PDF page bound without changing its accepted values.

    This is a common transport compatibility rule, not a strategy. Only the
    reviewed legacy location is supported; all other metadata stays verbatim.
    """
    result = deepcopy(schema)
    if (server, tool) != ("@sylphlab/pdf-reader-mcp", "read_pdf"):
        return result, None
    path = ("properties", "sources", "items", "properties", "pages", "anyOf", 0, "items")
    try:
        node = result
        for key in path:
            node = node[key]
    except (KeyError, IndexError, TypeError):
        return result, None
    if not isinstance(node, dict) or not isinstance(node.get("exclusiveMinimum"), bool):
        return result, None
    if type(node.get("minimum")) not in (int, float):
        raise ValueError("Legacy PDF exclusive bound requires a numeric minimum")
    original = deepcopy(node)
    exclusive = node.pop("exclusiveMinimum")
    if exclusive:
        node["exclusiveMinimum"] = node.pop("minimum")
    return result, {"path": list(path), "original": original, "normalized": deepcopy(node)}


async def snapshot(clients, version, commit):
    records = []
    compatibility = []
    for server, client in clients.items():
        cursor = None
        while True:
            page = await client.list_tools(cursor=cursor)
            for tool in page.tools:
                parameters, audit = compatible_input_schema(server, tool.name, tool.inputSchema)
                if audit:
                    compatibility.append({"server": server, "tool": tool.name, **audit})
                records.append(
                    {
                        "tool_id": f"{server}::{tool.name}",
                        "server_id": server,
                        "version": version,
                        "name": tool.name,
                        "parameters": parameters,
                        "description": tool.description or "",
                        "usage_rules": [],
                        "output_schema": tool.outputSchema,
                        "routing": {"server_id": server, "tool_name": tool.name},
                    }
                )
            cursor = page.nextCursor
            if not cursor:
                break
    result = {
        "schema_version": "1.0",
        "benchmark_commit": commit,
        "version": version,
        "source": "live_released_mcp_servers",
        "tools": records,
    }
    if compatibility:
        result["schema_compatibility"] = compatibility
    return result

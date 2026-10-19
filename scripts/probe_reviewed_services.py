"""Executable integration checks, not model tasks or benchmark scores.

Run: uv run python scripts/probe_reviewed_services.py --output results/raw/services-check
Requires bootstrap --scope all and the pinned MCPEVOL_NODE.
"""

import argparse
import asyncio
import json
from pathlib import Path

from pe6203.audit import error_detail
from pe6203.benchmark import digest, source, write_json
from pe6203.transport import sessions

SERVERS = {
    "memory": "@modelcontextprotocol/server-memory",
    "filesystem": "@modelcontextprotocol/server-filesystem",
    "thinking": "@modelcontextprotocol/server-sequential-thinking",
    "tasks": "mcp-tasks",
    "calculator": "mcp-calculator",
    "math": "math-mcp",
}


async def verify(root, output):
    output.mkdir(parents=True, exist_ok=False)
    lock, _ = source(root)
    report = {
        "kind": "real_mcp_functional_probe",
        "benchmark_commit": lock["commit"],
        "dataset_revision": lock["dataset_revision"],
        "model_used": None,
        "task_evaluation": False,
        "TF": None,
        "PE": None,
        "ECS": None,
        "checks": [],
    }
    for stage in lock["stages"]:
        for label, server in SERVERS.items():
            directory = output / stage / label
            workspace = directory / "workspace"
            workspace.mkdir(parents=True)
            calls = []
            record = {"version": stage, "server_id": server, "status": "failed", "calls": calls}

            async def call(clients, name, arguments):
                response = await clients[server].call_tool(name, arguments)
                data = response.model_dump(mode="json", exclude_none=True)
                calls.append({"name": name, "arguments": arguments, "result": data})
                write_json(directory / "calls.json", calls)
                if response.isError:
                    raise AssertionError(f"Tool error: {name}")
                return "\n".join(x.get("text", "") for x in data.get("content", []))

            def connect():
                return sessions(root, stage, [server], workspace, directory / "stderr.log")

            try:
                async with asyncio.timeout(45):
                    async with connect() as clients:
                        if label == "memory":
                            await call(
                                clients,
                                "create_entities",
                                {
                                    "entities": [
                                        {
                                            "name": "PE6203_probe",
                                            "entityType": "check",
                                            "observations": ["restart persistence"],
                                        }
                                    ]
                                },
                            )
                        elif label == "filesystem":
                            await call(
                                clients,
                                "write_file",
                                {
                                    "path": str(workspace / "probe.txt"),
                                    "content": "PE6203_probe",
                                },
                            )
                        elif label == "tasks":
                            await call(
                                clients,
                                "tasks_setup",
                                {
                                    "workspace": str(workspace),
                                    "source_path": str(workspace / "tasks.md"),
                                },
                            )
                            await call(
                                clients, "tasks_add", {"texts": ["PE6203_probe"], "status": "To Do"}
                            )
                        elif label == "calculator":
                            result = await call(clients, "add", {"a": 2, "b": 5})
                            assert "7" in result, result
                        elif label == "math":
                            result = await call(clients, "evaluate", {"expression": "2+5"})
                            assert "7" in result, result
                        else:
                            result = await call(
                                clients,
                                "sequentialthinking",
                                {
                                    "thought": "Check local MCP response format.",
                                    "nextThoughtNeeded": False,
                                    "thoughtNumber": 1,
                                    "totalThoughts": 1,
                                },
                            )
                            assert json.loads(result)["thoughtNumber"] == 1, result
                    if label in ("memory", "filesystem", "tasks"):
                        async with connect() as clients:
                            if label == "memory":
                                result = await call(clients, "read_graph", {})
                            elif label == "filesystem":
                                result = await call(
                                    clients,
                                    "read_text_file",
                                    {"path": str(workspace / "probe.txt")},
                                )
                            else:
                                result = await call(
                                    clients, "tasks_search", {"terms": ["PE6203_probe"]}
                                )
                            assert "PE6203_probe" in result, result
                        record["fresh_process_persistence"] = True
                    record["status"] = "verified"
            except Exception as exc:
                record["error"] = error_detail(exc)
            record["call_object_sha256"] = digest(calls)
            report["checks"].append(record)
            write_json(output / "functional-probes.json", report)
            print(stage, label, record["status"], record.get("error", ""), flush=True)
    return all(c["status"] == "verified" for c in report["checks"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(0 if asyncio.run(verify(Path.cwd(), args.output.resolve())) else 2)

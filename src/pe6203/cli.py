import argparse
import asyncio
import json
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

from .benchmark import load_task, read_json, source, write_json
from .bootstrap import bootstrap
from .judge import ecs
from .runner import run
from .transport import sessions, snapshot


async def metadata(root, version, output):
    lock, upstream = source(root)
    task = load_task(upstream, lock["smoke_task_id"])
    with tempfile.TemporaryDirectory(prefix="mcpevol-metadata-") as tmp:
        async with sessions(
            root, version, task["servers"], Path(tmp), Path(tmp) / "stderr.log"
        ) as clients:
            result = await snapshot(clients, version, lock["commit"])
    write_json(output, result)
    return {"output": str(output), "version": version, "tools": len(result["tools"])}


async def probe(root, version, output):
    """Scripted real MCP operations. Deliberately not labeled an agent or benchmark run."""
    lock, upstream = source(root)
    task = load_task(upstream, lock["smoke_task_id"])
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    workspace = output / "workspace"
    calls = []
    project_server, graph_server = list(lock["servers"])

    async def invoke(clients, server, name, arguments):
        response = await clients[server].call_tool(name, arguments)
        result = response.model_dump(mode="json", exclude_none=True)
        calls.append({"server_id": server, "name": name, "arguments": arguments, "result": result})
        write_json(output / "calls.json", calls)
        if response.isError:
            raise RuntimeError(f"MCP probe failed: {server}/{name}")
        return result

    async with sessions(
        root, version, task["servers"], workspace, output / "mcp.stderr.log"
    ) as clients:
        catalog = await snapshot(clients, version, lock["commit"])
        write_json(output / "metadata.json", catalog)
        await invoke(
            clients,
            project_server,
            "create_project",
            {
                "workingDirectory": str(workspace),
                "name": "PE6203 environment probe",
                "description": "Isolated transport test, not a benchmark result",
            },
        )
        state = read_json(workspace / ".agentic-tools-mcp/tasks/tasks.json")
        await invoke(
            clients,
            project_server,
            "create_task",
            {
                "workingDirectory": str(workspace),
                "name": "Verify persistence",
                "details": "Reload through a fresh MCP process",
                "projectId": state["projects"][0]["id"],
            },
        )
        await invoke(
            clients,
            graph_server,
            "create_entities",
            {
                "entities": [
                    {
                        "name": "Environment",
                        "entityType": "component",
                        "observations": ["real MCP probe"],
                    },
                    {
                        "name": "Persistence",
                        "entityType": "check",
                        "observations": ["fresh-process reload"],
                    },
                ]
            },
        )
        await invoke(
            clients,
            graph_server,
            "create_relations",
            {
                "relations": [
                    {"from": "Environment", "to": "Persistence", "relationType": "verifies"}
                ]
            },
        )
    # Prove state survives server shutdown and a fresh connection.
    async with sessions(
        root, version, task["servers"], workspace, output / "mcp.stderr.log"
    ) as clients:
        projects = await invoke(
            clients, project_server, "list_projects", {"workingDirectory": str(workspace)}
        )
        graph = await invoke(clients, graph_server, "read_graph", {})
    persisted = "PE6203 environment probe" in json.dumps(projects) and all(
        word in json.dumps(graph) for word in ("Environment", "Persistence", "verifies")
    )
    result = {
        "kind": "real_mcp_transport_probe",
        "version": version,
        "benchmark_commit": lock["commit"],
        "dataset_revision": lock["dataset_revision"],
        "TF": None,
        "PE": None,
        "ECS": None,
        "model_used": None,
        "persistent_state_verified": persisted,
        "calls": calls,
    }
    write_json(output / "probe.json", result)
    if not persisted:
        raise RuntimeError("MCP persistence verification failed")
    return {k: v for k, v in result.items() if k != "calls"}


def doctor(root):
    lock, upstream = source(root)
    node = os.environ.get("MCPEVOL_NODE", "node")

    def version(command):
        try:
            return subprocess.check_output(
                command, text=True, stderr=subprocess.STDOUT, timeout=10
            ).strip()
        except (OSError, subprocess.SubprocessError):
            return "unavailable"

    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "node": version([node, "--version"]),
        "npm": version(["npm", "--version"]),
        "docker_client": version(["docker", "--version"]),
        "container_required": False,
        "upstream_commit": lock["commit"],
        "dataset_revision": lock["dataset_revision"],
        "task": load_task(upstream, lock["smoke_task_id"]),
        "credentials": {
            name: bool(os.environ.get(name))
            for name in ("AGENT_API_KEY", "AGENT_BASE_URL", "JUDGE_API_KEY", "JUDGE_BASE_URL")
        },
        "stages_installed": {
            v: (root / ".cache/mcpevol" / spec["directory"] / "extraction.json").exists()
            for v, spec in lock["stages"].items()
        },
    }


def main():
    parser = argparse.ArgumentParser(description="PE6203 Group A MCPEvol environment and runner")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project checkout root")
    sub = parser.add_subparsers(dest="command", required=True)
    report = sub.add_parser("report", help="Read saved run or baseline pilot results; no API calls")
    report.add_argument("inputs", type=Path, nargs="+")
    report.add_argument("--details", action="store_true")
    report.add_argument("--format", choices=["text", "json", "html"], default="text")
    report.add_argument("--output", type=Path, help="Save to a new .txt/.json/.html file")
    setup = sub.add_parser("bootstrap", help="Verify and install immutable benchmark releases")
    setup.add_argument(
        "--stages",
        nargs="+",
        choices=["early", "middle", "late"],
        default=["early", "middle", "late"],
    )
    for name in ("metadata", "probe"):
        p = sub.add_parser(name)
        p.add_argument("--version", choices=["early", "middle", "late"], required=True)
        p.add_argument("--output", type=Path, required=True)
    sub.add_parser("doctor", help="Report environment and credential presence, never secret values")
    p = sub.add_parser("run", help="Run agent -> real MCP -> official rubric judge -> saved logs")
    p.add_argument("--task-id", type=int, default=139)
    p.add_argument("--version", choices=["early", "middle", "late"], required=True)
    p.add_argument(
        "--strategy",
        choices=["no_update", "full_rewrite", "selective_patch", "current_metadata_smoke"],
        required=True,
    )
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--config", type=Path, default=Path("configs/smoke.json"))
    p.add_argument("--knowledge", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("ecs", help="Compute ECS from a JSON mapping of early/middle/late TF")
    p.add_argument("scores", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "report":
            from .report import render_saved_report

            rendered = render_saved_report(
                args.inputs, format_name=args.format, expanded=args.details, output=args.output
            )
            print(rendered, end="")
            return 0
        elif args.command == "bootstrap":
            result = bootstrap(args.root, args.stages)
            result = {
                k: {"files": v["files"], "packages": len(v["packages"])} for k, v in result.items()
            }
        elif args.command in ("metadata", "probe"):
            result = asyncio.run(globals()[args.command](args.root, args.version, args.output))
        elif args.command == "doctor":
            result = doctor(args.root)
        elif args.command == "ecs":
            result = ecs(read_json(args.scores))
        else:
            config = read_json(args.config)
            config.update(root=str(args.root), output_dir=str(args.output))
            if args.knowledge:
                config["knowledge_path"] = str(args.knowledge)
            _, result = run(args.task_id, args.version, args.strategy, args.seed, config)
            report_path = args.output / "report.txt"
            if args.format == "text" and report_path.is_file():
                print(report_path.read_text(encoding="utf-8"), end="")
            else:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0 if result["status"] == "evaluated" else 2
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:
        # API exceptions are already redacted and persisted inside run().
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

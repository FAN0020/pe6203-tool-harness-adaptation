import argparse
import asyncio
import json
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

from .audit import probe_servers
from .baselines import write_adaptation
from .batch import run_batch
from .benchmark import load_task, read_json, source, write_json
from .bootstrap import bootstrap
from .inventory import build_inventory
from .judge import ecs
from .report import render_saved_report
from .runner import run
from .transport import sessions, snapshot


async def metadata(root, version, output, task_id=None):
    lock, upstream = source(root)
    task = load_task(upstream, task_id if task_id is not None else lock["smoke_task_id"])
    with tempfile.TemporaryDirectory(prefix="mcpevol-metadata-") as tmp:
        async with sessions(
            root, version, task["servers"], Path(tmp), Path(tmp) / "stderr.log"
        ) as clients:
            result = await snapshot(clients, version, lock["commit"])
    write_json(output, result)
    return {
        "output": str(output),
        "task_id": task["idx"],
        "version": version,
        "tools": len(result["tools"]),
    }


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
    # Pass through so the experiment interface owns its help and nested commands.
    if len(sys.argv) > 1 and sys.argv[1] == "experiment":
        from .experiment import main as experiment_main

        return experiment_main(Path.cwd(), sys.argv[2:])
    parser = argparse.ArgumentParser(description="PE6203 Group A MCPEvol environment and runner")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project checkout root")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser(
        "experiment", add_help=False, help="Interactive experiment CLI: prepare/run/report/netlify"
    )
    p.add_argument("arguments", nargs=argparse.REMAINDER)
    p = sub.add_parser("report", help="Read saved run reports offline; no model calls")
    p.add_argument("inputs", nargs="+", type=Path, help="Run directories or saved evidence files")
    p.add_argument("--format", choices=["text", "json", "html"], default="text")
    p.add_argument("--details", action="store_true", help="Include tool calls and saved state")
    p.add_argument("--output", type=Path, help="Write to a new file without overwriting")
    p = sub.add_parser("adapt", help="Build knowledge; Full Rewrite and hybrid Patch use an LLM")
    p.add_argument(
        "--strategy", choices=["no_update", "full_rewrite", "selective_patch"], required=True
    )
    p.add_argument("--old-knowledge", type=Path, required=True)
    p.add_argument("--new-metadata", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument(
        "--selective-mode",
        choices=["deterministic_v1", "hybrid_v2", "hybrid_v3", "hybrid_v5", "hybrid_v6"],
        default="hybrid_v2",
        help="QI-V2 hybrid is the default; V1 is retained for historical comparisons",
    )
    p.add_argument("--capability-evidence", type=Path, help="Frozen V3 source evidence manifest")
    p.add_argument("--patch-budget", type=Path, help="Hybrid request/time limits JSON")
    p.add_argument("--evidence-bundle", type=Path, help="Independent V5 source/probe manifest")
    p.add_argument(
        "--validation-cases", type=Path, help="Independent argument regression cases JSON"
    )
    p.add_argument(
        "--updater-config", type=Path, help="Updater JSON settings; use env names for secrets"
    )
    p.add_argument(
        "--allow-metadata-api", action="store_true", help="Allow sending tool metadata to updater"
    )
    p = sub.add_parser(
        "collect-v5-probes", help="Run a reviewed, task-independent fixed MCP probe plan"
    )
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser(
        "run-v5", help="Explicit V5 knowledge plus optional Python artifact validation"
    )
    p.add_argument("--task-id", type=int, required=True)
    p.add_argument("--version", choices=["early", "middle", "late"], required=True)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--adaptation", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    scope = p.add_mutually_exclusive_group(required=True)
    scope.add_argument("--artifact-protocol", type=Path)
    scope.add_argument("--non-python-deliverable", action="store_true")
    p = sub.add_parser(
        "run-v6", help="Explicit V6 knowledge plus optional Python artifact validation"
    )
    p.add_argument("--task-id", type=int, required=True)
    p.add_argument("--version", choices=["early", "middle", "late"], required=True)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--adaptation", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    scope = p.add_mutually_exclusive_group(required=True)
    scope.add_argument("--artifact-protocol", type=Path)
    scope.add_argument("--non-python-deliverable", action="store_true")
    p = sub.add_parser("run-artifact-arm", help="Run one verified frozen five-arm experiment entry")
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument(
        "--arm",
        choices=["no_update", "full_rewrite", "deterministic_v1", "hybrid_v2", "hybrid_v3"],
        required=True,
    )
    p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser(
        "freeze-artifact-plan", help="Require and freeze equal execution budgets for five arms"
    )
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser(
        "validate-artifact", help="Check an exact JSON Python deliverable; Docker only"
    )
    p.add_argument("--answer", type=Path, required=True)
    p.add_argument("--protocol", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    setup = sub.add_parser("bootstrap", help="Verify and install immutable benchmark releases")
    setup.add_argument(
        "--stages",
        nargs="+",
        choices=["early", "middle", "late"],
        default=["early", "middle", "late"],
    )
    setup.add_argument("--scope", choices=["smoke", "all"], default="smoke")
    p = sub.add_parser("inventory", help="Audit all selected tasks and released server entries")
    p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser(
        "probe-servers", help="Initialize reviewed services and export complete catalogs"
    )
    p.add_argument(
        "--stages",
        nargs="+",
        choices=["early", "middle", "late"],
        default=["early", "middle", "late"],
    )
    p.add_argument("--timeout", type=float, default=30)
    p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("batch", help="Execute an explicit run plan with a resumable ledger")
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--resume", action="store_true")
    for name in ("metadata", "probe"):
        p = sub.add_parser(name)
        p.add_argument("--version", choices=["early", "middle", "late"], required=True)
        p.add_argument("--output", type=Path, required=True)
        if name == "metadata":
            p.add_argument("--task-id", type=int, default=139)
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
    p.add_argument("--config", type=Path, default=Path("configs/full-catalog-smoke.json"))
    knowledge = p.add_mutually_exclusive_group()
    knowledge.add_argument("--knowledge", type=Path)
    knowledge.add_argument("--adaptation", type=Path, help="Validated adaptation.json with costs")
    p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("ecs", help="Compute ECS from a JSON mapping of early/middle/late TF")
    p.add_argument("scores", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "experiment":
            from .experiment import main as experiment_main

            return experiment_main(args.root, args.arguments)
        elif args.command == "report":
            print(
                render_saved_report(
                    args.inputs,
                    format_name=args.format,
                    expanded=args.details,
                    output=args.output,
                ),
                end="",
            )
            return 0
        elif args.command == "adapt":
            if args.evidence_bundle and (
                args.strategy != "selective_patch" or args.selective_mode not in {"hybrid_v5", "hybrid_v6"}
            ):
                raise ValueError("Evidence bundles are only supported in hybrid_v5/hybrid_v6")
            from .capability import load_evidence

            result = write_adaptation(
                args.old_knowledge,
                args.new_metadata,
                args.strategy,
                args.output,
                context={
                    **(
                        {"capability_evidence": load_evidence(args.capability_evidence)}
                        if args.capability_evidence
                        else {}
                    ),
                    **(
                        {"evidence_bundle": str(args.evidence_bundle)}
                        if args.evidence_bundle else {}
                    ),
                    "selective_mode": args.selective_mode,
                    "patch_budget": read_json(args.patch_budget) if args.patch_budget else {},
                    "validation_cases": read_json(args.validation_cases)
                    if args.validation_cases
                    else [],
                    "updater": {
                        **(read_json(args.updater_config) if args.updater_config else {}),
                        "allow_metadata_api": args.allow_metadata_api,
                    },
                },
            )
        elif args.command == "collect-v5-probes":
            from .evidence_v5 import collect_probes

            result = asyncio.run(collect_probes(args.root, args.plan, args.output))
        elif args.command == "run-v5":
            from .execution_v5 import run_v5

            _, result = run_v5(
                args.root,
                args.task_id,
                args.version,
                args.seed,
                args.config,
                args.adaptation,
                args.output,
                args.artifact_protocol,
                args.non_python_deliverable,
            )
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0 if result["status"] == "evaluated" else 2
        elif args.command == "run-v6":
            from .execution_v6 import run_v6

            _, result = run_v6(
                args.root,
                args.task_id,
                args.version,
                args.seed,
                args.config,
                args.adaptation,
                args.output,
                args.artifact_protocol,
                args.non_python_deliverable,
            )
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0 if result["status"] == "evaluated" else 2
        elif args.command == "run-artifact-arm":
            from .artifact_plan import run_arm

            _, result = run_arm(args.plan, args.arm, args.root, args.output)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0 if result["status"] == "evaluated" else 2
        elif args.command == "freeze-artifact-plan":
            from .artifact_plan import freeze

            result = freeze(args.plan, args.output)
        elif args.command == "validate-artifact":
            from .artifact_validation import validate

            result = asyncio.run(
                validate(args.answer.read_text(), read_json(args.protocol), args.output)
            )
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0 if result["accepted_artifact"] else 2
        elif args.command == "bootstrap":
            result = bootstrap(args.root, args.stages, args.scope)
            result = {
                k: {"files": v["files"], "packages": len(v["packages"])} for k, v in result.items()
            }
        elif args.command == "inventory":
            lock, upstream = source(args.root)
            result = build_inventory(upstream, lock, args.root / ".cache/mcpevol")
            write_json(args.output, result)
            result = {"output": str(args.output), **result["summary"]}
        elif args.command == "probe-servers":
            result = asyncio.run(probe_servers(args.root, args.stages, args.output, args.timeout))
            result = {
                "output": str(args.output),
                "checks": len(result["servers"]),
                "verified": sum(r["status"] == "catalog_verified" for r in result["servers"]),
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0 if result["verified"] == result["checks"] else 2
        elif args.command == "batch":
            ledger = run_batch(args.root, args.plan, args.output, args.resume)
            result = {
                "output": str(args.output),
                "runs": len(ledger["runs"]),
                "complete": sum(r["status"] == "complete" for r in ledger["runs"]),
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0 if result["complete"] == result["runs"] else 2
        elif args.command == "metadata":
            result = asyncio.run(metadata(args.root, args.version, args.output, args.task_id))
        elif args.command == "probe":
            result = asyncio.run(probe(args.root, args.version, args.output))
        elif args.command == "doctor":
            result = doctor(args.root)
        elif args.command == "ecs":
            result = ecs(read_json(args.scores))
        else:
            config = read_json(args.config)
            config.update(root=str(args.root), output_dir=str(args.output))
            if args.knowledge:
                config["knowledge_path"] = str(args.knowledge)
                config.pop("adaptation_path", None)
            if args.adaptation:
                config["adaptation_path"] = str(args.adaptation)
            _, result = run(args.task_id, args.version, args.strategy, args.seed, config)
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

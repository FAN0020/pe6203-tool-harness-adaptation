"""Real MCP contract probes, no model calls; save all observations before asserting."""

import argparse
import asyncio
import json
import re
import tempfile
from pathlib import Path

from pe6203.benchmark import read_json, write_json
from pe6203.experiment import STAGES, collect_catalogs, configure_runtime, sha
from pe6203.transport import sessions


async def verify(root, output):
    configure_runtime(root)
    await collect_catalogs(root, [133, 235, 283], output)
    observations = []
    for stage in STAGES:
        with tempfile.TemporaryDirectory(prefix="benchmark-probe-") as tmp:
            workspace = Path(tmp)
            ids = [
                "math-mcp",
                "mcp-ai-agent-guidelines",
                "@umengfe/mcp-server-chart",
                "@modelcontextprotocol/server-sequential-thinking",
                "@pimzino/agentic-tools-mcp",
            ]
            async with sessions(root, stage, ids, workspace, workspace / "stderr.log") as clients:

                async def call(sid, tool, args, expected_error=None):
                    try:
                        result = (
                            await asyncio.wait_for(clients[sid].call_tool(tool, args), 35)
                        ).model_dump(mode="json", exclude_none=True)
                    except RuntimeError as exc:
                        result = {"isError": True, "error": str(exc)}
                    item = {
                        "stage": stage,
                        "server": sid,
                        "tool": tool,
                        "args": args,
                        "result": result,
                        "expected_error": expected_error,
                        "passed": (
                            bool(result.get("isError")) and expected_error in json.dumps(result)
                        )
                        if expected_error
                        else not result.get("isError", False),
                    }
                    observations.append(item)
                    write_json(output / "probes.json", observations)
                    return result

                await call(
                    "math-mcp",
                    "validate_syntax",
                    {"expression": "2+3*4"},
                    "requires allow_variables" if stage == "late" else None,
                )
                if stage == "late":
                    await call(
                        "math-mcp",
                        "validate_syntax",
                        {"expression": "2+3*4", "allow_variables": False},
                    )
                    await call(
                        "math-mcp",
                        "batch_evaluate",
                        {"expressions": ["2+3*4", "(2+3)*4"]},
                        "handleBatchEvaluate is not a function",
                    )
                await call("math-mcp", "evaluate", {"expression": "2+3*4"})
                await call(
                    "mcp-ai-agent-guidelines",
                    "security-hardening-prompt-builder",
                    {
                        "codeContext": "Python mathematical expression evaluator",
                        "securityFocus": "security-hardening",
                        "language": "python",
                        "complianceStandards": ["OWASP-Top-10"],
                    },
                )
                await call(
                    "@umengfe/mcp-server-chart",
                    "generate_column_chart",
                    {"data": [{"category": "Electronics", "value": 6.2}], "group": False},
                )
                await call(
                    "@umengfe/mcp-server-chart",
                    "generate_area_chart",
                    {"data": [{"time": "Jan", "value": 1.2}, {"time": "Feb", "value": 1.1}]},
                )
                await call(
                    "@umengfe/mcp-server-chart",
                    "generate_district_map",
                    {
                        "title": "Sales",
                        "data": {
                            "name": "中国",
                            "dataType": "number",
                            "dataLabel": "Sales",
                            "dataValueUnit": "million RMB",
                            "subdistricts": [{"name": "广东省", "dataValue": "15.8"}],
                        },
                    },
                )
                await call(
                    "@modelcontextprotocol/server-sequential-thinking",
                    "sequentialthinking",
                    {
                        "thought": "Split dashboard work into data ingestion, log processing, and visualization milestones.",
                        "nextThoughtNeeded": False,
                        "thoughtNumber": 1,
                        "totalThoughts": 1,
                    },
                    "getThoughtHistory is not a function" if stage == "late" else None,
                )
                if stage != "early":
                    await call(
                        "@modelcontextprotocol/server-sequential-thinking",
                        "parallel-thinking",
                        {
                            "pathId": "dashboard",
                            "thought": "Evaluate the data-processing workstream.",
                            "pathNumber": 1,
                            "totalPaths": 1,
                            "thoughtInPath": 1,
                            "pathStatus": "completed",
                            "readyForSynthesis": True,
                        },
                        "Additional properties are not allowed",
                    )
                sid = "@pimzino/agentic-tools-mcp"
                project = await call(
                    sid,
                    "create_project",
                    {
                        "workingDirectory": tmp,
                        "name": "Benchmark probe",
                        "description": "Temporary isolated project for runtime verification",
                    },
                )
                pid = re.search(r"ID: ([0-9a-f-]{36})", project["content"][0]["text"]).group(1)
                await call(
                    sid,
                    "create_task",
                    {
                        "workingDirectory": tmp,
                        "projectId": pid,
                        "name": "Parse data",
                        "details": "Validate CSV columns and record parse errors",
                        "complexity": 3,
                    },
                )
                await call(
                    sid,
                    "analyze_task_complexity",
                    {"workingDirectory": tmp, "projectId": pid, "autoCreateSubtasks": False},
                )
        print(f"{stage}: observations recorded", flush=True)
    write_json(
        output / "verification.json",
        {
            "kind": "real_mcp_contract_probes_not_model_scores",
            "observations": len(observations),
            "all_passed": all(x["passed"] for x in observations),
            "observed_errors": sum(bool(x["result"].get("isError")) for x in observations),
            "catalog_sha256": {
                str(p.relative_to(output)): sha(p)
                for p in sorted((output / "catalogs").rglob("*.json"))
            },
            "probes_sha256": sha(output / "probes.json"),
        },
    )
    result = read_json(output / "verification.json")
    if not result["all_passed"]:
        raise ValueError(f"Unexpected contract behavior; see {output / 'probes.json'}")
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    print(
        json.dumps(
            asyncio.run(verify(Path(__file__).resolve().parents[1], args.output.resolve())),
            indent=2,
        )
    )

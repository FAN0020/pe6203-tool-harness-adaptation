"""Public V5 CLI update + SDK agent loop + real optional Docker, no paid model.

All model responses are explicit local HTTP fixtures. The generic normalize
tests are unrelated to MCPEvol task answers. This is implementation acceptance,
not Evol evaluation, source authentication or proof of semantic entailment.
"""

import argparse
import asyncio
import hashlib
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from openai import AsyncOpenAI

from pe6203.artifact_validation import DockerBackend, settings
from pe6203.benchmark import read_json, write_json
from pe6203.runner import agent_loop, prepare_tools

GOOD = "def normalize(value):\n if not isinstance(value, str): raise TypeError('string required')\n return value.strip().lower()\n"
BAD = "def normalize(value):\n return value.strip()\n"


def updater_reply(payload):
    ids = [
        key
        for key, value in payload["evidence_registry"].items()
        if value["kind"] == "catalog"
        and value["side"] == "target"
        and value["field"] == "description"
        and value["tool_id"] in {"server::display", "server::fetch_balance"}
    ]
    if "candidates" in payload:
        return {
            "decisions": [
                {
                    "tool_id": row["tool_id"],
                    "action": "update" if row["tool_id"] == "server::display" else "keep",
                    "reason": "Synthetic units change"
                    if row["tool_id"] == "server::display"
                    else "Unrelated rule",
                    "basis": ["c1"] if row["tool_id"] == "server::display" else [],
                    "evidence_ids": ids if row["tool_id"] == "server::display" else [],
                }
                for row in payload["candidates"]
            ]
        }
    return {
        "patches": [
            {
                "tool_id": "server::display",
                "retain_rule_indices": [],
                "rules": [
                    {
                        "kind": "guidance",
                        "text": "Convert cents to dollars before display.",
                        "evidence_ids": ids,
                    }
                ],
                "basis": ["c1"],
                "evidence_ids": ids,
                "reason": "Withdraw obsolete direct conversion rule",
            }
        ]
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--image", help="Reviewed, already local Python image pinned by digest")
    args = parser.parse_args()
    root, output = Path(__file__).resolve().parents[1], args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    protocol = read_json(root / "examples/qi-v5/artifact-protocol.json")
    if args.image:
        protocol["image"] = args.image
    protocol = settings(protocol)
    write_json(output / "protocol-before-generation.json", protocol)
    actual_backend = DockerBackend(protocol).available()
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(body)
            if len(requests) > 4:
                self.send_error(429)
                return
            try:
                payload = json.loads(body["messages"][-1]["content"])
            except ValueError:
                payload = {}
            if "evidence_registry" in payload:
                content = json.dumps(updater_reply(payload))
            else:
                source = GOOD if "attempt" in payload else BAD if actual_backend else "def broken(:"
                content = json.dumps(
                    {
                        "artifact": {"path": "artifact.py", "language": "python", "source": source},
                        "summary": "Synthetic normalization function; finite tests only.",
                    }
                )
            wire = json.dumps(
                {
                    "id": "scripted-local-fixture",
                    "object": "chat.completion",
                    "created": 1,
                    "model": "SCRIPTED-NOT-LLM",
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": "stop",
                            "message": {"role": "assistant", "content": content},
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 10,
                        "completion_tokens": 5,
                        "total_tokens": 15,
                        "cost": 0.0,
                    },
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(wire)))
            self.end_headers()
            self.wfile.write(wire)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}/v1"
    env = {**os.environ, "V5_FIXTURE_API_KEY": "LOCAL-TEST-ONLY", "V5_FIXTURE_BASE_URL": base_url}
    write_json(
        output / "updater-config.json",
        {
            "api_key_env": "V5_FIXTURE_API_KEY",
            "base_url_env": "V5_FIXTURE_BASE_URL",
            "model": "SCRIPTED-NOT-LLM",
            "timeout": 10,
        },
    )
    events = []
    try:
        command = [
            sys.executable,
            "-m",
            "pe6203.cli",
            "adapt",
            "--strategy",
            "selective_patch",
            "--selective-mode",
            "hybrid_v5",
            "--old-knowledge",
            str(root / "examples/qi-v2/early.json"),
            "--new-metadata",
            str(root / "examples/qi-v2/late.json"),
            "--updater-config",
            str(output / "updater-config.json"),
            "--allow-metadata-api",
            "--output",
            str(output / "adaptation"),
        ]
        process = subprocess.run(
            command, cwd=root, env=env, capture_output=True, text=True, timeout=25
        )
        (output / "updater.stdout.txt").write_text(process.stdout)
        if process.returncode:
            raise RuntimeError("Public V5 CLI failed; inspect retained adaptation audit")
        knowledge = read_json(output / "adaptation/knowledge.json")
        tools, routes = prepare_tools(knowledge["tools"], "selective_patch")
        workspace = output / "workspace"
        workspace.mkdir()

        async def execute():
            async with AsyncOpenAI(
                api_key="LOCAL-TEST-ONLY", base_url=base_url, max_retries=0, timeout=10
            ) as client:
                return await agent_loop(
                    client,
                    {},
                    tools,
                    routes,
                    "Write normalize(value): strip and lower strings, reject other types.",
                    workspace,
                    {
                        "max_rounds": 1,
                        "agent": {
                            "model": "SCRIPTED-NOT-LLM",
                            "temperature": 0,
                            "max_completion_tokens": 256,
                        },
                        "artifact_validation": protocol,
                    },
                    0,
                    events.append,
                )

        outcome = asyncio.run(execute())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        write_json(output / "scripted-api-requests.json", requests)
        write_json(output / "events.json", events)
    write_json(output / "outcome.json", outcome)
    audit = outcome["artifact_validation"]
    adaptation = read_json(output / "adaptation/adaptation.json")
    checks = {
        "public_v5_update_with_two_scripted_requests": adaptation["pipeline_version"] == "hybrid_v5"
        and adaptation["cost"]["calls"] == 2,
        "four_local_sdk_requests_total": len(requests) == 4,
        "obsolete_rule_withdrawn": "without conversion"
        not in json.dumps(knowledge["tools"][1]["usage_rules"]),
        "new_guidance_is_explicitly_unverified": knowledge["tools"][1]["usage_rules"][0].startswith(
            "Unverified LLM guidance"
        ),
        "actual_failure_reaches_repair": json.loads(requests[-1]["messages"][-1]["content"])[
            "attempt"
        ]["status"]
        == ("test_failed" if actual_backend else "syntax_failed"),
        "repaired_source_revalidated": len(audit["attempts"]) == 2
        and audit["attempts"][1]["static_status"] == "passed",
        "expected_honest_final_status": audit["status"]
        == ("passed_finite_tests" if actual_backend else "backend_unavailable"),
        "exact_repaired_hash": audit["latest_artifact"]["sha256"]
        == hashlib.sha256(GOOD.encode()).hexdigest(),
        "actor_usage_includes_repair": outcome["usage"]["total_tokens"] == 30,
    }
    result = {
        "status": "passed"
        if all(checks.values()) and actual_backend
        else "passed_checks_isolation_gap"
        if all(checks.values())
        else "failed",
        "checks": checks,
        "actual_isolated_execution": actual_backend,
        "real_llm_calls": 0,
        "benchmark_run": False,
        "actual_archived_mcp_probes_run": False,
        "scope": "Synthetic implementation acceptance, not benchmark effectiveness or semantic truth",
    }
    write_json(output / "acceptance.json", result)
    print(json.dumps(result, indent=2))
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())

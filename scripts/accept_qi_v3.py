"""QI-V3 acceptance with a SCRIPTED LOCAL HTTP endpoint, not a real LLM.

Public CLI updater + public runner agent_loop + actual configured Docker backend.
Without Docker, syntax failure -> scripted repair -> static pass -> unavailable is
recorded honestly. No generated code is ever executed on the host.
"""

import argparse
import asyncio
import hashlib
import json
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


def answer(source):
    return json.dumps(
        {
            "artifact": {"path": "artifact.py", "language": "python", "source": source},
            "summary": "Synthetic normalization function; finite tests only.",
        }
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--image", help="Already installed/reviewed Python image@sha256:...; no pulls"
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    command = [
        sys.executable,
        "-m",
        "pe6203.cli",
        "adapt",
        "--strategy",
        "selective_patch",
        "--selective-mode",
        "hybrid_v3",
        "--old-knowledge",
        str(root / "examples/qi-v3/catalog.json"),
        "--new-metadata",
        str(root / "examples/qi-v3/catalog.json"),
        "--capability-evidence",
        str(root / "examples/qi-v3/evidence.json"),
        "--output",
        str(output / "adaptation"),
    ]
    updater = subprocess.run(command, capture_output=True, text=True, timeout=15)
    (output / "updater.stdout.txt").write_text(updater.stdout)
    if updater.returncode:
        raise RuntimeError("Public V3 updater CLI failed")
    config = read_json(root / "examples/qi-v3/artifact-protocol.json")
    if args.image:
        config["image"] = args.image
    config = settings(config)
    write_json(output / "protocol-before-generation.json", config)
    actual_backend = DockerBackend(config).available()
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(body)
            if len(requests) > 2:
                self.send_error(429)
                return
            source = GOOD if len(requests) == 2 else BAD if actual_backend else "def broken(:"
            payload = json.dumps(
                {
                    "id": "scripted-local-fixture",
                    "object": "chat.completion",
                    "created": 1,
                    "model": "SCRIPTED-NOT-LLM",
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": "stop",
                            "message": {"role": "assistant", "content": answer(source)},
                        }
                    ],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    knowledge = read_json(output / "adaptation/knowledge.json")
    tools, routes = prepare_tools(knowledge["tools"], "selective_patch")
    workspace = output / "workspace"
    workspace.mkdir()
    events = []

    async def execute():
        async with AsyncOpenAI(
            api_key="LOCAL-TEST-ONLY",
            base_url=f"http://127.0.0.1:{server.server_port}/v1",
            max_retries=0,
            timeout=10,
        ) as client:
            return await agent_loop(
                client,
                {},
                tools,
                routes,
                "Write normalize(value): string strip and lower; reject other types.",
                workspace,
                {
                    "agent": {
                        "model": "SCRIPTED-NOT-LLM",
                        "temperature": 0,
                        "max_completion_tokens": 256,
                    },
                    "max_rounds": 1,
                    "artifact_validation": config,
                },
                0,
                events.append,
            )

    try:
        outcome = asyncio.run(execute())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    write_json(output / "scripted-api-requests.json", requests)
    write_json(output / "events.json", events)
    write_json(output / "outcome.json", outcome)
    audit = outcome["artifact_validation"]
    expected = "passed_finite_tests" if actual_backend else "backend_unavailable"
    checks = {
        "public_v3_updater": True,
        "two_sdk_http_requests": len(requests) == 2,
        "failure_reaches_repair_model_request": json.loads(requests[1]["messages"][-1]["content"])[
            "attempt"
        ]["status"]
        == ("test_failed" if actual_backend else "syntax_failed"),
        "repaired_source_revalidated": len(audit["attempts"]) == 2
        and audit["attempts"][1]["static_status"] == "passed",
        "expected_honest_final_status": audit["status"] == expected,
        "repaired_exact_hash": audit["latest_artifact"]["sha256"]
        == hashlib.sha256(GOOD.encode()).hexdigest(),
        "usage_includes_both_requests": outcome["usage"]["total_tokens"] == 30,
    }
    acceptance = {
        "scope": "Implementation acceptance; no benchmark effectiveness claim",
        "status": "passed_checks_isolation_gap"
        if all(checks.values()) and not actual_backend
        else "passed"
        if all(checks.values())
        else "failed",
        "checks": checks,
        "actual_isolated_execution": actual_backend,
        "final_artifact_status": audit["status"],
        "real_llm_calls": 0,
        "model_evidence": "scripted local HTTP API test server; not a model",
        "updater_model_calls": 0,
        "benchmark_run": False,
    }
    write_json(output / "acceptance.json", acceptance)
    print(json.dumps(acceptance, indent=2))
    return 0 if all(checks.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())

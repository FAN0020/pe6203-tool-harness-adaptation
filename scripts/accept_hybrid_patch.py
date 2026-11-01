"""Bounded QI-V2 CLI acceptance: explicit local API double or real LLM smoke.

No benchmark task, judge or MCP service is run. --live is an explicit opt-in to
at most two updater requests using only the synthetic examples/qi-v2 catalogs.
Every attempt uses a fresh output directory and retains both successes/failures.
"""

import argparse
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def fake_reply(payload):
    """Scripted test response; not a model and not evidence of reasoning quality."""
    evidence = [
        {
            "tool_id": "server::fetch_balance",
            "side": "target",
            "field": "description",
            "quote": "Returns the account balance for the display panel in cents.",
        },
        {
            "tool_id": "server::display",
            "side": "old",
            "field": "usage_rules",
            "quote": "Pass the balance service result directly as amount without conversion.",
        },
    ]
    if "candidates" in payload:
        return {
            "decisions": [
                {
                    "tool_id": c["tool_id"],
                    "action": "update" if c["tool_id"] == "server::display" else "keep",
                    "reason": "Unit conversion needed"
                    if c["tool_id"] == "server::display"
                    else "Rule unchanged",
                    "basis": ["c1"] if c["tool_id"] == "server::display" else [],
                    "evidence": evidence if c["tool_id"] == "server::display" else [],
                }
                for c in payload["candidates"]
            ]
        }
    return {
        "patches": [
            {
                "tool_id": "server::display",
                "usage_rules": [
                    "Convert the supplied amount from cents to dollars by dividing by 100 before display."
                ],
                "reason": "Amount source changed units",
                "basis": ["c1"],
                "evidence": evidence,
                "unresolved": False,
            }
        ]
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live", action="store_true", help="Use real OpenRouter updater; max two calls"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ)
    requests = []
    server = thread = None
    if args.live:
        if not env.get("OPENROUTER_API_KEY"):
            raise SystemExit("Configure OPENROUTER_API_KEY; no provider request was sent")
        settings = {
            "model": "deepseek/deepseek-v4.1-flash-1017",
            "temperature": 0.0,
            "max_tokens": 4096,
            "timeout": 55,
            "api_key_env": "OPENROUTER_API_KEY",
            "base_url_env": "QI_V2_ACCEPTANCE_BASE_URL",
        }
        env["QI_V2_ACCEPTANCE_BASE_URL"] = "https://openrouter.ai/api/v1"
    else:

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_POST(self):
                data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                requests.append(data)
                payload = json.loads(data["messages"][-1]["content"])
                response = {
                    "id": "synthetic-acceptance",
                    "object": "chat.completion",
                    "created": 0,
                    "model": "explicit-local-api-double",
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": "stop",
                            "message": {
                                "role": "assistant",
                                "content": json.dumps(fake_reply(payload)),
                            },
                        }
                    ],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
                }
                body = json.dumps(response).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        env["QI_V2_ACCEPTANCE_API_KEY"] = "TEST-ONLY-NOT-A-REAL-KEY"
        env["QI_V2_ACCEPTANCE_BASE_URL"] = f"http://127.0.0.1:{server.server_port}/v1"
        settings = {
            "model": "explicit-local-api-double",
            "temperature": 0.0,
            "max_tokens": 4096,
            "timeout": 10,
            "api_key_env": "QI_V2_ACCEPTANCE_API_KEY",
            "base_url_env": "QI_V2_ACCEPTANCE_BASE_URL",
        }
    (output / "settings.json").write_text(json.dumps(settings, indent=2) + "\n")
    (output / "budget.json").write_text(json.dumps({"max_calls": 2, "max_seconds": 120}) + "\n")
    command = [
        sys.executable,
        "-m",
        "pe6203.cli",
        "adapt",
        "--strategy",
        "selective_patch",
        "--old-knowledge",
        str(root / "examples/qi-v2/early.json"),
        "--new-metadata",
        str(root / "examples/qi-v2/late.json"),
        "--output",
        str(output / "adaptation"),
        "--updater-config",
        str(output / "settings.json"),
        "--patch-budget",
        str(output / "budget.json"),
        "--validation-cases",
        str(root / "examples/qi-v2/validation-cases.json"),
        "--allow-metadata-api",
    ]
    try:
        run = subprocess.run(
            command, cwd=root, env=env, capture_output=True, text=True, timeout=135
        )
    finally:
        if server:
            server.shutdown()
            server.server_close()
            thread.join()
    (output / "cli.stdout.txt").write_text(run.stdout)
    (output / "cli.stderr.txt").write_text(run.stderr)
    artifact_path = output / "adaptation/adaptation.json"
    artifact = json.loads(artifact_path.read_text()) if artifact_path.exists() else {}
    audit_path = output / "adaptation/updater-audit.json"
    audit = json.loads(audit_path.read_text()) if audit_path.exists() else {}
    old = json.loads((root / "examples/qi-v2/early.json").read_text())
    checks = {
        "cli_succeeded": run.returncode == 0,
        "pipeline_is_hybrid_v2": artifact.get("pipeline_version") == "hybrid_v2",
        "four_stages_passed": [s.get("status") for s in audit.get("stages", [])] == ["passed"] * 4,
        "full_catalog_review": set(audit.get("reviewed_tool_ids", []))
        == {t["tool_id"] for t in old["tools"]},
        "implicit_dependency_found": "server::display" in audit.get("semantic_impacted", [])
        and "server::display" not in audit.get("deterministic_impacted", []),
        "argument_regressions_passed": len(audit.get("validation", {}).get("argument_cases", []))
        == 3
        and all(c["passed"] for c in audit.get("validation", {}).get("argument_cases", [])),
        "bounded_calls": 0 < artifact.get("cost", {}).get("calls", 0) <= 2,
    }
    knowledge_path = output / "adaptation/knowledge.json"
    if knowledge_path.exists():
        knowledge = json.loads(knowledge_path.read_text())
        checks["unrelated_record_preserved"] = knowledge["tools"][2] == old["tools"][2]
    else:
        checks["unrelated_record_preserved"] = False
    report = {
        "kind": "live_llm_synthetic_smoke" if args.live else "local_api_double_acceptance",
        "benchmark_performance_evidence": False,
        "real_mcp_execution": False,
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "cost": artifact.get("cost"),
        "stages": audit.get("stages"),
        "response_models": sorted(
            {
                a["response"].get("model", "unknown")
                for a in audit.get("attempts", [])
                if "response" in a
            }
        ),
        "limits": {"max_calls": 2, "max_seconds": 120},
        "behavioral_generalization": "not_established",
    }
    (output / "acceptance.json").write_text(json.dumps(report, indent=2) + "\n")
    if requests:
        (output / "local-api-requests.json").write_text(json.dumps(requests, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

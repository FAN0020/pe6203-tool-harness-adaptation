"""Full adapter wiring with REAL MCP and an explicitly fake model HTTP service.

These scores are protocol fixtures, never benchmark measurements.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from pe6203.benchmark import read_json
from pe6203.runner import run

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.integration
@pytest.mark.parametrize("provider_fails", [False, True])
def test_full_adapter_wiring_real_mcp_with_model_protocol_fixture(
    tmp_path, monkeypatch, provider_fails
):
    if not (ROOT / ".cache/mcpevol/original/extraction.json").exists():
        pytest.skip("Requires released MCP services")
    node = ROOT / ".cache/node-runtime/node_modules/node/bin/node"
    if node.exists():
        monkeypatch.setenv("MCPEVOL_NODE", str(node))
    output = tmp_path / "protocol-fixture"
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests.append(body)
            if provider_fails:
                self.send_response(503)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":{"message":"protocol fixture outage"}}')
                return
            if "tools" in body and len(requests) == 1:
                message = {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "fixture-call",
                            "type": "function",
                            "function": {
                                "name": "create_project",
                                "arguments": json.dumps(
                                    {
                                        "workingDirectory": str(output / "workspace"),
                                        "name": "Protocol fixture",
                                        "description": "Not a benchmark result",
                                    }
                                ),
                            },
                        }
                    ],
                }
            elif "tools" in body:
                message = {"role": "assistant", "content": "Protocol fixture completed"}
            else:
                message = {
                    "role": "assistant",
                    "content": json.dumps(
                        {"task_fulfillment": 2, "grounding": 3, "planning_and_efficiency": 4}
                    ),
                }
            payload = {
                "id": "fixture",
                "object": "chat.completion",
                "created": 1,
                "model": "protocol-fixture",
                "choices": [
                    {
                        "index": 0,
                        "message": message,
                        "finish_reason": "tool_calls" if message.get("tool_calls") else "stop",
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12},
            }
            response = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("AGENT_API_KEY", "TEST-ONLY-SECRET")
    monkeypatch.setenv("JUDGE_API_KEY", "TEST-ONLY-SECRET")
    endpoint = f"http://127.0.0.1:{server.server_port}/v1"
    monkeypatch.setenv("AGENT_BASE_URL", endpoint)
    monkeypatch.setenv("JUDGE_BASE_URL", endpoint)
    config = read_json(ROOT / "configs/smoke.json")
    config.update(root=str(ROOT), output_dir=str(output), judge_runs=2)
    try:
        trace, result = run(139, "early", "no_update", 42, config)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    if provider_fails:
        assert result["status"] == "blocked"
        assert result["execution_status"] == "failed"
        assert result["TF"] is None and result["PE"] is None
        assert result["judge_status"] == "not_started"
        assert len(requests) == 1
        assert any(e["type"] == "initial_messages" for e in trace["events"])
        assert read_json(output / "result.json")["errors"]
        return
    assert result["status"] == "evaluated", result["errors"]
    assert result["execution_status"] == "completed"
    assert result["TF"] == 2 and result["PE"] == 4 and result["ECS"] is None
    assert result["cost"]["agent"]["total_tokens"] == 24
    assert result["cost"]["judge"]["total_tokens"] == 24
    assert (output / "workspace/.agentic-tools-mcp/tasks/tasks.json").exists()
    assert len(trace["trajectory_messages"]) == 5
    assert len(requests) == 4
    assert read_json(output / "EVAL/139.json")["eval_result"]["aggregate"]["complete"]
    assert "TEST-ONLY-SECRET" not in (output / "raw_trace.json").read_text()
    assert (output / "judge-prompt-1.txt").exists()

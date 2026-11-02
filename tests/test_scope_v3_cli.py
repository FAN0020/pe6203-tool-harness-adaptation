"""Actual V3 CLI through a scripted local API; no paid model or benchmark."""

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from scripts.measure_v3_scope import NEW_RULE, catalogs, scripted


def test_public_cli_changed_metadata_uses_compact_v3_and_literal_boundaries(tmp_path):
    old, target, evidence = catalogs(3)
    for name, value in [("old", old), ("target", target), ("evidence", evidence)]:
        (tmp_path / f"{name}.json").write_text(json.dumps(value))
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            payload = json.loads(data["messages"][-1]["content"])
            requests.append(payload)
            body = json.dumps(
                {
                    "id": "SCRIPTED-LOCAL-NOT-LLM",
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": "stop",
                            "message": {
                                "role": "assistant",
                                "content": json.dumps(scripted(payload)),
                            },
                        }
                    ],
                    "usage": {"prompt_tokens": 8, "completion_tokens": 9, "cost": 0},
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    config = {
        "model": "SCRIPTED-LOCAL-NOT-LLM",
        "max_tokens": 2048,
        "timeout": 10,
        "temperature": 0,
        "api_key_env": "V3_SCOPE_TEST_KEY",
        "base_url_env": "V3_SCOPE_TEST_BASE",
    }
    (tmp_path / "updater.json").write_text(json.dumps(config))
    env = {
        **os.environ,
        "V3_SCOPE_TEST_KEY": "LOCAL-TEST-ONLY",
        "V3_SCOPE_TEST_BASE": f"http://127.0.0.1:{server.server_port}/v1",
    }
    try:
        process = subprocess.run(
            [
                sys.executable,
                "-m",
                "pe6203.cli",
                "adapt",
                "--strategy",
                "selective_patch",
                "--selective-mode",
                "hybrid_v3",
                "--old-knowledge",
                str(tmp_path / "old.json"),
                "--new-metadata",
                str(tmp_path / "target.json"),
                "--capability-evidence",
                str(tmp_path / "evidence.json"),
                "--updater-config",
                str(tmp_path / "updater.json"),
                "--allow-metadata-api",
                "--output",
                str(tmp_path / "adaptation"),
            ],
            cwd=Path(__file__).parents[1],
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    assert process.returncode == 0, process.stderr
    artifact = json.loads((tmp_path / "adaptation/adaptation.json").read_text())
    knowledge = json.loads((tmp_path / "adaptation/knowledge.json").read_text())
    assert artifact["scope_policy"] == "program_first_light_screen_local_review_v1"
    assert artifact["updater_core_version"] == "hybrid_v3_program_first_v1"
    assert [r["phase"] for r in requests] == ["scope_screen", "local_semantic_review"]
    assert knowledge["tools"][1]["usage_rules"] == [NEW_RULE]
    assert all(
        t["capability_boundary"]["status"] == "literal_evidence_only" for t in knowledge["tools"]
    )

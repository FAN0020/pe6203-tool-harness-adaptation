"""Frozen 36-cell evaluation with a uniform, audited provider-pinning relay.

Authorization headers/keys are never persisted. The relay forwards only to the
official OpenRouter completion endpoint. It changes no strategy logic. Both
versions use the same relay policy, original rubric and shared task inputs.
"""

import hashlib
import hmac
import json
import subprocess
import threading
import time
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
from dotenv import dotenv_values

HERE = Path(__file__).resolve().parent
V5 = Path("/Users/q/Desktop/tool-selective_patch/V5")
V3 = Path("/Users/q/Desktop/tool-selective_patch/V3")
KEY = dotenv_values(V5 / ".env.v5")["V5_API_KEY"]
PLAN = json.loads((HERE / "frozen-plan.json").read_text())
LOCK = threading.Lock()
ACTIVE = {"cell": "initializing"}
LEDGER = []


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, ensure_ascii=False, indent=2).replace(KEY, "<redacted>") + "\n"
    temp = path.with_suffix(path.suffix + ".writing")
    temp.write_text(raw)
    temp.replace(path)


def verify():
    for path, expected in PLAN["files"].items():
        if sha(HERE / path) != expected:
            raise ValueError("Frozen input changed: " + path)
    for arm, root in [("V5", V5), ("V3", V3)]:
        actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
        if actual != PLAN["method_commits"][arm]:
            raise ValueError("Method commit changed: " + arm)
        for path, expected in PLAN["source_files"][arm].items():
            if sha(root / path) != expected:
                raise ValueError("Frozen method source changed: " + arm + "/" + path)


def phase(body):
    messages = body.get("messages", [])
    if messages and messages[0].get("role") != "system":
        return "judge"
    try:
        payload = json.loads(messages[-1].get("content", "")) if messages[-1].get("role") == "user" else {}
    except (ValueError, TypeError, IndexError):
        payload = {}
    if isinstance(payload, dict):
        if (
            "evidence_registry" in payload
            or ("changes" in payload and ("candidates" in payload or "selected" in payload))
            or "rewrite_checks" in payload
        ):
            return "updater"
        if "attempt" in payload and "source" in payload:
            return "repair"
    return "agent"


class Relay(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_POST(self):
        if self.path != "/v1/chat/completions" or not hmac.compare_digest(
            self.headers.get("Authorization", ""), "Bearer " + KEY
        ):
            self.send_error(403)
            return
        size = int(self.headers.get("Content-Length", 0))
        if not 0 < size <= 15_000_000:
            self.send_error(413)
            return
        body = json.loads(self.rfile.read(size))
        if body.get("model") != PLAN["model"] or body.get("stream"):
            self.send_error(400)
            return
        # The historical updater recognizes OpenRouter by hostname. Restore its
        # intended reasoning-disabled option after introducing localhost relay.
        if body.pop("thinking", None) is not None:
            body["reasoning"] = {"enabled": False}
        body["provider"] = PLAN["provider"]
        with LOCK:
            known = sum((r.get("response", {}).get("usage") or {}).get("cost") or 0 for r in LEDGER)
            if (
                len(LEDGER) >= PLAN["maximum_forwarded_requests"]
                or known >= PLAN["spend_guard_usd"]
            ):
                self.send_error(402, "Experiment spending/request guard reached")
                return
            number = len(LEDGER) + 1
            record = {
                "index": number,
                "cell": ACTIVE["cell"],
                "phase": phase(body),
                "started_at": datetime.now(UTC).isoformat(),
                "request": body,
                "status": "started",
            }
            LEDGER.append(record)
        dest = HERE / "transport" / f"request-{number:04d}.json"
        save(dest, record)
        started = time.monotonic()
        headers = {}
        try:
            with httpx.Client(timeout=125, trust_env=False, follow_redirects=False) as client:
                response = client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"},
                    json=body,
                )
            status, wire = response.status_code, response.content
            try:
                parsed = response.json()
            except ValueError:
                parsed = {"unparsed_response_sha256": hashlib.sha256(wire).hexdigest()}
            record.update(
                status="received",
                http_status=status,
                response=parsed,
                seconds=time.monotonic() - started,
            )
            if status == 200 and parsed.get("provider") != "Relace":
                record["provider_contract_violation"] = True
            if "retry-after" in response.headers:
                headers["Retry-After"] = response.headers["retry-after"]
        except Exception as exc:
            status, parsed = (
                502,
                {
                    "error": {
                        "message": "Audited relay transport failed",
                        "type": type(exc).__name__,
                    }
                },
            )
            wire = json.dumps(parsed).encode()
            record.update(
                status="transport_error",
                http_status=status,
                error_type=type(exc).__name__,
                seconds=time.monotonic() - started,
            )
        save(dest, record)
        # Never persist request headers or authentication material.
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(wire)))
            for key, value in headers.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(wire)
        except (BrokenPipeError, ConnectionResetError):
            record["downstream_disconnected"] = True
            save(dest, record)


def main():
    verify()
    server = ThreadingHTTPServer(("127.0.0.1", 0), Relay)
    server.daemon_threads = True
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    endpoint = f"http://127.0.0.1:{server.server_port}/v1"
    save(
        HERE / "transport-policy.json",
        {
            "endpoint": endpoint,
            "upstream": "https://openrouter.ai/api/v1",
            "provider": PLAN["provider"],
            "thinking_normalization": "restore historical OpenRouter updater reasoning disabled",
            "authorization_headers_persisted": False,
            "driver_sha256": sha(__file__),
            "child_sha256": sha(HERE / "run_cell.py"),
        },
    )
    completed = []
    try:
        for arm in PLAN["order"]:
            root = V3 if arm == "V3" else V5
            for stage in PLAN["stages"]:
                for task in PLAN["tasks"]:
                    if (HERE / "STOP_AFTER_CELL").exists():
                        raise RuntimeError("Requested stop after completed cell; all previous records retained")
                    verify()
                    name = f"{arm}/task{task}-{stage}-r0"
                    ACTIVE["cell"] = name
                    print(
                        json.dumps(
                            {
                                "event": "cell_started",
                                "cell": name,
                                "completed": len(completed),
                                "planned": 36,
                            }
                        ),
                        flush=True,
                    )
                    command = [
                        "uv",
                        "run",
                        "python",
                        str(HERE / "run_cell.py"),
                        "--plan",
                        str(HERE / "frozen-plan.json"),
                        "--arm",
                        arm,
                        "--task",
                        str(task),
                        "--stage",
                        stage,
                        "--endpoint",
                        endpoint,
                    ]
                    process = subprocess.run(
                        command, cwd=root, capture_output=True, text=True, timeout=1300
                    )
                    log = HERE / "logs" / (name.replace("/", "-") + ".txt")
                    log.parent.mkdir(exist_ok=True)
                    log.write_text(
                        (process.stdout + "\n" + process.stderr).replace(KEY, "<redacted>")
                    )
                    cell_path = HERE / "cells" / arm / f"task{task}-{stage}-r0" / "cell.json"
                    cell = (
                        json.loads(cell_path.read_text())
                        if cell_path.exists()
                        else {"status": "process_failed"}
                    )
                    cell["process_returncode"] = process.returncode
                    completed.append(cell)
                    save(
                        HERE / "progress.json",
                        {
                            "completed": len(completed),
                            "planned": 36,
                            "current": name,
                            "cells": completed,
                        },
                    )
                    print(
                        json.dumps({"event": "cell_finished", **cell}, ensure_ascii=False),
                        flush=True,
                    )
                    if process.returncode or any(
                        r.get("provider_contract_violation") for r in LEDGER
                    ):
                        raise RuntimeError("Process/provider contract failure; preserve all data")
                    records = [r for r in LEDGER if r["cell"] == name]
                    transport_only = records and not any(
                        r.get("http_status") == 200 for r in records
                    )
                    if transport_only:
                        raise RuntimeError(
                            "Model transport unavailable; no strategy or trajectory fallback"
                        )
        save(
            HERE / "completed.json",
            {
                "status": "complete",
                "cells": len(completed),
                "planned": 36,
                "real_model_requests": len(LEDGER),
            },
        )
    except BaseException as exc:
        save(
            HERE / "stopped.json",
            {
                "status": "stopped",
                "error_type": type(exc).__name__,
                "reason": str(exc),
                "completed_cells": len(completed),
                "no_silent_fallback": True,
            },
        )
        raise
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
        save(HERE / "transport-ledger.json", LEDGER)


if __name__ == "__main__":
    main()

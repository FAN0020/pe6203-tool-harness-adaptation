"""Gated, audited V6 pilot then eight remaining frozen cells.

All requests use one pinned official endpoint. Authentication is loaded from a
local ignored env file, never persisted. No score-driven acceptance changes.
Run with --plan frozen-plan.json --env-file LOCAL_SECRET_FILE.
"""

import argparse
import hashlib
import hmac
import json
import os
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
from dotenv import dotenv_values

from pe6203.baselines import write_adaptation
from pe6203.benchmark import digest, read_json, write_json
from pe6203.execution_v6 import run_v6
from pe6203.payload_v6 import measure


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(plan, home, root):
    for path, expected in plan["files"].items():
        if sha(home / path) != expected:
            raise ValueError("Frozen input changed: " + path)
    for path, expected in plan["source_files"].items():
        if sha(root / path) != expected:
            raise ValueError("Frozen implementation changed: " + path)
    if digest(plan["acceptance"]) != plan["acceptance_sha256"]:
        raise ValueError("Acceptance plan hash mismatch")


def child(args, plan, home):
    import shutil
    for role in ("AGENT", "JUDGE"):
        os.environ[role + "_BASE_URL"] = args.endpoint
    key = dotenv_values(args.env_file)["V5_API_KEY"]
    os.environ["AGENT_API_KEY"] = os.environ["JUDGE_API_KEY"] = key
    task, stage = args.cell.split("/")
    task = int(task)
    if task != 133 or stage != "middle":
        raise ValueError("This preregistered repeat permits only task133/middle")
    cell = home / "cells" / "task133-middle-r0"
    cell.mkdir(parents=True, exist_ok=False)
    shutil.copytree(home / "inputs/original-adaptation", cell / "adaptation")
    shutil.copy2(home / "inputs/frozen-execution-config.json", cell / "execution-config.json")
    write_json(cell / "reuse-provenance.json", {
        "knowledge_and_adaptation_copied_byte_identically": True,
        "new_updater_calls": 0,
        "native_result_update_cost_is_previous_one_time_cost_not_a_new_charge": True,
        "original_update_usd": plan["repeat_policy"]["reused_update_usd"],
    })
    status = {"task_id": task, "stage": stage, "status": "started", "actor_repeat": 1,
              "adaptation_reused": True, "new_updater_calls": 0}
    try:
        _, result = run_v6(Path.cwd(), task, stage, 0, cell / "execution-config.json",
                           cell / "adaptation/adaptation.json", cell / "run",
                           home / "inputs/python-protocol.json", non_python_deliverable=False)
        status.update(status=result["status"], execution_status=result["execution_status"],
                      judge_status=result["judge_status"], TF=result["TF"], PE=result["PE"])
    except Exception as exc:
        status.update(status="cell_error", error_type=type(exc).__name__)
        if isinstance(exc, ValueError):
            status["error"] = str(exc).replace(key, "<redacted>")
    finally:
        write_json(cell / "cell.json", status)
    print(json.dumps(status), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--cell")
    parser.add_argument("--endpoint")
    args = parser.parse_args()
    home, root = args.plan.resolve().parent, Path.cwd()
    plan = read_json(args.plan)
    verify(plan, home, root)
    if args.cell:
        return child(args, plan, home)
    if (home / "transport-policy.json").exists():
        raise ValueError(
            "Run already started; do not overwrite or silently resume a frozen experiment"
        )
    key = dotenv_values(args.env_file)["V5_API_KEY"]
    ledger, active, lock = [], {"cell": "initializing", "pilot": True}, threading.Lock()

    def save(path, value):
        raw = json.dumps(value, ensure_ascii=False, indent=2).replace(key, "<redacted>") + "\n"
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".writing")
        temp.write_text(raw)
        temp.replace(path)

    class Relay(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            if self.path != "/v1/chat/completions" or not hmac.compare_digest(
                self.headers.get("Authorization", ""), "Bearer " + key
            ):
                self.send_error(403)
                return
            size = int(self.headers.get("Content-Length", 0))
            if not 0 < size <= 15_000_000:
                self.send_error(413)
                return
            body = json.loads(self.rfile.read(size))
            if body.get("model") != plan["model"] or body.get("stream"):
                self.send_error(400)
                return
            body.pop("thinking", None)
            body["reasoning"] = {"enabled": False}
            body["provider"] = plan["provider"]
            sizing = measure(
                {"messages": body["messages"], "response_format": body.get("response_format")}
            )
            output_tokens = body.get("max_completion_tokens", body.get("max_tokens", 0))
            if type(output_tokens) is not int or output_tokens <= 0:
                self.send_error(400)
                return
            reserve = (
                sizing["reservation_input_tokens"] * plan["pricing"]["input_per_million"]
                + output_tokens * plan["pricing"]["output_per_million"]
            ) / 1e6
            with lock:
                costs = [(r.get("response", {}).get("usage") or {}).get("cost") for r in ledger]
                pilot_spend = sum(
                    c
                    for r, c in zip(ledger, costs, strict=True)
                    if r["cell"] == plan["pilot"] and type(c) in (int, float)
                )
                known = sum(c for c in costs if type(c) in (int, float))
                if (
                    len(ledger) >= plan["max_forwarded_requests"]
                    or any(c is None for c in costs)
                    or known + reserve > plan["max_usd"]
                    or (active["pilot"] and pilot_spend + reserve > plan["pilot_max_usd"])
                ):
                    self.send_error(
                        402, "Frozen cost/request guard reached; unknown charges are not zero"
                    )
                    return
                record = {
                    "index": len(ledger) + 1,
                    "cell": active["cell"],
                    "request": body,
                    "preflight": {**sizing, "reserved_usd": reserve},
                    "started_at": datetime.now(UTC).isoformat(),
                    "status": "started",
                }
                ledger.append(record)
            path = home / "transport" / f"request-{record['index']:04d}.json"
            save(path, record)
            started = time.monotonic()
            try:
                with httpx.Client(timeout=125, trust_env=False, follow_redirects=False) as client:
                    response = client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={"Authorization": "Bearer " + key},
                        json=body,
                    )
                status, wire = response.status_code, response.content
                parsed = response.json()
                record.update(
                    status="received",
                    http_status=status,
                    response=parsed,
                    seconds=time.monotonic() - started,
                )
                if status == 200 and parsed.get("provider") != "Relace":
                    record["provider_contract_violation"] = True
            except Exception as exc:
                status = 502
                wire = json.dumps({"error": {"message": "Audited relay transport error"}}).encode()
                record.update(
                    status="transport_error",
                    error_type=type(exc).__name__,
                    seconds=time.monotonic() - started,
                )
            save(path, record)
            try:
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(wire)))
                self.end_headers()
                self.wfile.write(wire)
            except (BrokenPipeError, ConnectionResetError):
                record["downstream_disconnected"] = True
                save(path, record)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Relay)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    endpoint = f"http://127.0.0.1:{server.server_port}/v1"
    save(
        home / "transport-policy.json",
        {
            "provider": plan["provider"],
            "max_usd": plan["max_usd"],
            "pilot_max_usd": plan["pilot_max_usd"],
            "authorization_headers_persisted": False,
        },
    )
    completed = []
    try:
        order = [plan["pilot"]] + [c for c in plan["cells"] if c != plan["pilot"]]
        for index, name in enumerate(order):
            verify(plan, home, root)
            if (home / "STOP_AFTER_CELL").exists():
                raise RuntimeError("Requested stop; prior cells retained")
            active.update(cell=name, pilot=index == 0)
            print(json.dumps({"event": "cell_started", "cell": name}), flush=True)
            process = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--plan",
                    str(args.plan.resolve()),
                    "--env-file",
                    str(args.env_file.resolve()),
                    "--cell",
                    name,
                    "--endpoint",
                    endpoint,
                ],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=1500,
            )
            task, stage = name.split("/")
            cell = home / "cells" / f"task{task}-{stage}-r0"
            (cell / "process.log").write_text(
                (process.stdout + process.stderr).replace(key, "<redacted>")
            )
            result = read_json(cell / "cell.json")
            completed.append(result)
            save(
                home / "progress.json",
                {"completed": len(completed), "planned": len(order), "cells": completed},
            )
            save(home / "transport-ledger.json", ledger)
            print(json.dumps({"event": "cell_finished", **result}), flush=True)
            if (
                process.returncode
                or result["status"] != "evaluated"
                or result.get("judge_status") != "complete"
            ):
                raise RuntimeError(
                    "Frozen infrastructure/complete-judging gate failed; no remaining paid cells"
                )
            if any(
                r.get("provider_contract_violation")
                or r.get("response", {}).get("usage", {}).get("cost") is None
                for r in ledger
            ):
                raise RuntimeError("Provider/cost contract failed")
            freeze = read_json(cell / "run-freeze.json")
            if digest(read_json(cell / "adaptation/knowledge.json")) != freeze["knowledge_sha256"]:
                raise RuntimeError("Pilot knowledge changed")
            if index == 0:
                save(
                    home / "pilot-gate.json",
                    {
                        "passed": True,
                        "cell": name,
                        "criteria": plan["pilot_gates"],
                        "quality_scores_are_not_gate_thresholds": True,
                        "original_outcome": result,
                    },
                )
        save(
            home / "completed.json",
            {"status": "complete", "cells": len(completed), "requests": len(ledger)},
        )
    except BaseException as exc:
        save(
            home / "stopped.json",
            {
                "status": "stopped",
                "error_type": type(exc).__name__,
                "reason": str(exc),
                "completed_cells": len(completed),
                "no_fallback": True,
            },
        )
        raise
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        save(home / "transport-ledger.json", ledger)


if __name__ == "__main__":
    main()

"""Opt-in artifact-v1: exact Python artifact, static check, isolated tests, bounded repair.

Only Docker runs generated/test code. No host exec/import fallback exists. Docker
must already have a locally reviewed image pinned by digest; images are never pulled.
"""

import ast
import asyncio
import hashlib
import json
import re
import selectors
import shutil
import subprocess
import threading
import time
import uuid
from copy import deepcopy
from pathlib import Path

from .benchmark import digest, write_json

VERSION = "artifact-v1"
CONTRACT = """Return one JSON object, no markdown, with exactly these keys:
{"artifact":{"path":"artifact.py","language":"python","source":"complete Python source"},
"summary":"brief user-facing explanation"}. The source is the exact final deliverable.
Tool observations about expressions or prompt templates do not test this artifact.
Independent finite artifact tests may follow; passing them is not proof of full security."""
DEFAULTS = {
    "version": VERSION,
    "max_repairs": 1,
    "timeout_seconds": 10,
    "max_source_bytes": 100000,
    "max_output_bytes": 16000,
    "max_repair_tokens": 4096,
    "repair_timeout_seconds": 60,
    "max_repair_request_chars": 300000,
}
# Trusted container driver. The artifact and supplied tests execute only inside Docker.
DRIVER = r"""
import hashlib, json, os, secrets, subprocess, sys
p = json.load(sys.stdin)
os.chdir('/work')
source = p['source'].encode('utf-8')
expected = hashlib.sha256(source).hexdigest()
open('artifact.py', 'wb').write(source)
test = p['tests'][0]
open('check.py', 'w').write("import sys; sys.path.insert(0, '/work')\n" + test['source'])
token = '__PE6203_TEST_COMPLETED_' + secrets.token_hex(32)
wrapper = "import runpy; runpy.run_path('/work/check.py', run_name='__main__'); print(" + repr(token) + ")"
try:
    r = subprocess.run([sys.executable, '-I', '-c', wrapper], capture_output=True,
                       timeout=p['timeout'], env={'PATH':'/usr/local/bin:/usr/bin:/bin'})
    out = (r.stdout + r.stderr).decode('utf-8', 'replace')
    try:
        actual = hashlib.sha256(open('artifact.py', 'rb').read()).hexdigest()
    except OSError:
        actual = None
    complete = r.stdout.endswith((token + '\n').encode())
    status = 'passed' if r.returncode == 0 and complete and actual == expected else (
        'unsupported_dependencies' if 'ModuleNotFoundError:' in out else
        'resource_failure' if r.returncode < 0 else 'test_failed')
    row = {'id':test['id'], 'kind':test['kind'], 'status':status,
           'returncode':r.returncode, 'normal_completion':complete,
           'artifact_sha256_before':expected, 'artifact_sha256_after':actual,
           'output':out.replace(token, '[completion-marker]')[:p['max_output']]}
except subprocess.TimeoutExpired:
    row = {'id':test['id'], 'kind':test['kind'], 'status':'timeout', 'normal_completion':False,
           'artifact_sha256_before':expected}
print(json.dumps({'tests':[row]}))
"""


def settings(value):
    if not isinstance(value, dict) or set(value) - set(DEFAULTS) - {"image", "tests"}:
        raise ValueError("Invalid artifact-v1 settings")
    config = {**DEFAULTS, **deepcopy(value)}
    if config["version"] != VERSION:
        raise ValueError("Unsupported artifact protocol version")
    for key, low, high in [
        ("max_repairs", 0, 3),
        ("timeout_seconds", 1, 30),
        ("max_source_bytes", 1, 200000),
        ("max_output_bytes", 256, 32000),
        ("max_repair_tokens", 1, 16384),
        ("repair_timeout_seconds", 1, 120),
        ("max_repair_request_chars", 1000, 500000),
    ]:
        if type(config[key]) is not int or not low <= config[key] <= high:
            raise ValueError("Invalid artifact budget: " + key)
    image = config.get("image", "")
    if not isinstance(image, str) or not re.fullmatch(r"[\w./:-]+@sha256:[a-f0-9]{64}", image):
        raise ValueError("Artifact backend requires an explicit image pinned by sha256")
    tests = config.get("tests", [])
    if not isinstance(tests, list) or len(tests) > 32:
        raise ValueError("Invalid independent tests")
    seen = set()
    for row in tests:
        if not isinstance(row, dict) or set(row) != {"id", "kind", "source"}:
            raise ValueError("Each independent test requires id, kind, source")
        if (
            not isinstance(row["id"], str)
            or not row["id"]
            or row["id"] in seen
            or row["kind"] not in {"benign", "negative"}
            or not isinstance(row["source"], str)
            or len(row["source"].encode()) > 20000
        ):
            raise ValueError("Invalid independent test")
        ast.parse(row["source"], filename="independent-test.py")  # static only
        seen.add(row["id"])
    config["tests"] = tests
    return config


def extract(answer, limit):
    try:
        data = json.loads(answer)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict) or set(data) != {"artifact", "summary"}:
        return None
    artifact = data["artifact"]
    if (
        not isinstance(artifact, dict)
        or set(artifact) != {"path", "language", "source"}
        or artifact["path"] != "artifact.py"
        or artifact["language"] != "python"
        or not isinstance(data["summary"], str)
        or not isinstance(artifact["source"], str)
        or not artifact["source"].strip()
        or len(artifact["source"].encode()) > limit
    ):
        return None
    return artifact["source"]


def _bounded(command, payload, timeout, limit, cancelled=None):
    """Run trusted Docker CLI only; cap host output memory and elapsed time."""
    proc = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env={"PATH": "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin"},
    )
    output = bytearray()
    deadline = time.monotonic() + timeout
    try:
        # Container input is bounded by validated source/test limits (< 1 MB).
        # A writer thread avoids blocking the timeout when a daemon never consumes stdin.
        def send():
            try:
                proc.stdin.write(payload)
                proc.stdin.close()
            except (BrokenPipeError, OSError):
                pass

        writer = threading.Thread(target=send, daemon=True)
        writer.start()
        with selectors.DefaultSelector() as selector:
            selector.register(proc.stdout, selectors.EVENT_READ)
            while selector.get_map():
                if cancelled is not None and cancelled.is_set():
                    return {"status": "cancelled"}
                if time.monotonic() >= deadline:
                    return {"status": "timeout"}
                for key, _ in selector.select(
                    timeout=max(0, min(0.1, deadline - time.monotonic()))
                ):
                    chunk = key.fileobj.read1(4096)
                    if not chunk:
                        selector.unregister(key.fileobj)
                    else:
                        output.extend(chunk)
                        if len(output) > limit:
                            return {"status": "resource_failure", "reason": "output_limit"}
        code = proc.wait(timeout=max(0.01, deadline - time.monotonic()))
        return {"returncode": code, "output": output.decode("utf-8", "replace")}
    except subprocess.TimeoutExpired:
        return {"status": "timeout"}
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait()
        proc.stdout.close()
        writer.join(timeout=1)


class DockerBackend:
    """No network, host mounts, privileged user, env credentials, or image pulls."""

    def __init__(self, config):
        self.config = config
        self.executable = shutil.which("docker")
        self.cancelled = threading.Event()

    def cancel(self):
        self.cancelled.set()

    def available(self):
        if not self.executable:
            return False
        try:
            check = _bounded(
                [self.executable, "image", "inspect", self.config["image"]], b"", 5, 100000
            )
            return check.get("returncode") == 0
        except OSError:
            return False

    def run(self, source, tests):
        if not self.available():
            return {"status": "backend_unavailable", "tests": [], "isolated_execution": False}
        rows = []
        for test in tests:
            # A fresh container per test prevents cross-test file/process contamination.
            result = self._run_one(source, test)
            if result["status"] != "observed":
                return {**result, "tests": rows + result.get("tests", [])}
            rows.extend(result["tests"])
        statuses = {r["status"] for r in rows}
        status = (
            "passed_finite_tests"
            if statuses == {"passed"}
            else next(
                (
                    s
                    for s in (
                        "resource_failure",
                        "timeout",
                        "unsupported_dependencies",
                        "test_failed",
                    )
                    if s in statuses
                ),
                "no_tests",
            )
        )
        return {"status": status, "tests": rows, "isolated_execution": True}

    def _run_one(self, source, test):
        tests = [test]
        cfg = self.config
        name = "pe6203-artifact-" + uuid.uuid4().hex
        command = [
            self.executable,
            "run",
            "--rm",
            "--pull=never",
            "--name",
            name,
            "--network=none",
            "--read-only",
            "--user=65534:65534",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--pids-limit=32",
            "--memory=128m",
            "--memory-swap=128m",
            "--cpus=0.5",
            "--ulimit=nofile=64:64",
            "--ulimit=fsize=1048576:1048576",
            "--ulimit=core=0:0",
            "--tmpfs=/work:rw,noexec,nosuid,size=16m,mode=1777",
            "--workdir=/work",
            "--entrypoint=python",
            "-i",
            cfg["image"],
            "-I",
            "-c",
            DRIVER,
        ]
        payload = json.dumps(
            {
                "source": source,
                "tests": tests,
                "timeout": cfg["timeout_seconds"],
                "max_output": cfg["max_output_bytes"],
            }
        ).encode()
        try:
            result = _bounded(
                command,
                payload,
                (len(tests) + 1) * cfg["timeout_seconds"] + 5,
                cfg["max_output_bytes"] * (len(tests) + 1),
                cancelled=self.cancelled,
            )
            if "status" in result:
                return {**result, "tests": [], "isolated_execution": False}
            if result["returncode"] != 0:
                return {
                    "status": "resource_failure"
                    if result["returncode"] in {137, 143}
                    else "backend_error",
                    "returncode": result["returncode"],
                    "tests": [],
                    "isolated_execution": False,
                }
            try:
                rows = json.loads(result["output"])["tests"]
                if len(rows) != len(tests) or any(r["id"] != t["id"] for r, t in zip(rows, tests)):
                    raise ValueError("incomplete results")
                expected = hashlib.sha256(source.encode()).hexdigest()
                if any(r.get("artifact_sha256_before") != expected for r in rows):
                    raise ValueError("Wrong artifact tested")
                if any(
                    r["status"] == "passed"
                    and (
                        r.get("normal_completion") is not True
                        or r.get("artifact_sha256_after") != expected
                    )
                    for r in rows
                ):
                    raise ValueError("Incomplete/tampered artifact test")
                return {"status": "observed", "tests": rows, "isolated_execution": True}
            except (ValueError, KeyError, TypeError, StopIteration):
                return {"status": "backend_error", "tests": [], "isolated_execution": False}
        finally:
            # Killing the Docker client alone does not reliably kill the container.
            try:
                _bounded([self.executable, "rm", "-f", name], b"", 5, 10000)
            except OSError:
                pass


async def validate(answer, config, output, repair=None, backend=None):
    """Repair callback receives observed failures; every returned source is revalidated.

    The callback is the execution model, not the updater or benchmark judge.
    Test doubles must be identified by callers; this function never fabricates repairs.
    """
    config = settings(config)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "protocol.json", config)
    started = time.monotonic()
    audit = {
        "version": VERSION,
        "protocol_sha256": digest(config),
        "status": "started",
        "attempts": [],
        "repairs": [],
        "latest_artifact": None,
        "accepted_artifact": None,
        "accepted_summary": None,
        "security_guarantee": False,
        "official_TF_PE": "separate_not_measured_here",
    }
    backend = backend if backend is not None else DockerBackend(config)
    current = answer
    try:
        for index in range(config["max_repairs"] + 1):
            attempt_started = time.monotonic()
            source = extract(current, config["max_source_bytes"])
            attempt = {"index": index, "status": "no_artifact", "isolated_execution": False}
            audit["attempts"].append(attempt)
            if source is not None:
                path = f"attempt-{index}.py"
                (output / path).write_bytes(source.encode("utf-8"))
                attempt.update(
                    artifact_path=path, sha256=hashlib.sha256(source.encode()).hexdigest()
                )
                audit["latest_artifact"] = {"path": path, "sha256": attempt["sha256"]}
                try:
                    compile(source, path, "exec", ast.PyCF_ONLY_AST)
                    compile(source, path, "exec")  # generates bytecode, never executes it
                    attempt["static_status"] = "passed"
                except (SyntaxError, ValueError, RecursionError, MemoryError) as exc:
                    attempt.update(
                        status="syntax_failed",
                        static_status="failed",
                        failure={"type": type(exc).__name__, "message": str(exc)[:2000]},
                    )
                else:
                    if not config["tests"]:
                        attempt["status"] = "no_tests"
                    else:
                        worker = asyncio.create_task(
                            asyncio.to_thread(backend.run, source, config["tests"])
                        )
                        try:
                            observed = await asyncio.shield(worker)
                        except asyncio.CancelledError:
                            if hasattr(backend, "cancel"):
                                backend.cancel()
                            # The real backend terminates the CLI then force-removes its named container.
                            # Do not leave a cancelled run silently executing a test container.
                            try:
                                await asyncio.wait_for(asyncio.shield(worker), 7)
                            except Exception:
                                pass
                            attempt["status"] = "cancelled"
                            audit.update(status="cancelled", termination="cancelled")
                            raise
                        attempt.update(observed)
            attempt["seconds"] = time.monotonic() - attempt_started
            audit["status"] = attempt["status"]
            if attempt["status"] == "passed_finite_tests":
                audit["accepted_artifact"] = deepcopy(audit["latest_artifact"])
                audit["accepted_summary"] = json.loads(current)["summary"]
                break
            if attempt["status"] not in {"syntax_failed", "test_failed", "no_artifact"}:
                break  # no repair guesses for backend/dependency/resource/test availability
            if index == config["max_repairs"] or repair is None:
                audit["termination"] = "repair_exhausted" if repair else "repair_not_configured"
                break
            feedback = {
                "protocol": VERSION,
                "attempt": deepcopy(attempt),
                "source": source,
                "independent_tests_sha256": digest(config["tests"]),
                "instruction": "Correct the exact artifact using these observed failures. "
                + CONTRACT,
            }
            write_json(output / f"repair-{index}-feedback.json", feedback)
            request = {"index": index, "status": "started"}
            audit["repairs"].append(request)
            write_json(output / "audit.json", audit)
            repair_started = time.monotonic()
            try:
                current = await asyncio.wait_for(repair(feedback), config["repair_timeout_seconds"])
                request["status"] = "returned_requires_revalidation"
            except BaseException as exc:
                request.update(status="repair_failed", error_type=type(exc).__name__)
                if isinstance(exc, asyncio.CancelledError):
                    audit["termination"] = "cancelled"
                    raise
                audit["termination"] = "repair_failed"
                break
            request["seconds"] = time.monotonic() - repair_started
            write_json(output / f"repair-{index}-response.json", {"answer": current})
        return audit
    except asyncio.CancelledError:
        audit.update(status="cancelled", termination="cancelled")
        raise
    except Exception as exc:
        audit.update(status="validation_error", error_type=type(exc).__name__)
        raise
    finally:
        audit["seconds"] = time.monotonic() - started
        write_json(output / "audit.json", audit)

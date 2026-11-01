"""Mock orchestration and SDK-wire tests are NOT actual isolated execution."""

import copy
import hashlib
import json

import httpx
import pytest
from openai import AsyncOpenAI
from test_contract import record
from test_runner import completion

from pe6203 import artifact_validation as av
from pe6203.runner import agent_loop, prepare_tools

IMAGE = "python@sha256:" + "0" * 64  # test placeholder, never pulled
TESTS = [
    {
        "id": "lower",
        "kind": "benign",
        "source": "from artifact import normalize\nassert normalize(' A ') == 'a'",
    },
    {
        "id": "reject",
        "kind": "negative",
        "source": "from artifact import normalize\ntry:\n normalize(None)\nexcept TypeError:\n pass\nelse:\n raise AssertionError('expected TypeError')",
    },
]
GOOD = "def normalize(value):\n if not isinstance(value, str): raise TypeError('string required')\n return value.strip().lower()\n"
BAD = "def normalize(value):\n return value.strip()\n"


def protocol(**kwargs):
    return {"image": IMAGE, "tests": copy.deepcopy(TESTS), **kwargs}


def answer(source):
    return json.dumps(
        {
            "artifact": {"path": "artifact.py", "language": "python", "source": source},
            "summary": "Synthetic test deliverable.",
        }
    )


class ScriptedBackend:
    """Pure test double: never executes any generated code, including GOOD/BAD."""

    def __init__(self, statuses):
        self.statuses = iter(statuses)
        self.sources = []

    def run(self, source, tests):
        self.sources.append(source)
        status = next(self.statuses)
        return {
            "status": status,
            "isolated_execution": False,
            "evidence_kind": "scripted_test_double",
            "tests": [
                {
                    "id": t["id"],
                    "kind": t["kind"],
                    "status": "passed" if status == "passed_finite_tests" else status,
                    "output": "scripted AssertionError: expected normalized lower-case text",
                }
                for t in tests
            ],
        }


@pytest.mark.asyncio
async def test_syntax_failure_feedback_repair_and_exact_revalidation(tmp_path):
    backend = ScriptedBackend(["passed_finite_tests"])
    observed = []

    async def repair(feedback):
        observed.append(feedback)
        return answer(GOOD)

    result = await av.validate(
        answer("def broken(:"), protocol(), tmp_path / "out", repair, backend
    )
    assert observed[0]["attempt"]["status"] == "syntax_failed"
    assert observed[0]["attempt"]["isolated_execution"] is False
    assert backend.sources == [GOOD]
    assert result["accepted_artifact"]["sha256"] == hashlib.sha256(GOOD.encode()).hexdigest()
    assert (tmp_path / "out/attempt-1.py").read_bytes() == GOOD.encode()


@pytest.mark.asyncio
async def test_failed_repair_cannot_bypass_final_validation(tmp_path):
    backend = ScriptedBackend(["test_failed", "test_failed"])

    async def repair(feedback):
        assert "AssertionError" in feedback["attempt"]["tests"][0]["output"]
        return answer(BAD)

    result = await av.validate(answer(BAD), protocol(), tmp_path / "out", repair, backend)
    assert len(backend.sources) == 2
    assert result["accepted_artifact"] is None
    assert result["status"] == "test_failed" and result["termination"] == "repair_exhausted"
    assert result["latest_artifact"]["path"] == "attempt-1.py"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status",
    [
        "backend_unavailable",
        "unsupported_dependencies",
        "timeout",
        "resource_failure",
        "backend_error",
    ],
)
async def test_nonrepairable_failures_are_distinct_and_do_not_guess(status, tmp_path):
    async def forbidden(feedback):
        raise AssertionError("No model request allowed for backend/resource failures")

    result = await av.validate(
        answer(GOOD), protocol(), tmp_path / "out", forbidden, ScriptedBackend([status])
    )
    assert result["status"] == status and result["repairs"] == []
    assert result["latest_artifact"] and result["accepted_artifact"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        "no code supplied",
        "```python\nprint('ambiguous')\n```",
        answer(""),
        answer(GOOD).replace("artifact.py", "../../escape.py"),
    ],
)
async def test_ambiguous_or_absent_artifact_never_executes(response, tmp_path):
    backend = ScriptedBackend([])
    result = await av.validate(response, protocol(max_repairs=0), tmp_path / "out", backend=backend)
    assert result["status"] == "no_artifact" and not backend.sources
    assert result["latest_artifact"] is None


@pytest.mark.asyncio
async def test_no_tests_never_executes(tmp_path):
    backend = ScriptedBackend([])
    result = await av.validate(answer(GOOD), protocol(tests=[]), tmp_path / "out", backend=backend)
    assert result["status"] == "no_tests" and backend.sources == []
    assert result["attempts"][0]["static_status"] == "passed"


@pytest.mark.asyncio
async def test_no_backend_does_not_execute_generated_side_effect_on_host(tmp_path, monkeypatch):
    monkeypatch.setattr(av.shutil, "which", lambda _: None)
    marker = tmp_path / "NEVER-CREATE"
    source = f"open({str(marker)!r}, 'w').write('unsafe host execution')"
    result = await av.validate(answer(source), protocol(), tmp_path / "out")
    assert result["status"] == "backend_unavailable"
    assert result["attempts"][0]["isolated_execution"] is False
    assert not marker.exists()


@pytest.mark.asyncio
async def test_repair_provider_failure_retains_latest_artifact_and_audit(tmp_path):
    async def repair(feedback):
        raise RuntimeError("provider problem")

    result = await av.validate(
        answer(BAD), protocol(), tmp_path / "out", repair, ScriptedBackend(["test_failed"])
    )
    assert result["termination"] == "repair_failed"
    assert result["latest_artifact"]["path"] == "attempt-0.py"
    assert (tmp_path / "out/audit.json").exists()


@pytest.mark.parametrize("arm", ["no_update", "full_rewrite", "v1", "v2", "v3"])
@pytest.mark.asyncio
async def test_public_agent_loop_same_protocol_model_budget_and_feedback_for_every_arm(
    arm, tmp_path, monkeypatch
):
    # Real SDK serialization; explicitly scripted HTTP and backend observations.
    backend = ScriptedBackend(["test_failed", "passed_finite_tests"])
    monkeypatch.setattr(av, "DockerBackend", lambda config: backend)
    requests, events = [], []
    workspace = tmp_path / arm / "workspace"
    workspace.mkdir(parents=True)

    def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        assert (workspace.parent / "artifact-protocol-frozen.json").exists()
        if len(requests) == 2:
            feedback = json.loads(body["messages"][-1]["content"])
            assert feedback["attempt"]["status"] == "test_failed"
            assert feedback["source"] == BAD
            assert body["max_completion_tokens"] == 128
            assert "tools" not in body
        return completion(
            {"role": "assistant", "content": answer(BAD if len(requests) == 1 else GOOD)}
        )

    strategy = arm if arm in {"no_update", "full_rewrite"} else "selective_patch"
    tools, routes = prepare_tools([record()], strategy)
    async with AsyncOpenAI(
        api_key="scripted",
        base_url="http://test.local/v1",
        max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    ) as client:
        result = await agent_loop(
            client,
            {},
            tools,
            routes,
            "Synthetic normalize task",
            workspace,
            {
                "max_rounds": 2,
                "agent": {"model": "fixture-model", "temperature": 0, "max_completion_tokens": 128},
                "artifact_validation": protocol(max_repair_tokens=128),
            },
            3,
            events.append,
        )
    assert result["artifact_validation"]["status"] == "passed_finite_tests"
    assert backend.sources == [BAD, GOOD]
    assert len(requests) == 2 and {r["model"] for r in requests} == {"fixture-model"}
    assert result["usage"]["total_tokens"] == 30
    assert json.loads(result["answer"])["artifact"]["source"] == GOOD
    assert (
        json.loads(result["answer"])["validation"]["sha256"]
        == hashlib.sha256(GOOD.encode()).hexdigest()
    )
    assert events[0]["type"] == "artifact_protocol_frozen"


def test_docker_command_constraints_and_input_hash(monkeypatch):
    cfg = av.settings(protocol())
    backend = av.DockerBackend(cfg)
    backend.executable = "/usr/bin/docker"
    monkeypatch.setattr(backend, "available", lambda: True)
    commands = []

    def bounded(command, payload, timeout, limit, **kwargs):
        commands.append(command)
        if "run" not in command:
            return {"returncode": 0, "output": ""}
        data = json.loads(payload)
        sha = hashlib.sha256(data["source"].encode()).hexdigest()
        return {
            "returncode": 0,
            "output": json.dumps(
                {
                    "tests": [
                        {
                            "id": data["tests"][0]["id"],
                            "kind": data["tests"][0]["kind"],
                            "status": "passed",
                            "normal_completion": True,
                            "artifact_sha256_before": sha,
                            "artifact_sha256_after": sha,
                        }
                    ]
                }
            ),
        }

    monkeypatch.setattr(av, "_bounded", bounded)
    result = backend.run(GOOD, TESTS)
    runs = [c for c in commands if "run" in c]
    assert len(runs) == len(TESTS)  # fresh container per independent test
    for command in runs:
        for flag in [
            "--network=none",
            "--read-only",
            "--user=65534:65534",
            "--cap-drop=ALL",
            "--pull=never",
            "--security-opt=no-new-privileges",
            "--pids-limit=32",
            "--memory=128m",
        ]:
            assert flag in command
        assert not ({"-v", "--volume", "--mount", "--env", "-e", "--privileged"} & set(command))
        assert command[command.index("-i") + 1] == IMAGE
    assert result["status"] == "passed_finite_tests"


@pytest.mark.parametrize(
    "change",
    [
        {"normal_completion": False},
        {"artifact_sha256_after": "tampered"},
        {"artifact_sha256_before": "wrong artifact"},
    ],
)
def test_exit_zero_or_wrong_artifact_is_never_accepted(monkeypatch, change):
    backend = av.DockerBackend(av.settings(protocol()))
    backend.executable = "/usr/bin/docker"
    monkeypatch.setattr(backend, "available", lambda: True)
    sha = hashlib.sha256(GOOD.encode()).hexdigest()
    row = {
        "id": TESTS[0]["id"],
        "kind": "benign",
        "status": "passed",
        "returncode": 0,
        "normal_completion": True,
        "artifact_sha256_before": sha,
        "artifact_sha256_after": sha,
        **change,
    }
    monkeypatch.setattr(
        av,
        "_bounded",
        lambda *args, **kwargs: {"returncode": 0, "output": json.dumps({"tests": [row]})},
    )
    assert backend.run(GOOD, TESTS[:1])["status"] == "backend_error"


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["provider_error", "cancelled"])
async def test_public_repair_error_or_cancel_keeps_unknown_usage_event(
    failure, tmp_path, monkeypatch
):
    import asyncio

    backend = ScriptedBackend(["test_failed"])
    monkeypatch.setattr(av, "DockerBackend", lambda config: backend)
    events, requests = [], []
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    async def handler(request):
        requests.append(request)
        if len(requests) == 2:
            if failure == "cancelled":
                raise asyncio.CancelledError()
            raise httpx.ConnectError("scripted outage", request=request)
        return completion({"role": "assistant", "content": answer(BAD)})

    tools, routes = prepare_tools([record()], "no_update")
    async with AsyncOpenAI(
        api_key="scripted",
        base_url="http://test.local/v1",
        max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    ) as client:
        task = agent_loop(
            client,
            {},
            tools,
            routes,
            "Task",
            workspace,
            {
                "max_rounds": 1,
                "agent": {"model": "fixture-model", "temperature": 0, "max_completion_tokens": 128},
                "artifact_validation": protocol(),
            },
            0,
            events.append,
        )
        if failure == "cancelled":
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            result = await task
            assert result["usage"]["total_tokens"] is None
            assert result["artifact_validation"]["termination"] == "repair_failed"
    assert len(requests) == 2
    assert any(e["type"] == "artifact_repair_error" for e in events)
    audit = json.loads((tmp_path / "artifact-validation/audit.json").read_text())
    assert audit["accepted_artifact"] is None and audit["latest_artifact"]
    if failure == "cancelled":
        assert audit["status"] == "cancelled"


@pytest.mark.asyncio
async def test_cancel_during_validation_stops_backend_and_persists_audit(tmp_path):
    import asyncio
    import threading

    entered, stopped = threading.Event(), threading.Event()

    class CancellableBackend:
        def run(self, source, tests):
            entered.set()
            assert stopped.wait(2)
            return {"status": "cancelled", "isolated_execution": False}

        def cancel(self):
            stopped.set()

    task = asyncio.create_task(
        av.validate(answer(GOOD), protocol(), tmp_path / "out", backend=CancellableBackend())
    )
    assert await asyncio.to_thread(entered.wait, 2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert stopped.is_set()
    audit = json.loads((tmp_path / "out/audit.json").read_text())
    assert audit["status"] == "cancelled" and audit["accepted_artifact"] is None


@pytest.mark.asyncio
async def test_truncated_generation_repaired_acceptance_retains_summary_and_compatible_status(
    tmp_path, monkeypatch
):
    backend = ScriptedBackend(["passed_finite_tests"])
    monkeypatch.setattr(av, "DockerBackend", lambda config: backend)
    requests = []

    def handler(request):
        requests.append(request)
        payload = json.loads(
            completion(
                {
                    "role": "assistant",
                    "content": "incomplete" if len(requests) == 1 else answer(GOOD),
                }
            ).content
        )
        if len(requests) == 1:
            payload["choices"][0]["finish_reason"] = "length"
        return httpx.Response(200, json=payload)

    tools, routes = prepare_tools([record()], "no_update")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    async with AsyncOpenAI(
        api_key="scripted",
        base_url="http://test.local/v1",
        max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    ) as client:
        result = await agent_loop(
            client,
            {},
            tools,
            routes,
            "Task",
            workspace,
            {
                "max_rounds": 1,
                "agent": {"model": "fixture-model", "temperature": 0, "max_completion_tokens": 128},
                "artifact_validation": protocol(),
            },
            0,
            lambda e: None,
        )
    assert result["generation_status"] == "output_truncated"
    assert result["status"] == "completed" and result["completion_origin"] == "artifact_repair"
    assert result["artifact_validation"]["accepted_artifact"]
    assert json.loads(result["answer"])["summary"] == "Synthetic test deliverable."

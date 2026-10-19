"""Saved baseline observations must survive the CLI presentation unchanged."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "pe6203.cli", "report", *map(str, args)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def recorded_run(tmp_path):
    folder = tmp_path / "full_rewrite" / "execution"
    write(
        folder / "result.json",
        {
            "task_id": 139,
            "version": "middle",
            "strategy": "full_rewrite",
            "seed": 0,
            "status": "evaluated",
            "execution_status": "max_rounds",
            "judge_status": "complete",
            "TF": 8.4,
            "PE": 7.0,
            "ECS": None,
            "seconds": 60,
            "config": {
                "judge_runs": 5,
                "max_rounds": 12,
                "execution_backend": "pinned_upstream_ChatModel_stdio_bridge",
            },
            "cost": {"update": {"tokens": 18831, "seconds": 10.55, "usd": None}},
        },
    )
    write(
        folder / "raw_trace.json",
        {
            "question": "Create a project",
            "answer": "No final answer generated.",
            "events": [
                {"type": "agent_response", "round": 1},
                {
                    "type": "tool_result",
                    "name": "server_1mcp_create_project",
                    "arguments": {"name": "Demo"},
                    "result": {"isError": False},
                    "elapsed_seconds": 2,
                },
                {"type": "agent_response", "round": 2},
                {
                    "type": "tool_error",
                    "name": "server_1mcp_create_task",
                    "arguments": {},
                    "error": "TimeoutError",
                    "elapsed_seconds": 32,
                },
                *[
                    {
                        "type": "judge_result",
                        "result": {
                            "task_fulfillment": 8,
                            "grounding": 9,
                            "planning_and_efficiency": 7,
                        },
                    }
                    for _ in range(5)
                ],
            ],
        },
    )
    write(
        folder / "workspace/.agentic-tools-mcp/tasks/tasks.json",
        {"projects": [{"name": "Demo"}], "tasks": []},
    )
    return folder


def test_upstream_trace_rounds_errors_and_legacy_update_cost_are_visible(recorded_run):
    result = cli(recorded_run, "--details")
    assert result.returncode == 0, result.stderr
    for value in (
        "8.40",
        "7.00",
        "5/5",
        "18,831",
        "10.55",
        "max_rounds",
        "轮数上限",
        "Demo",
        "create_project",
        "create_task",
        "TimeoutError",
        "round=2",
    ):
        assert value in result.stdout
    data = json.loads(cli(recorded_run, "--format", "json").stdout)["runs"][0]
    assert data["tool_count"] == 2 and data["tool_errors"] == 1
    assert data["trace_complete"] is True
    assert data["cost"]["update"]["total_tokens"] == 18831
    assert [call["round"] for call in data["calls"]] == [1, 2]


def test_pilot_folder_loads_all_strategies_and_retains_adaptation_failure(recorded_run):
    root = recorded_run.parent.parent
    write(
        root / "summary.json",
        {
            "task_id": 139,
            "target_version": "middle",
            "dry_run": False,
            "config": {"seed": 0, "judge_runs": 5},
            "runs": [
                {
                    "strategy": "full_rewrite",
                    "execution_dir": str(recorded_run),
                    "status": "evaluated",
                },
                {
                    "strategy": "no_update",
                    "status": "adaptation_failed",
                    "error_type": "ValueError",
                    "update_cost": {
                        "input_tokens": 7,
                        "output_tokens": 3,
                        "elapsed_seconds": 2,
                        "api_cost_usd": None,
                    },
                },
            ],
        },
    )
    result = cli(root)
    assert result.returncode == 0, result.stderr
    assert "full_rewrite" in result.stdout and "adaptation_failed" in result.stdout
    data = json.loads(cli(root / "summary.json", "--format", "json").stdout)["runs"]
    assert len(data) == 2
    assert data[1]["scores"]["TF"] is None
    assert data[1]["cost"]["update"]["total_tokens"] == 10


def test_report_preserves_adapter_trace_and_unknown_zero_and_refuses_overwrite(tmp_path):
    source = tmp_path / "evidence.json"
    write(
        source,
        {
            "result": {
                "task_id": 139,
                "status": "blocked",
                "config": {"api_key": "DO-NOT-SHOW"},
                "cost": {"agent": {"total_tokens": None}, "update": {"tokens": 0}},
            },
            "tool_results": [
                {
                    "round": 1,
                    "call": {"function": {"name": "create_project", "arguments": "{}"}},
                    "result": {"isError": True, "error": "unavailable\u001b[2J\u0007"},
                }
            ],
        },
    )
    before = source.read_bytes()
    output = tmp_path / "summary.txt"
    result = cli(source, "--details", "--output", output)
    assert result.returncode == 0, result.stderr
    text = output.read_text()
    assert "update 0" in text and "agent 未获得" in text
    assert "create_project" in text and "ERROR" in text
    assert "DO-NOT-SHOW" not in text and "\x1b" not in text and "\x07" not in text
    assert source.read_bytes() == before
    assert cli(source, "--output", output).returncode == 2
    assert cli(source, "--format", "json", "--output", source).returncode == 2

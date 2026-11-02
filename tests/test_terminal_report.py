"""CLI reports expose measured results without turning missing data into success."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "results/evidence/baseline-integration"
GOOD = EVIDENCE / "real-early-no-update-v2.json"
FAILED = EVIDENCE / "real-early-no-update.json"


def cli(*args, env=None):
    return subprocess.run(
        [sys.executable, "-m", "pe6203.cli", *map(str, args)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


def test_default_terminal_report_shows_real_scores_state_and_cost_without_modifying_evidence():
    before = hashlib.sha256(GOOD.read_bytes()).hexdigest()
    result = cli("report", GOOD)
    assert result.returncode == 0, result.stderr
    for observed in ("139", "early", "no_update", "9.80", "8.60", "5/5", "23", "37"):
        assert observed in result.stdout
    assert "未获得" in result.stdout  # ECS and USD are not measured.
    assert "179,215" in result.stdout and "86,057" in result.stdout
    assert "评分完整" in result.stdout
    assert before == hashlib.sha256(GOOD.read_bytes()).hexdigest()


def test_failed_run_and_different_protocols_remain_visible_without_average_or_zero_scores():
    result = cli("report", GOOD, FAILED)
    assert result.returncode == 0, result.stderr
    assert "judge_incomplete" in result.stdout and "0/5" in result.stdout
    assert "length" in result.stdout and "1/18" in result.stdout
    assert "配置不同" in result.stdout and "不能直接比较" in result.stdout
    assert "real-early-no-update-v2" in result.stdout
    assert "real-early-no-update" in result.stdout


def test_details_exposes_actual_calls_judge_variation_and_final_answer():
    result = cli("report", GOOD, "--details")
    assert result.returncode == 0, result.stderr
    assert "create_project" in result.stdout and "create_memory" in result.stdout
    assert "最终回答" in result.stdout and "Ableton Analysis" in result.stdout
    assert "Grounding" in result.stdout and "6.00" in result.stdout
    assert "9.00" in result.stdout and "10.00" in result.stdout


def test_json_mode_and_saved_text_keep_unknown_zero_and_refuse_overwrite(tmp_path):
    source = tmp_path / "result.json"
    source.write_text(
        json.dumps(
            {
                "task_id": 223,
                "version": "early",
                "strategy": "no_update",
                "status": "blocked",
                "config": {"api_key": "DO-NOT-PRINT", "judge_runs": 5},
                "cost": {"agent": {"total_tokens": None}, "update": {"total_tokens": 0}},
                "errors": [{"message": "provider unavailable\u001b[2J\u0007"}],
            }
        )
    )
    result = cli("report", source, "--format", "json")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)["runs"][0]
    assert data["scores"]["TF"] is None
    assert data["cost"]["agent"]["total_tokens"] is None
    assert data["cost"]["update"]["total_tokens"] == 0
    assert data["tool_count"] is None and data["tool_errors"] is None
    assert data["judge_records_available"] is False
    assert "DO-NOT-PRINT" not in result.stdout
    output = tmp_path / "summary.txt"
    result = cli("report", source, "--output", output)
    assert result.returncode == 0, result.stderr
    text = output.read_text()
    assert "blocked" in text and "未获得" in text and "provider unavailable" in text
    assert "\x1b" not in text and "\x07" not in text
    assert cli("report", source, "--output", output).returncode == 2
    assert cli("report", source, "--output", source).returncode == 2


def test_artifact_protocol_report_separates_generation_completion_and_acceptance(tmp_path):
    source = tmp_path / "result.json"
    source.write_text(
        json.dumps(
            {
                "task_id": 999,
                "status": "evaluated",
                "execution_status": "completed",
                "generation_status": "output_truncated",
                "completion_origin": "artifact_repair",
                "artifact_validation": {
                    "status": "passed_finite_tests",
                    "accepted_artifact": {"path": "attempt-1.py"},
                    "repairs": [{}],
                },
                "config": {},
            }
        )
    )
    result = cli("report", source)
    assert result.returncode == 0
    for text in [
        "passed_finite_tests",
        "initial=output_truncated",
        "final=completed",
        "origin=artifact_repair",
        "accepted=True",
        "security_guarantee=False",
    ]:
        assert text in result.stdout

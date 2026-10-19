import hashlib
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def report_data(path):
    return json.loads(
        re.search(
            r'<script id="report-data" type="application/json">(.*?)</script>',
            path.read_text(),
            re.S,
        ).group(1)
    )


def command(*args):
    return subprocess.run(
        [sys.executable, "-m", "pe6203.cli", "report", *map(str, args)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def test_report_preserves_real_scores_failed_attempts_and_partial_trace_counts(tmp_path):
    inputs = [
        ROOT / "results/evidence/baseline-integration" / name
        for name in ("real-early-no-update-v2.json", "real-early-no-update.json")
    ]
    before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs]
    output = tmp_path / "report.html"
    result = command(*inputs, "--output", output)
    assert result.returncode == 0, result.stderr
    data = report_data(output)
    good, failed = data["runs"]
    assert good["scores"] == {"TF": 9.8, "PE": 8.6, "ECS": None}
    assert len(good["judges"]) == 5
    assert good["tool_count"] == 23 and good["tool_errors"] == 0
    assert good["state_counts"]["relation_count"] == 37
    assert failed["scores"]["TF"] is None and failed["scores"]["PE"] is None
    assert failed["tool_count"] == 18 and failed["trace_complete"] is False
    assert all(j["finish_reason"] == "length" for j in failed["judges"])
    assert data["protocols_differ"] is True
    assert before == [hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs]
    assert command(*inputs, "--output", output).returncode == 2


def test_report_keeps_unknown_distinct_from_zero_and_untrusted_text_inert(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    attack = '</script><img src=x onerror="alert(1)">'
    (run / "result.json").write_text(
        json.dumps(
            {
                "task_id": 223,
                "status": "blocked",
                "execution_status": "not_started",
                "judge_status": "not_started",
                "TF": None,
                "PE": None,
                "ECS": None,
                "config": {"api_key": "DO-NOT-INCLUDE", "judge_runs": 5},
                "cost": {"agent": {"total_tokens": None}, "update": {"total_tokens": 0}},
                "errors": [{"type": "ValueError", "message": attack}],
            }
        )
    )
    output = tmp_path / "blocked.html"
    result = command(run, "--output", output)
    assert result.returncode == 0, result.stderr
    data = report_data(output)["runs"][0]
    assert data["cost"]["agent"]["total_tokens"] is None
    assert data["cost"]["update"]["total_tokens"] == 0
    assert data["errors"][0]["message"] == attack
    assert not data["calls"] and not data["judges"]
    assert "DO-NOT-INCLUDE" not in output.read_text()
    assert attack not in output.read_text()
    tags = []

    class Tags(HTMLParser):
        def handle_starttag(self, tag, attrs):
            tags.append(tag)

    Tags().feed(output.read_text())
    assert "img" not in tags
    assert command(run, "--output", run / "result.json").returncode == 2

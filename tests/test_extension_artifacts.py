import importlib.util
import json
from pathlib import Path

SOURCE = (
    Path(__file__).parents[1] / "experiments/extensions/magicui-log-dashboard-v1/check_artifacts.py"
)


def checker():
    spec = importlib.util.spec_from_file_location("extension_checker", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_artifact_check_requires_executed_parser_and_rejects_hardcoded_result(tmp_path):
    m = checker()
    workspace = tmp_path / "workspace"
    (workspace / "logs").mkdir(parents=True)
    (workspace / "logs/a.log").write_text("[2026-02-02T00:00:00.000Z] [ERROR] a\n")
    expected = {
        "daily": [{"date": "2026-02-02", "errors": 1}],
        "total_errors": 1,
        "days_covered": 1,
        "busiest_day": "2026-02-02",
    }
    oracle = tmp_path / "oracle.json"
    oracle.write_text(json.dumps(expected))
    before = m.check(workspace, oracle, tmp_path / "missing")
    assert before["parser_exists"] is False and before["core_data"] is False
    (workspace / "public").mkdir()
    (workspace / "public/data.json").write_text(json.dumps(expected))
    (workspace / "parse-logs.cjs").write_text("/* hardcoded data is already present */")
    after = m.check(workspace, oracle, tmp_path / "hardcoded")
    assert after["replay_correct"] is False and after["core_data"] is False


def test_exact_output_requires_zero_dates_and_integer_counts():
    m = checker()
    expected = {
        "daily": [{"date": "2026-02-02", "errors": 0}],
        "total_errors": 0,
        "days_covered": 1,
        "busiest_day": "2026-02-02",
    }
    assert m.equal_data(expected, expected)
    assert not m.equal_data({**expected, "daily": []}, expected)
    assert not m.equal_data({**expected, "total_errors": False}, expected)


def test_artifact_check_accepts_real_parser_and_reexecutes_with_added_log(tmp_path):
    m = checker()
    workspace = tmp_path / "workspace"
    (workspace / "logs").mkdir(parents=True)
    (workspace / "logs/a.log").write_text("[2026-02-02T00:00:00.000Z] [ERROR] a\n")
    (workspace / "public").mkdir()
    (workspace / "parse-logs.cjs").write_text("""
const fs=require('fs');let n=0;
for(const f of fs.readdirSync('logs')) for(const l of fs.readFileSync('logs/'+f,'utf8').split('\\n'))
if(/^\\[2026-02-02T[^\\]]+\\] \\[ERROR\\]/.test(l)) n++;
fs.writeFileSync('public/data.json',JSON.stringify({daily:[{date:'2026-02-02',errors:n}],total_errors:n,days_covered:1,busiest_day:'2026-02-02'}));
""")
    expected = {
        "daily": [{"date": "2026-02-02", "errors": 1}],
        "total_errors": 1,
        "days_covered": 1,
        "busiest_day": "2026-02-02",
    }
    (workspace / "public/data.json").write_text(json.dumps(expected))
    oracle = tmp_path / "oracle.json"
    oracle.write_text(json.dumps(expected))
    result = m.check(workspace, oracle, tmp_path / "assessment")
    assert result["core_data"] is True
    assert len(result["executions"]) == 2
    assert (workspace / "public/data.json").read_text() == json.dumps(expected)

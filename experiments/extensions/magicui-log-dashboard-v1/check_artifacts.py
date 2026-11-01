"""Frozen deterministic data acceptance. Run only against copied agent artifacts."""

import argparse
import copy
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
NODE = ROOT / ".cache/node-runtime/node_modules/node/bin/node"


def equal_data(actual, expected):
    if not isinstance(actual, dict) or set(actual) != set(expected):
        return False
    if any(type(actual.get(k)) is not int for k in ("total_errors", "days_covered")):
        return False
    if not isinstance(actual.get("daily"), list) or any(
        not isinstance(r, dict)
        or set(r) != {"date", "errors"}
        or type(r.get("errors")) is not int
        or not isinstance(r.get("date"), str)
        for r in actual["daily"]
    ):
        return False
    return actual == expected


def check(workspace, oracle, output):
    workspace, output = Path(workspace), Path(output)
    expected = json.loads(Path(oracle).read_text())
    output.mkdir(parents=True, exist_ok=False)
    result = {
        "parser_exists": (workspace / "parse-logs.cjs").is_file(),
        "page_exists": (workspace / "public/index.html").is_file(),
        "saved_data_correct": False,
        "replay_correct": False,
        "mutation_correct": False,
        "core_data": False,
        "executions": [],
    }
    try:
        result["saved_data_correct"] = equal_data(
            json.loads((workspace / "public/data.json").read_text()), expected
        )
    except (OSError, ValueError):
        pass
    if result["parser_exists"]:
        for variant in ("replay", "mutation"):
            target = output / variant
            shutil.copytree(
                workspace, target, symlinks=False, ignore=shutil.ignore_patterns(".home", "tmp.js")
            )
            (target / "public/data.json").unlink(missing_ok=True)
            want = copy.deepcopy(expected)
            if variant == "mutation":
                day = want["daily"][0]["date"]
                (target / "logs/assessment-extra.log").write_text(
                    f"[{day}T23:59:59.000Z] [ERROR] [audio-0] additional event\n"
                    "    Error: continuation is not another event\n"
                    f"[{day}T23:59:59.001Z] [INFO] [audio-0] Error counter inspection\n"
                )
                want["daily"][0]["errors"] += 1
                want["total_errors"] += 1
                want["busiest_day"] = min(want["daily"], key=lambda r: (-r["errors"], r["date"]))[
                    "date"
                ]
            (target / ".home").mkdir(exist_ok=True)
            env = {
                "HOME": str(target / ".home"),
                "TMPDIR": str(target),
                "PATH": str(NODE.parent) + ":/usr/bin:/bin",
                "LANG": "en_US.UTF-8",
            }
            try:
                execution = subprocess.run(
                    [str(NODE), "parse-logs.cjs"],
                    cwd=target,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                result["executions"].append(
                    {
                        "variant": variant,
                        "exit_code": execution.returncode,
                        "stdout": execution.stdout,
                        "stderr": execution.stderr,
                    }
                )
                result[variant + "_correct"] = execution.returncode == 0 and equal_data(
                    json.loads((target / "public/data.json").read_text()), want
                )
            except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
                result["executions"].append({"variant": variant, "error": str(exc)})
    result["core_data"] = all(
        result[k]
        for k in ("parser_exists", "saved_data_correct", "replay_correct", "mutation_correct")
    )
    (output / "data-check.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace", type=Path)
    parser.add_argument("oracle", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(check(args.workspace, args.oracle, args.output), indent=2))

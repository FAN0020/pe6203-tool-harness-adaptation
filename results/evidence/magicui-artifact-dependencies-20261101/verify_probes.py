"""Offline artifact checks against the preregistered native dependency canary."""

import hashlib
import json
import tarfile
from pathlib import Path

FOLDER = Path(__file__).resolve().parent
PREFIX = "results/evidence/magicui-artifact-dependencies-20261101/"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    manifest = json.loads((FOLDER / "archive-manifest.json").read_text())
    archive = FOLDER / "probe-and-source.tar.gz"
    assert sha(archive.read_bytes()) == manifest["archive_sha256"]
    with tarfile.open(archive) as tar:
        files = {m.name: tar.extractfile(m).read() for m in tar if m.isfile()}
    assert {k: sha(v) for k, v in files.items()} == manifest["files"]
    planpath = "experiments/magicui-artifact-dependencies-v1.json"
    plan = json.loads(files[planpath])
    pre = json.loads(files[PREFIX + "preexecution.json"])
    assert pre["plan_sha256"] == sha(files[planpath])
    assert pre["collector_sha256"] == sha(files[PREFIX + "run_probes.py"])
    assert pre["freeze_commit"].startswith("f7763cb")
    for item in plan["source"]:
        assert sha(files[item["path"]]) == item["sha256"]
    execution = json.loads(files[PREFIX + "execution.json"])
    assert execution["status"] == "completed_requires_review" and execution["stopping"] is None
    assert execution["tool_calls"] == execution["catalog_calls"] == 2
    assert execution["model_calls"] == execution["model_usd"] == 0
    rows = json.loads(files[PREFIX + "observations.json"])
    assert len(rows) == len(plan["schedule"]) == 2
    for index, (row, step) in enumerate(zip(rows, plan["schedule"], strict=True), 1):
        assert row == json.loads(files[PREFIX + f"call-{index:02d}.json"])
        assert row["index"] == index
        for k, v in step.items():
            assert row[k] == v
        assert "exception" not in row and row["result"]["isError"] is False
        assert pre["started_utc"] <= row["started_utc"] <= row["ended_utc"] <= execution["ended_utc"]
        value = json.loads("\n".join(x.get("text", "") for x in row["result"]["content"]))
        if index == 1:
            assert value["input"] == plan["canary_text"]
            assert value["cwd"].endswith("/" + PREFIX + "workspaces/file_roundtrip")
        else:
            canary = next(x for x in value if x["name"] == plan["canary_component"])
            assert len(value) == 9 and len(canary["content"]) == 6314
            assert 'from "motion/react"' in canary["content"]
            assert "MagicCard" in canary["content"] and "magic-card.json" in canary["install"]
    work = PREFIX + "workspaces/file_roundtrip/"
    assert files[work + "probe-input.txt"].decode() == plan["canary_text"]
    assert json.loads(files[work + "probe-output.json"]) == {"received": plan["canary_text"]}
    assert files[work + "probe-page.html"].decode() == plan["canary_html"]
    assert files[work + "tmp.js"].decode() == plan["schedule"][0]["arguments"]["code"]
    warnings = files[PREFIX + "run.log"].decode().count("Failed to parse JSONRPC message from server")
    assert warnings == 3
    print(json.dumps({
        "archive_integrity": True, "files": len(files), "frozen_source_files": len(plan["source"]),
        "tool_calls": 2, "catalog_calls": 2, "model_calls": 0, "model_usd": 0,
        "isolated_native_file_read_write_verified": True, "native_special_effects_code_verified": True,
        "inherited_stdout_protocol_warnings_preserved": warnings,
        "original_task_logs_available": False, "agent_improvement_tested": False, "goal_complete": False,
    }, indent=2))


if __name__ == "__main__":
    main()

"""Offline source, native-memory and reused PDF evidence checks."""

import hashlib
import json
import tarfile
from pathlib import Path

FOLDER = Path(__file__).resolve().parent
PREFIX = "results/evidence/context7-task-dependencies-20261101/"


def sha(value):
    return hashlib.sha256(value).hexdigest()


def main():
    manifest = json.loads((FOLDER / "archive-manifest.json").read_text())
    archive = FOLDER / "probe-and-source.tar.gz"
    assert sha(archive.read_bytes()) == manifest["archive_sha256"]
    with tarfile.open(archive) as tar:
        files = {m.name: tar.extractfile(m).read() for m in tar if m.isfile()}
    assert {k: sha(v) for k, v in files.items()} == manifest["files"]
    plan_path = "experiments/context7-task-dependencies-v1.json"
    plan = json.loads(files[plan_path])
    pre = json.loads(files[PREFIX + "preexecution.json"])
    assert pre["plan_sha256"] == sha(files[plan_path])
    assert pre["collector_sha256"] == sha(files[PREFIX + "run_probes.py"])
    for item in plan["source"]:
        assert sha(files[item["path"]]) == item["sha256"]
    execution = json.loads(files[PREFIX + "execution.json"])
    assert execution["status"] == "completed_requires_review"
    assert execution["tool_calls"] == 6 and execution["catalog_calls"] == 3
    assert execution["model_calls"] == execution["model_usd"] == 0
    rows = json.loads(files[PREFIX + "observations.json"])
    states = json.loads(files[PREFIX + "state-checks.json"])
    assert len(rows) == 6 and len(states) == 3
    for stage, state in zip(plan["stages"], states, strict=True):
        assert state["stage"] == stage
        stage_rows = [r for r in rows if r["stage"] == stage]
        for index, (row, step) in enumerate(zip(stage_rows, plan["schedule"], strict=True), 1):
            assert row == json.loads(files[PREFIX + f"{stage}-{index:02d}.json"])
            assert row["tool"] == step["tool"] and row["arguments"] == step["arguments"]
            assert "exception" not in row and not row["result"].get("isError")
            data = json.loads("\n".join(c.get("text", "") for c in row["result"]["content"]))
            assert data == ([plan["entity"]] if index == 1 else
                            {"entities": [plan["entity"]], "relations": []})
        raw = files[PREFIX + f"{stage}-memory.jsonl"]
        assert sha(raw) == state["sha256"]
        assert [json.loads(line) for line in raw.splitlines()] == [
            {"type": "entity", **plan["entity"]}]
    assert len({s["sha256"] for s in states}) == 1
    reuse = json.loads(files[plan["pdf_reuse"]])
    assert sha(files[reuse["fixture"]["path"]]) == reuse["fixture"]["sha256"]
    for record in reuse["records"]:
        raw = files[record["record"]]
        assert sha(raw) == record["sha256"]
        row = json.loads(raw)
        data = json.loads(row["result"]["content"][0]["text"])["results"]
        rt = next(x for x in data if "RT-2" in x["source"])
        assert rt["success"]
        assert [{"page": x["page"], "chars": len(x["text"]),
                 "text_sha256": sha(x["text"].encode())}
                for x in rt["data"]["page_texts"]] == record["pages"]
    print(json.dumps({"archive_integrity": True, "files": len(files),
                      "memory_tool_calls": 6, "catalog_calls": 3,
                      "memory_round_trip_all_stages": True,
                      "saved_memory_identical_all_stages": True,
                      "reused_pdf_records": 3, "new_pdf_calls": 0,
                      "model_calls": 0, "goal_complete": False}, indent=2))


if __name__ == "__main__":
    main()

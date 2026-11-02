"""Verify the frozen native routing probe offline; makes no service calls."""

import hashlib
import json
import tarfile
from pathlib import Path

FOLDER = Path(__file__).resolve().parent
PREFIX = "results/evidence/magicui-argument-routing-probes-20261101/"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    manifest = json.loads((FOLDER / "archive-manifest.json").read_text())
    archive = FOLDER / "probe-and-source.tar.gz"
    assert sha(archive.read_bytes()) == manifest["archive_sha256"]
    with tarfile.open(archive) as tar:
        files = {m.name: tar.extractfile(m).read() for m in tar if m.isfile()}
    assert {k: sha(v) for k, v in files.items()} == manifest["files"]
    plan_path = "experiments/magicui-argument-routing-probes-v1.json"
    plan = json.loads(files[plan_path])
    pre = json.loads(files[PREFIX + "preexecution.json"])
    assert pre["plan_sha256"] == sha(files[plan_path])
    assert pre["collector_sha256"] == sha(files[PREFIX + "run_probes.py"])
    assert pre["freeze_commit"].startswith("7c5f0af")
    for item in plan["source"]:
        assert sha(files[item["path"]]) == item["sha256"]
    execution = json.loads(files[PREFIX + "execution.json"])
    assert execution["status"] == "completed_requires_review" and execution["stopping"] is None
    assert execution["tool_calls"] == 9 and execution["catalog_calls"] == 3
    assert execution["model_calls"] == execution["model_usd"] == 0
    catalogs = {
        stage: {t["name"]: t for t in json.loads(files[PREFIX + f"{stage}-catalog.json"])["tools"]}
        for stage in ("early", "middle", "late")
    }
    malformed = {"getComponentDetails", "getComponentsByNames", "searchComponents"}
    for stage, catalog in catalogs.items():
        assert (malformed & catalog.keys()) == (malformed if stage == "late" else set())
    for tool in malformed:
        assert catalogs["late"][tool]["inputSchema"] == {"type": "object", "properties": {}}
    rows = json.loads(files[PREFIX + "observations.json"])
    assert len(rows) == len(plan["schedule"]) == 9
    categories, indexes, defects = {}, {}, []
    for index, (row, step) in enumerate(zip(rows, plan["schedule"], strict=True), 1):
        assert row == json.loads(files[PREFIX + f"call-{index:02d}.json"])
        assert row["index"] == index
        for key, value in step.items():
            assert row[key] == value
        assert "exception" not in row
        assert pre["started_utc"] <= row["started_utc"] <= row["ended_utc"] <= execution["ended_utc"]
        result = row["result"]
        value = "\n".join(c.get("text", "") for c in result["content"])
        kind = row["kind"]
        if kind == "details_argument_loss":
            assert result["isError"] is True and 'Component "undefined" not found' in value
            defects.append(row["tool"])
        elif kind == "batch_argument_loss":
            assert result["isError"] is True and "No valid component names" in value
            defects.append(row["tool"])
        else:
            assert result["isError"] is False
            data = json.loads(value)
            if kind == "category":
                selected = next(x for x in data if x["name"] == plan["canary_component"])
                assert 'from "motion/react"' in selected["content"]
                assert "TextAnimate" in selected["content"] and "text-animate.json" in selected["install"]
                assert len(data) == 14
                categories[row["stage"]] = value
            elif kind == "index":
                assert any(x["name"] == plan["canary_component"] for g in data["categories"] for x in g["components"])
                indexes[row["stage"]] = value
            elif kind == "registry":
                assert any(x and x["name"] == plan["canary_component"] for x in data)
            elif kind == "search_argument_loss":
                assert "query" not in data and data["category"] is None
                assert data["resultCount"] == len(data["results"]) == 78
                assert any(x["name"] != plan["canary_component"] for x in data["results"])
                defects.append(row["tool"])
    assert len(set(categories.values())) == len(set(indexes.values())) == 1
    assert set(defects) == malformed
    print(json.dumps({
        "archive_integrity": True, "files": len(files), "frozen_source_files": len(plan["source"]),
        "tool_calls": 9, "catalog_calls": 3, "model_calls": 0, "model_usd": 0,
        "late_argument_loss_tools": defects, "native_category_code_all_stages": True,
        "category_results_byte_identical": True, "index_results_byte_identical": True,
        "agent_improvement_tested": False, "goal_complete": False,
    }, indent=2))


if __name__ == "__main__":
    main()

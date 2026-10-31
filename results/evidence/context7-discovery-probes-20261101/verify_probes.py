"""Offline verification of frozen Context7 native probes; never calls a service."""

import hashlib
import json
import re
import tarfile
from pathlib import Path

FOLDER = Path(__file__).resolve().parent
PREFIX = "results/evidence/context7-discovery-probes-20261101/"


def sha(value):
    return hashlib.sha256(value).hexdigest()


def main():
    manifest = json.loads((FOLDER / "archive-manifest.json").read_text())
    archive = FOLDER / "probe-and-source.tar.gz"
    assert sha(archive.read_bytes()) == manifest["archive_sha256"]
    with tarfile.open(archive) as tar:
        files = {m.name: tar.extractfile(m).read() for m in tar if m.isfile()}
    assert {k: sha(v) for k, v in files.items()} == manifest["files"]
    plan_path = "experiments/context7-discovery-probes-v1.json"
    plan = json.loads(files[plan_path])
    pre = json.loads(files[PREFIX + "preexecution.json"])
    assert pre["plan_sha256"] == sha(files[plan_path])
    assert pre["collector_sha256"] == sha(files[PREFIX + "run_probes.py"])
    for item in plan["source"]:
        assert sha(files[item["path"]]) == item["sha256"]
    execution = json.loads(files[PREFIX + "execution.json"])
    assert execution["status"] == "completed_requires_review"
    assert execution["tool_calls"] == 8 and execution["catalog_calls"] == 3
    assert execution["model_calls"] == execution["model_usd"] == 0
    rows = json.loads(files[PREFIX + "observations.json"])
    assert len(rows) == len(plan["schedule"]) == 8
    ids, searches, docs, defects = {}, [], {}, []
    for index, (row, step) in enumerate(zip(rows, plan["schedule"], strict=True), 1):
        assert row == json.loads(files[PREFIX + f"call-{index:02d}.json"])
        assert row["index"] == index
        for key in ("stage", "kind", "tool"):
            assert row[key] == step[key]
        expected = dict(step["arguments"])
        if row["kind"] == "documentation":
            expected["libraryId"] = ids[row["stage"]]
        assert row["arguments"] == expected
        assert "exception" not in row and row["result"]["isError"] is False
        value = "\n".join(c.get("text", "") for c in row["result"]["content"])
        if row["kind"] == "discovery":
            assert value == (
                "Error fetching popular libraries: ReferenceError: "
                "CONTEXT7_API_BASE_URL is not defined")
            defects.append(row["stage"])
        elif row["kind"] == "resolve":
            match = re.search(r"Context7-compatible library ID:\s*(/[^\s]+)", value)
            assert match
            ids[row["stage"]] = match.group(1)
            searches.append(value)
        else:
            assert "z.string().min(5)" in value
            assert "Validates minimum length" in value
            assert "Source: https://github.com/colinhacks/zod/" in value
            docs[row["stage"]] = value
    assert defects == ["middle", "late"]
    assert ids == execution["library_ids"]
    assert set(ids.values()) == {"/colinhacks/zod"}
    assert len(set(searches)) == 1
    assert docs["middle"] == docs["late"] != docs["early"]
    for stage in ("early", "middle", "late"):
        catalog = json.loads(files[PREFIX + f"{stage}-catalog.json"])
        names = [x["name"] for x in catalog["tools"]]
        assert names == (["resolve-library-id", "query-docs"] if stage == "early" else
                         ["resolve-library-id", "list-popular-libraries", "query-docs"])
    print(json.dumps({
        "archive_integrity": True, "files": len(files), "tool_calls": 8,
        "catalog_calls": 3, "model_calls": 0, "defect_stages": defects,
        "native_alternative_all_stages": True, "search_results_identical": True,
        "docs_middle_late_identical": True, "docs_early_different": True,
        "agent_improvement_tested": False, "goal_complete": False,
    }, indent=2))


if __name__ == "__main__":
    main()

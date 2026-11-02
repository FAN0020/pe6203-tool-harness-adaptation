"""Independent saved-output checker: standard library only, no updater imports."""

import argparse
import hashlib
import json
import tarfile
from copy import deepcopy
from pathlib import Path

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[2]
PREFIX = "results/evidence/native-argument-routing-updater-20261101/"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def verify(read):
    def load(path):
        return json.loads(read(path))

    spec = load("experiments/native-argument-routing-updater-v1.json")
    catalogs = load(spec["catalog_fixture"])
    assert sha(read(spec["catalog_fixture"])) == spec["catalog_fixture_sha256"]
    for stage in ("early", "middle", "late"):
        native = load(f"results/evidence/magicui-argument-routing-probes-20261101/{stage}-catalog.json")
        expected = {t["name"]: t for t in native["tools"]}
        assert len(catalogs[stage]["tools"]) == len(expected)
        for tool in catalogs[stage]["tools"]:
            original = expected[tool["name"]]
            assert tool["parameters"] == original["inputSchema"]
            assert tool["description"] == original["description"]
            assert tool["output_schema"] == original.get("outputSchema")
            assert tool["usage_rules"] == []
    for item in spec["source"]:
        assert sha(read(item["path"])) == item["sha256"]
    execution = load(PREFIX + "offline-records/execution.json")
    assert execution["implementation_commit"].startswith("cee763a")
    assert execution["case_count"] == 4 and execution["adaptations"] == 8
    assert execution["agent_calls"] == execution["judge_calls"] == execution["native_calls"] == 0
    for item in execution["source"]:
        assert sha(read(item["path"])) == item["sha256"]
    protected = {item["path"]: item["sha256"] for item in spec["offline_input_source"]}
    for name in ("src/pe6203/selective.py", "src/pe6203/baselines.py"):
        assert sha(read(name)) == protected[name]
    assert sha(read(PREFIX + "test-before-identity-correction.py")) == protected[
        "tests/test_native_argument_routing.py"]
    provenance = load(PREFIX + "retention-source-provenance.json")
    for item in provenance["rows"]:
        assert sha(read(item["copy"])) == item["sha256"]
    rows = load(PREFIX + "offline-records/results.json")
    assert [r["name"] for r in rows] == [
        "magicui-early", "magicui-middle", "magicui-late", "retention-235"]
    counts = {}
    for row in rows:
        name = row["name"]
        base = row["selective_patch"]
        candidate = row["native_argument_routing"]
        expected = deepcopy(base["knowledge"])
        edits = spec["annotations"] if name == "magicui-late" else {}
        for tool in expected["tools"]:
            if tool["tool_id"] in edits:
                entry = edits[tool["tool_id"]]
                contract = {k: tool[k] for k in spec["contract_fingerprint_fields"]}
                assert sha(canonical(contract).encode()) == entry["native_contract_sha256"]
                assert tool["description"] == entry["before"]
                tool["description"] = entry["after"]
        assert candidate["knowledge"] == expected
        assert base["model_routes"] == candidate["model_routes"]
        assert len(base["model_tools"]) == len(candidate["model_tools"]) == len(expected["tools"])
        records = {(t["server_id"], t["name"]): t for t in expected["tools"]}
        changed_model_descriptions = 0
        for left, right in zip(base["model_tools"], candidate["model_tools"], strict=True):
            previous, current = left["function"], right["function"]
            assert left["type"] == right["type"] == "function"
            restored = deepcopy(current)
            changed_model_descriptions += previous["description"] != current["description"]
            restored["description"] = previous["description"]
            assert restored == previous
            route = candidate["model_routes"][current["name"]]
            record = records[(route["server_id"], route["tool_name"])]
            assert current["parameters"] == record["parameters"]
            if record["tool_id"] in edits:
                assert current["description"] == edits[record["tool_id"]]["after"]
        assert changed_model_descriptions == len(edits)
        for strategy in ("selective_patch", "native_argument_routing"):
            value = row[strategy]
            assert value["cost"]["calls"] == value["cost"]["total_tokens"] == value["cost"]["usd"] == 0
            saved = read(PREFIX + f"offline-records/{name}-{strategy}-knowledge.json")
            assert json.loads(saved) == value["knowledge"]
            if name == "retention-235":
                assert saved == read(PREFIX + "retention-early.json")
        annotations = [c for c in candidate["changes"]
                       if c["operation"] == "reconcile_native_argument_routing"]
        assert len(annotations) == len(edits)
        counts[name] = len(edits)
    return {"recorded_catalogs_verified": True, "case_count": 4, "adaptations": 8,
            "description_changes": counts, "model_parameters_and_routes_unchanged": True,
            "retention_235_exact_k0_bytes": True, "updater_model_calls_tokens_usd": 0,
            "native_agent_judge_calls": 0, "task_improvement_verified": False, "goal_complete": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Check files before sealing the archive")
    args = parser.parse_args()
    if args.live:
        result = verify(lambda path: (ROOT / path).read_bytes())
    else:
        manifest = json.loads((FOLDER / "archive-manifest.json").read_text())
        archive = FOLDER / "offline-and-source.tar.gz"
        assert sha(archive.read_bytes()) == manifest["archive_sha256"]
        with tarfile.open(archive) as tar:
            files = {m.name: tar.extractfile(m).read() for m in tar if m.isfile()}
        assert {k: sha(v) for k, v in files.items()} == manifest["files"]
        result = verify(files.__getitem__)
        result.update(archive_integrity=True, archived_files=len(files))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

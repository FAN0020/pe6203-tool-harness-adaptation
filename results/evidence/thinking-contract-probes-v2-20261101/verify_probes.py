"""Recheck archived native probe outputs with the Python standard library only."""
import hashlib
import json
import tarfile
from pathlib import Path

FOLDER = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    manifest = json.loads((FOLDER / "archive-manifest.json").read_text())
    archive = FOLDER / "probe-and-source.tar.gz"
    assert sha(archive.read_bytes()) == manifest["archive_sha256"]
    with tarfile.open(archive) as tar:
        files = {m.name: tar.extractfile(m).read() for m in tar if m.isfile()}
    assert {k: sha(v) for k, v in files.items()} == manifest["files"]

    def read(name):
        return json.loads(files[name])

    v1 = "results/evidence/thinking-contract-probes-20261101/"
    v2 = "results/evidence/thinking-contract-probes-v2-20261101/"
    for stage in ("early", "middle"):
        for index in (1, 2):
            r = read(v1 + f"{stage}/{index:02d}-sequentialthinking.json")["result"]
            assert not r.get("isError")
            assert r["structuredContent"]["thoughtHistoryLength"] == index
    failure = read(v1 + "first-attempt.json")
    assert failure["tool_calls_executed"] == 6
    assert sha(files[v1 + "run.log"]) == failure["log_sha256"]
    assert b"Additional properties are not allowed ('pathsSummary', 'synthesisReady'" in files[v1 + "run.log"]
    late = read(v1 + "late-observations.json")
    assert len(late) == 6
    for row in late[:2]:
        assert row["result"]["isError"]
        assert row["result"]["content"][0]["text"] == "thinkingServer.getThoughtHistory is not a function"
    assert late[2]["client_exception"] is None
    assert late[3]["result"]["structuredContent"]["pathsSummary"][0]["thoughtCount"] == 2
    assert "pathsSummary" in late[3]["client_exception"]["message"]
    for row in late[4:]:
        assert "synthesisData" in row["client_exception"]["message"]
    assert late[5]["result"]["structuredContent"]["synthesizedConclusion"] == "UNVERIFIED_SENTINEL_43"
    assert late[5]["result"]["structuredContent"]["synthesisData"]["sourcePaths"] == ["absent_path"]
    plan = read("experiments/thinking-contract-probes-v2.json")
    for item in plan["source"]:
        assert sha(files[item["path"]]) == item["sha256"]
    rows = read(v2 + "observations.json")
    assert len(rows) == 7
    for row in rows:
        assert not row["result"].get("isError")
        if row["kind"] == "notebook":
            state = row["result"]["structuredContent"]
            assert row["arguments"]["readyForSynthesis"] is False
            assert state["activePaths"] == (["synthetic_one"] if row["index"] == 1 else [])
            assert state["pathStatus"] == ("active" if row["index"] == 1 else "completed")
            assert "synthesisReady" not in state and "pathsSummary" not in state
        else:
            fixture = v2 + f"workspaces/{row['stage']}-csv/anotation_path/csv/customers-100.csv"
            assert sha(files[fixture]) == plan["csv_readiness"]["fixture_sha256"]
            expected = "\n".join(files[fixture].decode().splitlines()[:4])
            texts = "\n".join(x.get("text", "") for x in row["result"]["content"])
            assert expected in texts.replace("\r\n", "\n")
    print(json.dumps({"verified": True, "archive_files": len(files), "tool_calls": 19,
                     "catalog_calls": 8, "model_calls": 0, "v1_failure_preserved": True,
                     "late_missing_method_confirmed": True, "native_output_schema_failures_confirmed": True,
                     "schema_compatible_terminal_path": True, "csv_readiness": True,
                     "agent_efficacy": "not_tested"}, indent=2))


if __name__ == "__main__":
    main()

"""Offline verification of failed readiness, not verification of filter behavior."""
import hashlib
import json
import tarfile
from pathlib import Path

FOLDER = Path(__file__).resolve().parent


def sha(value):
    return hashlib.sha256(value).hexdigest()


def main():
    manifest = json.loads((FOLDER / "archive-manifest.json").read_text())
    archive = FOLDER / "probe-and-source.tar.gz"
    assert sha(archive.read_bytes()) == manifest["archive_sha256"]
    with tarfile.open(archive) as tar:
        files = {m.name: tar.extractfile(m).read() for m in tar if m.isfile()}
    assert {k: sha(v) for k, v in files.items()} == manifest["files"]

    def read(name):
        return json.loads(files[name])

    prefixes = ["results/evidence/city-station-filter-probes-20261101",
                "results/evidence/city-station-filter-probes-v2-20261101"]
    plans = ["experiments/city-station-filter-probes-v1.json",
             "experiments/city-station-filter-probes-v2.json"]
    for prefix, plan_name in zip(prefixes, plans, strict=True):
        execution = read(prefix + "/execution.json")
        assert execution["status"] == "stopped_readiness_unestablished"
        assert execution["tool_calls"] == execution["catalog_calls"] == 0
        assert execution["model_calls"] == execution["model_usd"] == 0
        pre = read(prefix + "/preexecution.json")
        assert pre["plan_sha256"] == sha(files[plan_name])
        assert pre["collector_sha256"] == sha(files[prefix + "/run_probes.py"])
        for item in read(plan_name)["source"]:
            assert sha(files[item["path"]]) == item["sha256"]
    first = read(prefixes[0] + "/execution.json")
    assert "no reviewed runtime profile" in first["stopping"]["message"]
    log = files[prefixes[1] + "/early-stderr.log"].decode()
    assert "getLCQueryPath" in log and "Error: get station name js file failed." in log
    source = files[".cache/mcpevol/original/node_modules/12306-mcp/build/index.js"].decode()
    assert "const LCQUERY_PATH = await getLCQueryPath()" in source
    assert "html.match(/ var lc_search_url = '(.+?)'/)" in source
    profile = read("configs/server-profiles.json")
    assert profile["servers"]["12306-mcp"] == {"entry": "build/index.js"}
    review = read(prefixes[1] + "/mechanism-review.json")
    assert review["status"] == "native_startup_unavailable_mechanism_unverified"
    print(json.dumps({"verified_archive_integrity": True, "files": len(files),
                      "tool_calls": 0, "catalog_calls": 0, "model_calls": 0,
                      "mechanism_proven": False, "goal_complete": False,
                      "decision": "No agent trial; native Early initialization failed."}, indent=2))


if __name__ == "__main__":
    main()

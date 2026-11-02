"""Read-only, offline evidence verification; no model/native calls."""
import hashlib
import json
from pathlib import Path
from urllib.parse import unquote
import re

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    freeze = read(HERE / "admission-freeze.json")
    index = read(HERE / "evidence-index.json")
    for mapping in (freeze["files"], index["files"]):
        for name, expected in mapping.items():
            assert sha(ROOT / name) == expected, name
    sources = read(HERE / "sources/file-manifest.json")
    repos = {x["repo"]: x for x in read(HERE / "sources/repo-index.json")}
    for item in sources:
        repo = repos[item["repo"]]
        assert repo["sha"] == item["sha"]
        path = HERE / "sources" / repo["id"] / item["path"]
        assert path.stat().st_size == item["bytes"] and sha(path) == item["sha256"]
    result = read(HERE / "admission-result.json")
    assert result["status"] == "not_ready_for_agent_trial"
    assert result["model_calls"] == result["native_mcp_calls"] == result["usd"] == 0
    assert not result["goal_complete"]
    assert all(result[k] is None for k in ("TF", "PE", "ECS", "agent_completion"))
    protocol = read(ROOT / "experiments/verified-component-memory-admission-v1.json")
    count = 0
    for source, selection in zip(protocol["sources"], result["selections"], strict=True):
        native = read(ROOT / source["path"])
        records = [x for b in native["result"]["content"] if b["type"] == "text" for x in json.loads(b["text"])]
        chosen = min(records, key=lambda x: (len(x["content"].encode()), x["name"]))
        path = HERE / "selected-programs" / source["category"]
        assert chosen == read(path / "native-record.json")
        assert chosen["content"] == (path / "selected.tsx").read_text()
        assert chosen["name"] == selection["name"]
        assert sha(path / "selected.tsx") == selection["code_sha256"]
        assert selection["node_parse_exit_code"] != 0 and not selection["dependency_resolution_pass"]
        assert selection["rendered_effect"] == "not_verified" and not selection["admitted"]
        assert "SyntaxError" in (path / "node-check.stderr.txt").read_text()
        count += len(records)
    assert count == 23 and result["selected_code_bytes"] == 2481
    assert result["byte_bound_pass"]
    projection = read(ROOT / "results/evidence/extensions/magicui-log-dashboard-v1/mechanism-projection.json")
    for cell, bound in zip(projection, result["context_bounds"], strict=True):
        a, b = [cell["responses"][i]["usage"]["prompt_tokens"] for i in (0, -1)]
        assert bound["cell"] == cell["cell"] and bound["gross_static_share_percent"] == 100*a/b
    report = ROOT / "reports/method-learning-and-program-memory.html"
    links = re.findall(r'href="([^"]+)"', report.read_text())
    local = [x for x in links if not x.startswith("https://")]
    assert all((report.parent / unquote(x)).is_file() for x in local)
    methods = read(HERE / "method-review.json")["papers"]
    for method in methods:
        for pointer in method["code"]:
            file, line = pointer.rsplit(":", 1)
            assert int(line) <= len((HERE / "sources" / method["id"] / file).read_text().splitlines())
    print(json.dumps({"verified": True, "frozen_inputs": len(freeze["files"]),
                      "targeted_historical_sources": len(index["files"]),
                      "official_source_and_license_files": len(sources), "paper_versions": len(methods),
                      "native_components_considered": count, "selected_programs": 2,
                      "local_report_links": len(local), "model_calls": 0, "usd": 0,
                      "goal_complete": False}, indent=2))


if __name__ == "__main__":
    main()

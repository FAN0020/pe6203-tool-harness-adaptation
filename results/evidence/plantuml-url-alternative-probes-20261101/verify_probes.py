"""Verify dependency readiness, retained file-save failure and distinct URL alternative."""
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

    prefix = "results/evidence/"
    old = prefix + "icon-task-dependencies-probes-20261101/"
    new = prefix + "plantuml-url-alternative-probes-20261101/"
    for folder, plan in [(old, "icon-task-dependencies-probes-v1"),
                         (new, "plantuml-url-alternative-probes-v1")]:
        plan_path = "experiments/" + plan + ".json"
        pre = read(folder + "preexecution.json")
        assert pre["plan_sha256"] == sha(files[plan_path])
        assert pre["collector_sha256"] == sha(files[folder + "run_probes.py"])
        for entry in read(plan_path)["source"]:
            assert sha(files[entry["path"]]) == entry["sha256"]
    first, second = read(old + "execution.json"), read(new + "execution.json")
    assert first["tool_calls"] == 9 and first["catalog_calls"] == 6
    assert first["status"] == "stopped_readiness_unestablished"
    assert first["stopping"]["stage"] == "late"
    assert second["tool_calls"] == second["catalog_calls"] == 1
    assert second["status"] == "completed_requires_review"
    assert first["model_calls"] == second["model_calls"] == 0
    pngs, urls, docs, examples = [], [], [], []
    for stage in ["early", "middle", "late"]:
        values = []
        for i in [1, 2, 3]:
            row = read(old + f"{stage}-{i:02d}.json")
            content = "\n".join(c.get("text", "") for c in row["result"]["content"])
            values.append(content)
            if i < 3:
                assert not row["result"].get("isError")
                assert "Button" in content and ("API" if i == 1 else "import") in content
            elif stage == "late":
                assert row["result"]["isError"] is True
                assert "response is not defined" in content
            else:
                result = json.loads(content)
                assert result["success"] is True
                urls.append(result["url"])
                png = files[old + f"workspaces/{stage}/probe.png"]
                assert png.startswith(b"\x89PNG\r\n\x1a\n")
                pngs.append(png)
        docs.append(values[0])
        examples.append(values[1])
    row = read(new + "late-01.json")
    assert not row["result"].get("isError")
    result = json.loads(row["result"]["content"][0]["text"])
    assert result["success"] is True and "local_path" not in result
    assert result["url"] == urls[0] == urls[1]
    assert pngs[0] == pngs[1]
    assert docs[0] == docs[1] == docs[2] and examples[0] == examples[1] == examples[2]
    print(json.dumps({"archive_integrity": True, "files": len(files),
                      "tool_calls": 10, "catalog_calls": 7, "model_calls": 0,
                      "antd_dependency_ready": True, "late_file_save_regression": True,
                      "late_url_alternative": True, "identical_rendered_canary": True,
                      "agent_benefit_tested": False, "goal_complete": False}, indent=2))


if __name__ == "__main__":
    main()

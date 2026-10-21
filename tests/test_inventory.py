"""The inventory must account for every selected task without inventing server mappings."""

import json
from zipfile import ZipFile

from test_contract import module


def test_inventory_keeps_missing_servers_and_excludes_reference_data(tmp_path):
    upstream, cache = tmp_path / "upstream", tmp_path / "cache"
    data = upstream / "src/custom/data/test_cases"
    data.mkdir(parents=True)
    cache.mkdir()
    (data / "chosen_idx.json").write_text(json.dumps({"samples": [{"idx": 1}, {"idx": 2}]}))
    (data / "test_cases.json").write_text(
        json.dumps(
            [
                {
                    "idx": 1,
                    "question": "Local task",
                    "servers": {"local": ["read"]},
                    "answer": "ORACLE",
                },
                {
                    "idx": 2,
                    "question": "External task",
                    "servers": {"missing-alias": [], "python": []},
                    "trajectory_messages": ["ORACLE"],
                },
                {"idx": 3, "question": "Not selected", "servers": {"excluded": []}},
            ]
        )
    )
    (data / "status_dict.json").write_text(json.dumps({"local": {"tools": [{"name": "read"}]}}))
    lock = {"commit": "pinned", "dataset_revision": "release", "stages": {}}
    for stage, directory in [("early", "original"), ("middle", "iter3"), ("late", "iter5")]:
        config = upstream / f"servers/1mcp_config/{directory}/mcp.json"
        config.parent.mkdir(parents=True)
        config.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "local": {
                            "command": "npx",
                            "args": ["-y", "local"],
                            "env": {"API_KEY": "DO-NOT-PUBLISH"},
                        },
                        "python": {"command": "uvx", "args": ["unlocked-python-server"]},
                    }
                }
            )
        )
        archive = stage + ".zip"
        lock["stages"][stage] = {"directory": directory, "archive": archive, "sha256": "audit-only"}
        with ZipFile(cache / archive, "w") as z:
            z.writestr(
                "node_modules/local/package.json",
                json.dumps({"name": "local", "version": "1", "bin": {"local": "main.js"}}),
            )
            if stage != "late":
                z.writestr("node_modules/local/main.js", "// released code")
    report = module("inventory").build_inventory(upstream, lock, cache)
    assert [x["task_id"] for x in report["tasks"]] == [1, 2]
    assert report["summary"]["task_server_names"] == 3
    servers = {s["server_id"]: s for s in report["servers"]}
    assert servers["missing-alias"]["stages"]["early"]["status"] == "missing_config"
    assert servers["python"]["stages"]["early"]["status"] == "not_in_node_archive"
    assert servers["local"]["stages"]["early"]["status"] == "entry_available"
    assert servers["local"]["stages"]["late"]["status"] == "missing_entry"
    assert servers["local"]["stages"]["early"]["env_names"] == ["API_KEY"]
    text = json.dumps(report)
    assert "ORACLE" not in text and "DO-NOT-PUBLISH" not in text
    assert "excluded" not in text


def test_all_archive_extraction_rejects_escape_before_writing(tmp_path):
    archive = tmp_path / "release.zip"
    with ZipFile(archive, "w") as z:
        z.writestr("node_modules/a/package.json", '{"name":"a","version":"1"}')
        z.writestr("node_modules/a/index.js", "released")
    result = module("bootstrap").extract_all(archive, tmp_path / "installed")
    assert (tmp_path / "installed/node_modules/a/index.js").read_text() == "released"
    assert result["files"] == 2
    with ZipFile(archive, "a") as z:
        z.writestr("node_modules/../../escape", "bad")
    import pytest

    with pytest.raises(ValueError, match="Unsafe"):
        module("bootstrap").extract_all(archive, tmp_path / "bad")
    assert not (tmp_path / "bad/node_modules/a/index.js").exists()


def test_all_archive_preserves_release_root_lockfiles(tmp_path):
    archive = tmp_path / "release.zip"
    with ZipFile(archive, "w") as z:
        z.writestr("package.json", '{"name":"released-root"}')
        z.writestr("package-lock.json", '{"lockfileVersion":3}')
    module("bootstrap").extract_all(archive, tmp_path / "out")
    assert json.loads((tmp_path / "out/package-lock.json").read_text())["lockfileVersion"] == 3

import json
from pathlib import Path

import pytest
from test_contract import module


def test_launch_profile_uses_pinned_entry_and_isolated_env(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_API_KEY", "NEVER-INHERIT")
    entry = tmp_path / ".cache/mcpevol/iter3/node_modules/local/index.js"
    entry.parent.mkdir(parents=True)
    entry.write_text("// archived server")
    workspace = tmp_path / "run"
    profile = {
        "entry": "index.js",
        "args": ["{workspace}"],
        "env": {"STATE": "{workspace}/state.json"},
    }
    parameters = module("transport").launch_parameters(
        tmp_path, "iter3", "local", workspace, profile
    )
    assert parameters.args == [str(entry), str(workspace)]
    assert parameters.cwd == str(workspace)
    assert parameters.env["STATE"] == str(workspace / "state.json")
    assert Path(parameters.env["HOME"]).is_relative_to(workspace)
    assert "NEVER-INHERIT" not in json.dumps(parameters.env)
    with pytest.raises(ValueError, match="entry"):
        module("transport").launch_parameters(
            tmp_path, "iter3", "local", workspace, {"entry": "../../../outside.js"}
        )


def test_task_file_arguments_cannot_escape_workspace_even_through_symlinks(tmp_path):
    workspace = tmp_path / "run"
    workspace.mkdir()
    (workspace / "escape").symlink_to(tmp_path)
    check = module("transport").check_arguments
    check({"source_path": "tasks.md", "workspace": str(workspace)}, workspace)
    for path in ["../outside.md", "escape/outside.md", str(tmp_path / "outside.md")]:
        with pytest.raises(ValueError, match="workspace"):
            check({"source_path": path}, workspace)


def test_profile_manifest_is_pinned_and_missing_servers_are_explicit(tmp_path):
    config = tmp_path / "configs/server-profiles.json"
    config.parent.mkdir()
    config.write_text(
        json.dumps({"benchmark_commit": "pin", "servers": {"local": {"entry": "index.js"}}})
    )
    load = module("transport").server_profiles
    assert "local" in load(tmp_path, {"commit": "pin", "servers": {}})
    with pytest.raises(ValueError, match="commit"):
        load(tmp_path, {"commit": "different", "servers": {}})

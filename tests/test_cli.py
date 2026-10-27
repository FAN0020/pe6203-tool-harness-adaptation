import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from test_contract import module

ROOT = Path(__file__).resolve().parents[1]


def test_cli_help_exposes_handoff_commands():
    result = subprocess.run(
        [sys.executable, "-m", "pe6203.cli", "--help"], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    for command in ["bootstrap", "metadata", "probe", "run", "ecs", "doctor"]:
        assert command in result.stdout


@pytest.mark.integration
@pytest.mark.parametrize("version", ["early", "middle", "late"])
def test_released_mcp_services_write_and_reload_real_state(tmp_path, version):
    if not (ROOT / ".cache/mcpevol/original/extraction.json").exists():
        pytest.skip("Run pe6203 bootstrap to install the pinned real services")
    node = ROOT / ".cache/node-runtime/node_modules/node/bin/node"
    env = {**os.environ, **({"MCPEVOL_NODE": str(node)} if node.exists() else {})}
    output = tmp_path / version
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pe6203.cli",
            "probe",
            "--version",
            version,
            "--output",
            str(output),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    evidence = json.loads((output / "probe.json").read_text())
    assert evidence["kind"] == "real_mcp_transport_probe"
    assert evidence["TF"] is None and evidence["PE"] is None
    assert evidence["persistent_state_verified"] is True
    assert len(evidence["calls"]) >= 4
    assert all(not call["result"].get("isError", False) for call in evidence["calls"])


def test_missing_credentials_are_saved_as_blocked_not_scores(tmp_path, monkeypatch):
    if not (ROOT / ".cache/mcpevol/upstream/.git").exists():
        pytest.skip("Requires the pinned upstream checkout")
    config = json.loads((ROOT / "configs/full-catalog-smoke.json").read_text())
    config.update(root=str(ROOT), output_dir=str(tmp_path / "missing-credentials"))
    monkeypatch.delenv("AGENT_API_KEY", raising=False)
    _, result = module("runner").run(139, "early", "no_update", 0, config)
    assert result["status"] == "blocked"
    assert result["TF"] is None and result["PE"] is None
    assert "AGENT_API_KEY" in result["errors"][0]["message"]
    assert (Path(config["output_dir"]) / "result.json").exists()
    assert "blocked" in (Path(config["output_dir"]) / "report.txt").read_text()
    with pytest.raises(FileExistsError):
        module("runner").run(139, "early", "no_update", 0, config)

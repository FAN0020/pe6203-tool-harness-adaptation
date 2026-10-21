from contextlib import asynccontextmanager

import pytest
from test_contract import module


@pytest.mark.asyncio
async def test_server_audit_records_failed_startup_and_continues(tmp_path, monkeypatch):
    audit = module("audit")
    monkeypatch.setattr(
        audit, "source", lambda root: ({"commit": "pin", "dataset_revision": "release"}, tmp_path)
    )
    monkeypatch.setattr(audit, "server_profiles", lambda root, lock: {"broken": {}, "working": {}})

    @asynccontextmanager
    async def sessions(root, stage, servers, workspace, stderr, timeout):
        if servers == ["broken"]:
            raise RuntimeError("required dependency missing")
        yield {"working": object()}

    async def snapshot(clients, stage, commit):
        return {"tools": [{"name": "read"}], "version": stage, "benchmark_commit": commit}

    monkeypatch.setattr(audit, "sessions", sessions)
    monkeypatch.setattr(audit, "snapshot", snapshot)
    result = await audit.probe_servers(tmp_path, ["early"], tmp_path / "output")
    assert [r["status"] for r in result["servers"]] == ["failed", "catalog_verified"]
    assert "required dependency missing" in result["servers"][0]["error"]
    assert result["servers"][1]["tool_count"] == 1
    assert (tmp_path / "output/server-probes.json").exists()
    assert result["model_used"] is None


def test_catalog_cli_reports_nonzero_when_any_server_fails(tmp_path, monkeypatch, capsys):
    cli = module("cli")

    async def probe(*args):
        return {"servers": [{"status": "failed"}, {"status": "catalog_verified"}]}

    monkeypatch.setattr(cli, "probe_servers", probe)
    monkeypatch.setattr("sys.argv", ["pe6203", "probe-servers", "--output", str(tmp_path / "out")])
    assert cli.main() == 2
    assert '"verified": 1' in capsys.readouterr().out

from pathlib import Path

import httpx
import pytest
from mcp.types import CallToolResult, TextContent


def test_netlify_only_uploads_generated_html_as_draft(tmp_path, monkeypatch):
    from pe6203 import netlify

    commands = []

    def cli_boundary(root, arguments, **kwargs):
        commands.append(arguments)
        directory = Path(arguments[arguments.index("--dir") + 1])
        assert (directory / "index.html").read_text() == "<h1>Papers</h1>"
        assert list(directory.iterdir()) == [directory / "index.html"]
        return {"deploy_url": "https://draft--example.netlify.app", "deploy_id": "d1"}

    monkeypatch.setattr(netlify, "command_json", cli_boundary)
    monkeypatch.setattr(
        netlify.httpx, "get", lambda *a, **k: httpx.Response(200, text="<h1>Papers</h1>")
    )
    url = netlify.publish_html(tmp_path, tmp_path / "workspace", "<h1>Papers</h1>", "site-123")
    assert url == "https://draft--example.netlify.app"
    assert "--prod" not in commands[0]
    assert "--no-build" in commands[0]
    assert commands[0][commands[0].index("--site") + 1] == "site-123"
    assert len(list((tmp_path / "workspace").rglob("deployment.json"))) == 1


def test_publish_failure_never_returns_a_fake_url(tmp_path, monkeypatch):
    from pe6203 import netlify

    monkeypatch.setattr(netlify, "command_json", lambda *a, **k: {})
    with pytest.raises(ValueError, match="URL"):
        netlify.publish_html(tmp_path, tmp_path / "workspace", "<html>test</html>", "site-123")


def test_inaccessible_deployment_is_recorded_as_failure(tmp_path, monkeypatch):
    from pe6203 import netlify

    monkeypatch.setattr(
        netlify,
        "command_json",
        lambda *a, **k: {"deploy_url": "https://draft--example.netlify.app"},
    )
    monkeypatch.setattr(netlify.httpx, "get", lambda *a, **k: httpx.Response(401))
    with pytest.raises(ValueError, match="public"):
        netlify.publish_html(tmp_path, tmp_path / "workspace", "<html>test</html>", "site-123")
    assert len(list((tmp_path / "workspace").rglob("deployment.json"))) == 1


@pytest.mark.asyncio
async def test_replay_keeps_stage_fetcher_and_rejects_unfrozen_urls(tmp_path):
    from pe6203.benchmark import write_json
    from pe6203.experiment import sha
    from pe6203.netlify import FrozenSourceClient, replay_source

    page = tmp_path / "page.html"
    page.write_text("<html><h1>Frozen papers</h1></html>")
    manifest = tmp_path / "manifest.json"
    write_json(
        manifest, {"url": "https://example.org/papers", "file": "page.html", "sha256": sha(page)}
    )

    class FetcherBoundary:
        async def call_tool(self, name, args):
            assert name == "fetch_url"
            assert args["timeout"] == 4321
            async with httpx.AsyncClient() as client:
                response = await client.get(args["url"])
            return CallToolResult(content=[TextContent(type="text", text=response.text)])

    records = [
        {
            "server_id": "fetcher-mcp",
            "name": "fetch_url",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}, "timeout": {"type": "number"}},
                "required": ["url"],
            },
        }
    ]
    with replay_source(manifest) as frozen:
        wrapped = FrozenSourceClient(FetcherBoundary(), records, frozen)
        result = await wrapped.call_tool(
            "fetch_url", {"url": "https://example.org/papers", "timeout": 4321}
        )
        assert "Frozen papers" in result.content[0].text
        result = await wrapped.call_tool("fetch_url", {"url": "https://different.example.org"})
        assert result.isError
    page.write_text("tampered")
    with pytest.raises(ValueError, match="hash"):
        with replay_source(manifest):
            pass


@pytest.mark.asyncio
async def test_netlify_proxy_enforces_target_schema_before_upload(tmp_path, monkeypatch):
    from pe6203 import netlify

    def never_upload(*args):
        pytest.fail("Invalid tool arguments must not reach Netlify")

    monkeypatch.setattr(netlify, "publish_html", never_upload)
    records = [
        {
            "server_id": "edgeone-pages-mcp",
            "name": "deploy_html",
            "parameters": {
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
            },
        }
    ]
    client = netlify.NetlifyClient(tmp_path, tmp_path, "site-123", records)
    result = await client.call_tool("deploy_html", {"html": "wrong parameter"})
    assert result.isError

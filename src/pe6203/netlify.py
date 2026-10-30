"""Explicit task223 variant: frozen source, released fetcher, Netlify draft publishing.

Netlify credentials remain in its own CLI login store (or NETLIFY_AUTH_TOKEN).
Neither the model nor archived MCP child processes receive these credentials.
"""

import asyncio
import copy
import hashlib
import json
import os
import subprocess
import threading
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from jsonschema import Draft202012Validator, ValidationError
from mcp.types import CallToolResult, TextContent

from .benchmark import read_json, write_json

NETLIFY_VERSION = "23.15.1"
DEFAULT_SOURCE = "https://arxiv.org/search/?query=embodied+ai&searchtype=all&abstracts=show&order=-announced_date_first&size=50"


def cli_command(root):
    entry = Path(root) / "tools/netlify/node_modules/netlify-cli/bin/run.js"
    if not entry.is_file():
        raise FileNotFoundError("Run ./experiment netlify install first")
    return [os.environ.get("MCPEVOL_NODE", "node"), str(entry)]


def cli_environment():
    allowed = (
        "HOME",
        "PATH",
        "TMPDIR",
        "SYSTEMROOT",
        "APPDATA",
        "XDG_CONFIG_HOME",
        "NETLIFY_AUTH_TOKEN",
    )
    return {
        **{k: os.environ[k] for k in allowed if k in os.environ},
        "NETLIFY_TELEMETRY_DISABLED": "1",
        "NO_UPDATE_NOTIFIER": "1",
    }


def command_json(root, arguments, cwd=None, timeout=180):
    completed = subprocess.run(
        cli_command(root) + arguments,
        cwd=cwd or root,
        env={**cli_environment(), "CI": "true"},
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if completed.returncode:
        raise ValueError(
            "Netlify command failed. Run ./experiment netlify login and link; inspect site permissions/network."
        )
    try:
        return json.loads(completed.stdout)
    except ValueError as exc:
        raise ValueError("Netlify did not return valid JSON") from exc


def site_id(root):
    value = os.environ.get("NETLIFY_SITE_ID")
    state = Path(root) / ".netlify/state.json"
    if not value and state.is_file():
        value = read_json(state).get("siteId")
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            "Run ./experiment netlify login, then ./experiment netlify link to select your experiment site"
        )
    return value


def check_setup(root, site):
    if not site:
        raise ValueError("A dedicated Netlify experiment site is required")
    info = command_json(root, ["api", "getSite", "--data", json.dumps({"site_id": site})])
    if info.get("id") != site:
        raise ValueError("Netlify could not verify access to the selected experiment site")


def ensure_runtime(root):
    """Install missing pinned dependencies before entering the interactive login flow."""
    from .bootstrap import bootstrap
    from .experiment import STAGES, configure_runtime

    root = Path(root).resolve()
    node = root / ".cache/node-runtime/node_modules/node/bin/node"
    if not node.exists():
        subprocess.run(
            [
                "npm",
                "install",
                "--prefix",
                str(root / ".cache/node-runtime"),
                "--no-audit",
                "--no-fund",
                "node@24.13.0",
            ],
            check=True,
            cwd=root,
        )
    configure_runtime(root)
    lock = read_json(root / "configs/benchmark.lock.json")
    missing = [
        v
        for v in STAGES
        if any(
            not (
                root / ".cache/mcpevol" / lock["stages"][v]["directory"] / "node_modules" / entry
            ).is_file()
            for entry in (
                "fetcher-mcp/build/index.js",
                "edgeone-pages-mcp/dist/index.js",
                "playwright/cli.js",
            )
        )
    ]
    if missing:
        print("安装缺少的锁定 MCP 发布包（首次可能下载数 GB）", flush=True)
        bootstrap(root, missing, scope="all")
    cli = root / "tools/netlify/node_modules/netlify-cli/bin/run.js"
    if not cli.is_file() or not list((root / ".cache/playwright").glob("chromium-*")):
        if setup(root, "install"):
            raise ValueError(
                "依赖安装失败；修复网络后重新运行 ./experiment papers，已下载内容会保留"
            )


def setup_wizard(root):
    ensure_runtime(root)
    try:
        command_json(root, ["api", "getCurrentUser"])
    except ValueError:
        print("请在浏览器完成 Netlify 登录；完成后 CLI 自动继续。", flush=True)
        if setup(root, "login"):
            raise ValueError("Netlify 登录未完成；重新运行 ./experiment papers 可继续")
        command_json(root, ["api", "getCurrentUser"])
    try:
        site = site_id(root)
    except ValueError:
        print("请选择你已创建的专用实验站点；只发布 draft。", flush=True)
        if setup(root, "link"):
            raise ValueError("站点关联未完成；重新运行 ./experiment papers 可继续")
        site = site_id(root)
    check_setup(root, site)
    return site


def setup(root, action):
    root = Path(root).resolve()
    if action == "install":
        result = subprocess.run(
            ["npm", "ci", "--prefix", str(root / "tools/netlify"), "--no-audit", "--no-fund"],
            cwd=root,
        )
        if result.returncode:
            return result.returncode
        # All stages resolve to the same pinned Playwright package in this release.
        for stage in ("original", "iter3", "iter5"):
            playwright = root / ".cache/mcpevol" / stage / "node_modules/playwright/cli.js"
            if not playwright.is_file():
                raise FileNotFoundError("Run uv run pe6203 bootstrap --scope all first")
            result = subprocess.run(
                [os.environ.get("MCPEVOL_NODE", "node"), str(playwright), "install", "chromium"],
                env={
                    **cli_environment(),
                    "PLAYWRIGHT_BROWSERS_PATH": str(root / ".cache/playwright"),
                },
                cwd=root,
            )
            if result.returncode:
                return result.returncode
        return 0
    if action not in ("login", "link", "status"):
        raise ValueError("Expected install, login, link or status")
    # Browser login and site selection are deliberately performed by the user.
    return subprocess.run(cli_command(root) + [action], cwd=root, env=cli_environment()).returncode


def publish_html(root, workspace, html, site):
    if not isinstance(html, str) or not html.strip() or len(html.encode()) > 4_000_000:
        raise ValueError("HTML must contain 1–4,000,000 bytes")
    directory = Path(workspace).resolve() / "published" / uuid.uuid4().hex
    directory.mkdir(parents=True)
    (directory / "index.html").write_text(html, encoding="utf-8")
    # Only this freshly created HTML directory is uploaded, never the repository.
    deployed = command_json(
        root,
        [
            "deploy",
            "--site",
            site,
            "--dir",
            str(directory),
            "--no-build",
            "--json",
            "--timeout",
            "120",
        ],
        cwd=directory,
    )
    url = deployed.get("deploy_url")
    parsed = urlsplit(url or "")
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or not parsed.hostname.endswith(".netlify.app")
    ):
        raise ValueError("Netlify did not return a valid HTTPS draft URL")
    audit = {
        "provider": "netlify",
        "production": False,
        "url": url,
        "deploy_id": deployed.get("deploy_id"),
        "site_id": site,
        "html_sha256": hashlib.sha256(html.encode()).hexdigest(),
        "public_url_verified": False,
    }
    audit_path = Path(workspace) / "deployments" / directory.name / "deployment.json"
    try:
        response = httpx.get(url, timeout=30, follow_redirects=False)
        audit["http_status"] = response.status_code
        audit["public_url_verified"] = response.status_code == 200
    except httpx.HTTPError as exc:
        audit["verification_error"] = type(exc).__name__
    finally:
        write_json(audit_path, audit)
    if not audit["public_url_verified"]:
        raise ValueError("Deployment URL is not publicly accessible; retained deployment.json")
    return url


def capture_source(url, directory):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Research source must be an explicit public HTTPS URL without credentials")
    with httpx.Client(timeout=45, follow_redirects=True) as client:
        response = client.get(url, headers={"User-Agent": "PE6203-research-reproduction/1.0"})
        response.raise_for_status()
    if "html" not in response.headers.get("content-type", "") or len(response.content) > 4_000_000:
        raise ValueError("Research listing must be HTML, at most 4 MB")
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "page.html").write_text(response.text, encoding="utf-8")
    manifest = {
        "url": url,
        "resolved_url": str(response.url),
        "captured_at": datetime.now(UTC).isoformat(),
        "file": "page.html",
        "sha256": hashlib.sha256((directory / "page.html").read_bytes()).hexdigest(),
        "content_type": response.headers.get("content-type"),
        "scope": "Latest means this listing at captured_at; paper relevance/top-five need review",
        "variant": "static HTML replay; scripts and subresources blocked by CSP",
    }
    write_json(directory / "manifest.json", manifest)
    return manifest


@contextmanager
def replay_source(manifest_path):
    manifest_path = Path(manifest_path)
    manifest = read_json(manifest_path)
    page = (manifest_path.parent / manifest["file"]).resolve()
    if (
        not page.is_relative_to(manifest_path.parent.resolve())
        or hashlib.sha256(page.read_bytes()).hexdigest() != manifest["sha256"]
    ):
        raise ValueError("Frozen research source hash mismatch")
    # Resolve original relative links, while preventing live scripts/assets changing the snapshot.
    import html

    body = (f'<base href="{html.escape(manifest["url"], quote=True)}">' + page.read_text()).encode()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path != "/source.html":
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header(
                "Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'"
            )
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield {**manifest, "replay_url": f"http://127.0.0.1:{server.server_port}/source.html"}
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def tool_result(text, error=False):
    return CallToolResult(content=[TextContent(type="text", text=text)], isError=error)


class NetlifyClient:
    def __init__(self, root, workspace, site, records):
        self.root, self.workspace, self.site = root, workspace, site
        self.schemas = {
            t["name"]: t["parameters"] for t in records if t["server_id"] == "edgeone-pages-mcp"
        }

    async def call_tool(self, name, arguments):
        try:
            if name not in self.schemas:
                raise ValueError("Tool not in current deployment catalog")
            Draft202012Validator(self.schemas[name]).validate(arguments)
            if name == "deploy_html":
                html = arguments["value"]
            elif name == "deploy_folder_or_zip":
                folder = Path(arguments["builtFolderPath"]).resolve()
                workspace = Path(self.workspace).resolve()
                if not folder.is_relative_to(workspace) or not folder.is_dir():
                    raise ValueError(
                        "Netlify variant supports generated HTML folders within the run workspace; zip uploads are unsupported"
                    )
                files = list(folder.iterdir())
                if len(files) != 1 or files[0].name != "index.html" or files[0].is_symlink():
                    raise ValueError(
                        "Task223 publishing accepts a single generated index.html only"
                    )
                html = files[0].read_text()
            else:
                raise ValueError("Unsupported deployment tool in Netlify variant")
            url = await asyncio.to_thread(publish_html, self.root, self.workspace, html, self.site)
            return tool_result(url)
        except (ValueError, KeyError, OSError, ValidationError, subprocess.SubprocessError) as exc:
            return tool_result(
                f"Netlify deployment failed: {type(exc).__name__}: {exc}", error=True
            )


class FrozenSourceClient:
    def __init__(self, original, records, frozen):
        self.original, self.frozen = original, frozen
        self.schemas = {
            t["name"]: t["parameters"] for t in records if t["server_id"] == "fetcher-mcp"
        }

    async def call_tool(self, name, arguments):
        try:
            if name not in self.schemas:
                raise ValueError("Tool not in current fetcher catalog")
            Draft202012Validator(self.schemas[name]).validate(arguments)
            args = copy.deepcopy(arguments)

            def mapped(url):
                if url not in (self.frozen["url"], self.frozen.get("resolved_url")):
                    raise ValueError("URL has no frozen source in this experiment")
                return self.frozen["replay_url"]

            if name == "fetch_url":
                args["url"] = mapped(args["url"])
            elif name == "fetch_urls":
                args["urls"] = [mapped(url) for url in args["urls"]]
            else:
                raise ValueError(
                    "Only frozen URL fetching is enabled; install browsers before the run"
                )
            result = await self.original.call_tool(name, args)
            for content in result.content:
                if hasattr(content, "text"):
                    content.text = content.text.replace(
                        self.frozen["replay_url"], self.frozen["url"]
                    )
            return result
        except (ValueError, KeyError, ValidationError) as exc:
            return tool_result(str(exc), error=True)


@contextmanager
def runtime_clients(clients, root, workspace, runtime, records):
    if not runtime:
        yield clients
        return
    if runtime.get("publish_backend") != "netlify" or set(clients) != {
        "fetcher-mcp",
        "edgeone-pages-mcp",
    }:
        raise ValueError("Netlify runtime is only supported for task223's fixed server set")
    with replay_source(runtime["source_manifest"]) as frozen:
        yield {
            "fetcher-mcp": FrozenSourceClient(clients["fetcher-mcp"], records, frozen),
            "edgeone-pages-mcp": NetlifyClient(root, workspace, runtime["site_id"], records),
        }

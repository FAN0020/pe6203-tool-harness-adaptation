"""Read-only, loopback-only original paper fixtures shared by both methods."""
import hashlib
import http.server
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / ".cache/mcpevol/fixtures/slidev-artifact-v1"
MANIFEST = ROOT / "results/evidence/slidev-readiness-20261031/fixture-manifest.json"
FILES = {row["path"]: row["sha256"] for row in json.loads(MANIFEST.read_text())}


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        key = unquote(urlsplit(self.path).path).removeprefix("/")
        if key not in FILES:
            self.send_error(404)
            return
        data = (FIXTURES / key).read_bytes()
        if hashlib.sha256(data).hexdigest() != FILES[key]:
            self.send_error(409, "Frozen fixture changed")
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    for key, digest in FILES.items():
        assert hashlib.sha256((FIXTURES / key).read_bytes()).hexdigest() == digest
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 4783), Handler)
    print("Serving exactly three hash-verified PDF fixtures on 127.0.0.1:4783", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()

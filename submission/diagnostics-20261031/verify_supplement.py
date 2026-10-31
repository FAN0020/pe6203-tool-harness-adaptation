"""Verify the supplement and recalculate its four trajectories without networking."""

import hashlib
import json
import runpy
import socket
import sys
import tarfile
import tempfile
from pathlib import Path

D = Path(__file__).resolve().parent
for item in json.loads((D / "SHA256SUMS.json").read_text()):
    p = D / item["path"]
    assert hashlib.sha256(p.read_bytes()).hexdigest() == item["sha256"], item["path"]


def blocked(*args, **kwargs):
    raise RuntimeError("Network is disabled for offline verification")


socket.socket = blocked
socket.create_connection = blocked
socket.getaddrinfo = blocked
with tempfile.TemporaryDirectory(prefix="pe6203-diagnostic-replay-") as temporary:
    t = Path(temporary)
    with tarfile.open(D / "raw.tar.gz") as archive:
        archive.extractall(t, filter="data")
    raw_manifest = json.loads((D / "raw-manifest.json").read_text())
    for item in raw_manifest:
        assert hashlib.sha256((t / item["path"]).read_bytes()).hexdigest() == item["sha256"], item[
            "path"
        ]
    reference = json.loads((t / "raw/reference-main-plan.json").read_text())
    source_files = 0
    for name, expected_hash in reference["files"].items():
        if name.startswith(("src/", "integration/", "configs/")):
            assert (
                hashlib.sha256((t / "raw/frozen-source" / name).read_bytes()).hexdigest()
                == expected_hash
            ), name
            source_files += 1
    sys.argv = [
        "audit.py",
        "--raw",
        str(t / "raw"),
        "--output",
        str(t / "recomputed"),
        "--skip-prior-evidence",
    ]
    runpy.run_path(str(D / "audit.py"), run_name="__main__")
    actual = json.loads((t / "recomputed/audit.json").read_text())
    expected = json.loads((D / "audit.json").read_text())
    assert expected.pop("prior_evidence_members_unchanged") == 10959
    assert actual.pop("prior_evidence_members_unchanged") is None
    assert actual == expected
print(
    json.dumps(
        {
            "status": "passed",
            "trajectories": 4,
            "ratings": 20,
            "raw_members_hashed": len(raw_manifest),
            "main_source_files_matched": source_files,
            "offline_recalculation": "identical except explicitly separate historical-preservation check",
            "network": "disabled",
            "model_calls": 0,
        }
    )
)

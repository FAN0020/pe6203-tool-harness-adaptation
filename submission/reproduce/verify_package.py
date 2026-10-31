"""Verify packaged hashes and replay with sockets disabled; never calls a model."""

import hashlib
import json
import os
import runpy
import socket
import sys
import tarfile
import tempfile
from pathlib import Path

R = Path(__file__).resolve().parents[1]
checked = 0
for item in json.loads((R / "SHA256SUMS.json").read_text()):
    p = R / item["path"]
    assert p.is_file(), item["path"]
    assert hashlib.sha256(p.read_bytes()).hexdigest() == item["sha256"], item["path"]
    checked += 1
for k in list(os.environ):
    if any(s in k.upper() for s in ["API_KEY", "TOKEN", "SECRET", "PASSWORD"]):
        os.environ.pop(k, None)


def blocked(*a, **k):
    raise RuntimeError("Network is disabled during offline verification")


socket.socket = blocked
socket.create_connection = blocked
socket.getaddrinfo = blocked
with tempfile.TemporaryDirectory(prefix="pe6203-offline-") as d:
    sys.argv = ["recalculate.py", "--archive", str(R / "evidence/main-raw.tar.gz"), "--output", d]
    runpy.run_path(str(R / "reproduce/recalculate.py"), run_name="__main__")
    for name in ["metrics.json", "cells.csv"]:
        assert (Path(d) / name).read_bytes() == (R / "evidence/recomputed" / name).read_bytes(), (
            name
        )
    corpus = Path(d) / "corpus"
    with tarfile.open(R / "evidence/trajectory-corpus.tar.gz", "r:gz") as archive:
        archive.extractall(corpus, filter="data")
    corpus_manifest = json.loads((R / "evidence/corpus-manifest.json").read_text())
    for item in corpus_manifest:
        member = corpus / item["path"]
        assert member.stat().st_size == item["bytes"], item["path"]
        assert hashlib.sha256(member.read_bytes()).hexdigest() == item["sha256"], item["path"]
    audit_output = Path(d) / "case-replay"
    os.environ["PE6203_EVIDENCE_ROOT"] = str(corpus)
    os.environ["PE6203_AUDIT_OUTPUT"] = str(audit_output)
    sys.path.insert(0, str(R / "reproduce"))
    for script in ["screen_trajectories.py", "audit_cases.py"]:
        runpy.run_path(str(R / "reproduce" / script), run_name="__main__")
    for name in ["trajectory-screening.json", "failure-cases.json", "diagnostic-review.json"]:
        assert json.loads((audit_output / name).read_text()) == json.loads(
            (R / "evidence" / name).read_text()
        ), name
print(
    json.dumps(
        {
            "hashed_files": checked,
            "offline_metrics": "byte-identical",
            "corpus_members_hashed": len(corpus_manifest),
            "case_audit": "same classifications and diagnostic results",
            "network": "disabled",
            "model_calls": 0,
        }
    )
)

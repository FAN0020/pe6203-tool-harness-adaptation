"""Build a credential-screened local evidence package. No API or network calls."""

import hashlib
import io
import json
import re
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
S = ROOT / "submission"


def sha(b):
    return hashlib.sha256(b).hexdigest()


secrets = []
for name in [".env", ".env copy"]:
    p = ROOT / name
    if p.exists():
        for line in p.read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                v = v.strip().strip("\"'")
                if re.search(r"KEY|TOKEN|SECRET|PASSWORD", k, re.I) and len(v) >= 16:
                    secrets.append(v.encode())
scanned = 0


def check(name, b):
    global scanned
    scanned += 1
    if Path(name).name in [".env", ".env copy", "credentials.json", "auth.json"]:
        raise ValueError("Forbidden credential file: " + name)
    if any(s in b for s in secrets) or re.search(
        rb"sk-or-v1-[0-9a-f]{32,}|sk-proj-[A-Za-z0-9_-]{40,}", b
    ):
        raise ValueError("Credential match; content withheld: " + name)


def check_tar(p):
    with tarfile.open(p, "r:gz") as t:
        for m in t:
            if m.isfile():
                check(str(p.name) + "/" + m.name, t.extractfile(m).read())


files = sorted(
    {
        p
        for d in [ROOT / "results/raw", ROOT / "results/evidence"]
        for p in d.rglob("*")
        if p.is_file()
        and not p.is_symlink()
        and p.suffix not in [".gz", ".zip", ".pyc"]
        and "__pycache__" not in p.parts
        and p.name != ".DS_Store"
    }
)
manifest = []
with tarfile.open(S / "evidence/trajectory-corpus.tar.gz", "w:gz") as t:
    for p in files:
        b = p.read_bytes()
        name = p.relative_to(ROOT).as_posix()
        check(name, b)
        manifest.append({"path": name, "bytes": len(b), "sha256": sha(b)})
        info = tarfile.TarInfo(name)
        info.size = len(b)
        info.mode = 0o644
        info.mtime = 0
        t.addfile(info, io.BytesIO(b))
(S / "evidence/corpus-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
history = []
archives = sorted((ROOT / "results/evidence").rglob("*.tar.gz"))
for p in archives:
    check_tar(p)
    b = p.read_bytes()
    history.append({"path": p.relative_to(ROOT).as_posix(), "bytes": len(b), "sha256": sha(b)})
(S / "evidence/history-manifest.json").write_text(json.dumps(history, indent=2) + "\n")
for p in [S / "evidence/main-raw.tar.gz", S / "evidence/source-main-12d693c.tar.gz"]:
    check_tar(p)
# The shared deck is the presentation deliverable. Local imports/build files stay private.
package = [
    p
    for p in S.rglob("*")
    if p.is_file()
    and not p.is_symlink()
    and ".build" not in p.parts
    and "slides" not in p.parts
    and "__pycache__" not in p.parts
    and p.suffix not in [".zip", ".pyc"]
    and p.name not in ["SHA256SUMS.json", "package-verification.json", "package-scan.json"]
]
checks = []
for p in sorted(package):
    b = p.read_bytes()
    check(p.relative_to(S).as_posix(), b)
    checks.append({"path": p.relative_to(S).as_posix(), "bytes": len(b), "sha256": sha(b)})
checks += [
    {"path": "history/" + h["path"], "bytes": h["bytes"], "sha256": h["sha256"]} for h in history
]
(S / "SHA256SUMS.json").write_text(json.dumps(checks, indent=2) + "\n")
(S / "evidence/package-scan.json").write_text(
    json.dumps(
        {
            "known_credentials_and_patterns": "no matches",
            "file_members_screened": scanned,
            "credentials_included": False,
            "scope": "package files and regular members of all included tar archives; no claim about unknown secret formats",
        },
        indent=2,
    )
    + "\n"
)
with zipfile.ZipFile(
    S / "PE6203-submission.zip", "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6
) as z:
    for p in sorted(package) + [S / "SHA256SUMS.json", S / "evidence/package-scan.json"]:
        z.write(p, p.relative_to(S).as_posix())
    for p in archives:
        z.write(p, "history/" + p.relative_to(ROOT).as_posix())
print(
    json.dumps(
        {
            "zip_bytes": (S / "PE6203-submission.zip").stat().st_size,
            "corpus_files": len(files),
            "raw_traces": sum(Path(r["path"]).name == "raw_trace.json" for r in manifest),
            "history_archives": len(history),
            "secret_matches": 0,
        }
    )
)

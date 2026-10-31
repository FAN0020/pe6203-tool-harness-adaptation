"""Package only the approved diagnostics; never modify previous delivery bundles."""

import hashlib
import io
import json
import re
import tarfile
import zipfile
from pathlib import Path

R = Path(__file__).resolve().parents[2]
D = Path(__file__).resolve().parent
RAW = R / "results/raw/course-targeted-diagnostics-20261031"
ARCHIVE = R / "submission/evidence/targeted-diagnostics-20261031.tar.gz"


def sha(b):
    return hashlib.sha256(b).hexdigest()


known = []
for name in [".env", ".env copy"]:
    p = R / name
    if p.exists():
        for line in p.read_text().splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                value = value.strip().strip("\"'")
                if re.search("KEY|TOKEN|SECRET|PASSWORD", key, re.I) and len(value) >= 16:
                    known.append(value.encode())


def scan(name, b):
    assert Path(name).name not in [".env", ".env copy", "credentials.json", "auth.json"], name
    assert not any(s in b for s in known), "Known credential match; content withheld: " + name
    assert not re.search(rb"sk-or-v1-[0-9a-f]{32,}|sk-proj-[A-Za-z0-9_-]{40,}", b), (
        "Credential pattern; content withheld: " + name
    )


raw_manifest = []
with tarfile.open(ARCHIVE, "w:gz") as t:
    for p in sorted(RAW.rglob("*")):
        if (
            not p.is_file()
            or p.is_symlink()
            or "__pycache__" in p.parts
            or p.suffix in [".pyc", ".lock"]
        ):
            continue
        name = "raw/" + p.relative_to(RAW).as_posix()
        b = p.read_bytes()
        scan(name, b)
        info = tarfile.TarInfo(name)
        info.size = len(b)
        info.mode = 0o644
        info.mtime = 0
        t.addfile(info, io.BytesIO(b))
        raw_manifest.append({"path": name, "sha256": sha(b), "bytes": len(b)})
(D / "raw-manifest.json").write_text(json.dumps(raw_manifest, indent=2) + "\n")
(D / "package-scan.json").write_text(
    json.dumps(
        {
            "known_credentials_and_patterns": "no matches",
            "raw_files": len(raw_manifest),
            "scope": "known local key values and common provider key patterns; not a guarantee for unknown formats",
        },
        indent=2,
    )
    + "\n"
)
files = [
    p
    for p in D.rglob("*")
    if p.is_file()
    and "__pycache__" not in p.parts
    and p.name not in ["SHA256SUMS.json", "package-verification.json"]
    and p.suffix not in [".pyc", ".zip"]
]
manifest = []
for p in sorted(files):
    b = p.read_bytes()
    scan(p.name, b)
    manifest.append({"path": p.relative_to(D).as_posix(), "sha256": sha(b), "bytes": len(b)})
manifest.append(
    {"path": "raw.tar.gz", "sha256": sha(ARCHIVE.read_bytes()), "bytes": ARCHIVE.stat().st_size}
)
(D / "SHA256SUMS.json").write_text(json.dumps(manifest, indent=2) + "\n")
out = R / "submission/PE6203-diagnostics-20261031.zip"
with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for p in sorted(files) + [D / "SHA256SUMS.json"]:
        z.write(p, p.relative_to(D).as_posix())
    z.write(ARCHIVE, "raw.tar.gz")
print(
    json.dumps(
        {
            "zip": out.name,
            "bytes": out.stat().st_size,
            "raw_members": len(raw_manifest),
            "new_trajectories": 4,
            "known_credentials": "no matches",
        }
    )
)

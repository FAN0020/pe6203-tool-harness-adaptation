"""Archive this completed trial only; preserve every raw file, including failures."""

import hashlib
import json
import subprocess
import tarfile
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    folder = Path(__file__).resolve().parent
    root = folder.parents[2]
    raw = root / "results/raw/discovery-contract-validation-20261101"
    freeze = json.loads((folder / "review-freeze.json").read_text())
    assert freeze["complete"] and freeze["review_count"] == 36
    commit = (folder / "review-freeze-commit.txt").read_text().strip()
    for name, expected in freeze["review_sha256"].items():
        path = folder / "blind-reviews" / name
        assert digest(path.read_bytes()) == expected
        committed = subprocess.check_output(
            ["git", "show", f"{commit}:{path.relative_to(root)}"], cwd=root
        )
        assert digest(committed) == expected
    state = json.loads((raw / "experiment.json").read_text())
    assert len(state["cells"]) == 36
    assert all(c["status"] == "evaluated" for c in state["cells"].values())
    assert json.loads((folder / "shutdown.json").read_text())["runner_exit_code"] == 0
    archive = folder / "raw-trial.tar.gz"
    manifest_path = folder / "raw-manifest.json"
    assert not archive.exists() and not manifest_path.exists()
    paths = sorted(p for p in raw.rglob("*") if p.is_file())
    hashes = {str(p.relative_to(root)): digest(p.read_bytes()) for p in paths}
    with tarfile.open(archive, "w:gz") as tar:
        for path in paths:
            tar.add(path, arcname=str(path.relative_to(root)), recursive=False)
    with tarfile.open(archive) as tar:
        actual = {m.name: digest(tar.extractfile(m).read()) for m in tar if m.isfile()}
    assert actual == hashes
    assert hashes == {str(p.relative_to(root)): digest(p.read_bytes()) for p in paths}
    manifest = {"prefix": str(raw.relative_to(root)), "archive_sha256": digest(archive.read_bytes()), "files": hashes}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"raw_files": len(hashes), "archive_bytes": archive.stat().st_size,
                      "archive_sha256": manifest["archive_sha256"]}))


if __name__ == "__main__":
    main()

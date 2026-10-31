"""Archive only this completed trial and its explicitly frozen source inputs."""
import hashlib
import json
import tarfile
from pathlib import Path

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[2]
RAW = ROOT / "results/raw/observed-contract-validation-20261031"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    state = json.loads((RAW / "experiment.json").read_text())
    assert len(state["cells"]) == 36
    assert all(c["status"] == "evaluated" for c in state["cells"].values())
    plan = json.loads((RAW / "plan.json").read_text())
    for name, digest in plan["files"].items():
        assert sha((ROOT / name).read_bytes()) == digest, name
    raw_files = [p for p in sorted(RAW.rglob("*")) if p.is_file() and not p.name.endswith(".lock")]
    assert all(not p.is_symlink() and p.name != ".env" for p in raw_files)
    archive = FOLDER / "raw-trial.tar.gz"
    assert not archive.exists(), "Archive already exists; verify it rather than overwrite."
    with tarfile.open(archive, "w:gz") as tar:
        for p in raw_files:
            tar.add(p, arcname=str(Path(RAW.name) / p.relative_to(RAW)), recursive=False)
    manifest = {"prefix": RAW.name, "archive_sha256": sha(archive.read_bytes()),
                "files": {str(Path(RAW.name) / p.relative_to(RAW)): sha(p.read_bytes()) for p in raw_files},
                "excluded": "Only runtime lock files; no other trial evidence omitted."}
    (FOLDER / "raw-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    source_names = [n for n in plan["files"] if not n.startswith(("results/", ".cache/"))]
    source_names += ["experiments/observed-contract-v1.json", "experiment"]
    source = FOLDER / "source-frozen.tar.gz"
    assert not source.exists()
    with tarfile.open(source, "w:gz") as tar:
        for name in sorted(set(source_names)):
            p = ROOT / name
            assert p.is_file() and not p.is_symlink() and p.name != ".env"
            tar.add(p, arcname=name, recursive=False)
    source_manifest = {
        "archive": source.name, "archive_sha256": sha(source.read_bytes()),
        "implementation_commit": "f892cad", "validation_preexecution_source_commit": "84317c3",
        "files": {n: sha((ROOT / n).read_bytes()) for n in sorted(set(source_names))},
        "runtime_hashes_only": {n: h for n, h in plan["files"].items() if n.startswith(".cache/")},
        "raw_inputs_archived_separately": [n for n in plan["files"] if n.startswith("results/")],
    }
    (FOLDER / "source-manifest.json").write_text(json.dumps(source_manifest, indent=2) + "\n")
    print(json.dumps({"archived_raw_files": len(raw_files), "source_files": len(set(source_names)),
                      "frozen_input_hashes_match": len(plan["files"])}))


if __name__ == "__main__":
    main()

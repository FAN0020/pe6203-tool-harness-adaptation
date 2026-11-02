"""Offline evaluation-code inventory, integrity checks and safe extraction.

This module never imports archived code, reads API credentials, or sends model
requests. Pinned source bundles preserve historical implementations separately
from main's active runtime. Online execution remains an explicit later action.
"""

import argparse
import ast
import hashlib
import json
import re
import tarfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent
VERSIONS = (2, 3, 5, 6)
SECRET = re.compile(rb"(?:sk-or-v1-|sk-proj-|sk-ant-api\d+-)[A-Za-z0-9_-]{35,}")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe_relative(value):
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "\\" in value:
        raise ValueError("Unsafe package-relative path")
    return path


def manifest(version, root=ROOT):
    directory = root / f"v{version}"
    path = directory / "manifest.json"
    if not path.exists():
        raise ValueError(f"evaluation-{version} is not present in this checkout")
    value = json.loads(path.read_text())
    if value.get("version") != version or value.get("schema") != "evaluation-package-1":
        raise ValueError("Invalid evaluation package identity")
    return directory, value


def archive_files(path):
    """Stream regular members only; never follow links or execute any content."""
    seen, total = set(), 0
    with tarfile.open(path, "r|gz") as archive:
        for entry in archive:
            safe_relative(entry.name)
            if entry.issym() or entry.islnk() or not (entry.isdir() or entry.isfile()):
                raise ValueError("Archive links and special files are forbidden")
            if entry.isdir():
                continue
            if entry.name in seen or entry.size > 100_000_000:
                raise ValueError("Duplicate or oversized archive member")
            seen.add(entry.name)
            total += entry.size
            if total > 1_500_000_000:
                raise ValueError("Archive exceeds the declared offline inspection allowance")
            yield entry.name, archive.extractfile(entry).read(), entry.mode


def check(version, root=ROOT):
    directory, data = manifest(version, root)
    if data["status"] != "ready":
        return {
            "version": version,
            "status": data["status"],
            "ready_for_merge": False,
            "reason": data["status_reason"],
            "new_model_calls": 0,
        }
    problems, code, members = [], 0, 0
    for relative, expected in data["files"].items():
        path = directory.joinpath(*safe_relative(relative).parts)
        if (
            path.is_symlink()
            or not path.is_file()
            or not path.resolve().is_relative_to(directory.resolve())
        ):
            problems.append("Missing/unsafe package file: " + relative)
            continue
        raw = path.read_bytes()
        if sha(raw) != expected:
            problems.append("File hash mismatch: " + relative)
        if SECRET.search(raw):
            problems.append("Possible credential in package file: " + relative)
        if path.suffix == ".py":
            try:
                ast.parse(raw, filename=relative)
                code += 1
            except SyntaxError:
                problems.append("Published evaluator source cannot parse: " + relative)
    for artifact in data["archives"]:
        relative = artifact["path"]
        found = {}
        for name, raw, _mode in archive_files(directory / relative):
            found[name] = sha(raw)
            members += 1
            if SECRET.search(raw):
                problems.append("Possible credential in archive member: " + relative + "/" + name)
            if artifact["role"] == "source" and name.endswith(".py"):
                try:
                    ast.parse(raw, filename=name)
                    code += 1
                except SyntaxError:
                    problems.append("Frozen evaluator source cannot parse: " + name)
        if found != artifact["members"]:
            problems.append("Archive member inventory/hash mismatch: " + relative)
    # Each published original-code copy must be byte-identical to its declared
    # Git source or local frozen original, not a silent reconstruction.
    for record in data["code_provenance"]:
        if data["files"].get(record["published_path"]) != record["sha256"]:
            problems.append("Code provenance mismatch: " + record["published_path"])
    return {
        "version": version,
        "status": "passed" if not problems else "failed",
        "ready_for_merge": not problems,
        "files_checked": len(data["files"]),
        "archive_members_checked": members,
        "Python_sources_parsed": code,
        "problems": problems,
        "new_model_calls": 0,
        "scope": "Code provenance, integrity and credential screening; not a new performance experiment",
    }


def extract(version, artifact_id, output, root=ROOT):
    directory, data = manifest(version, root)
    if data["status"] != "ready":
        raise ValueError(
            "This evaluation is pending/unavailable; extraction as a validated package is disabled"
        )
    artifact = next((a for a in data["archives"] if a["id"] == artifact_id), None)
    if artifact is None:
        raise ValueError("Unknown source/evidence archive ID")
    if sha((directory / artifact["path"]).read_bytes()) != data["files"][artifact["path"]]:
        raise ValueError("Archive hash mismatch")
    # Validate all member names/hashes before making any destination files.
    hashes = {name: sha(raw) for name, raw, _mode in archive_files(directory / artifact["path"])}
    if hashes != artifact["members"]:
        raise ValueError("Archive member manifest mismatch")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    for name, raw, _mode in archive_files(directory / artifact["path"]):
        path = output.joinpath(*safe_relative(name).parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        path.chmod(0o600)
    return {
        "version": version,
        "artifact": artifact_id,
        "files": len(hashes),
        "output": str(output.resolve()),
        "new_model_calls": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    p = sub.add_parser("verify")
    p.add_argument("--version", type=int, choices=VERSIONS)
    p.add_argument("--all", action="store_true")
    p.add_argument("--output", type=Path)
    p = sub.add_parser("extract")
    p.add_argument("--version", type=int, choices=VERSIONS, required=True)
    p.add_argument("--artifact", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "list":
        results = []
        for v in VERSIONS:
            if (ROOT / f"v{v}/manifest.json").exists():
                _, data = manifest(v)
                results.append(
                    {k: data[k] for k in ("version", "status", "status_reason", "batches")}
                )
        result, failed = results, False
    elif args.command == "extract":
        result, failed = extract(args.version, args.artifact, args.output), False
    else:
        if bool(args.version) == bool(args.all):
            parser.error("Choose --version or --all")
        versions = (
            [args.version]
            if args.version
            else [v for v in VERSIONS if (ROOT / f"v{v}/manifest.json").exists()]
        )
        result = [check(v) for v in versions]
        failed = any(not r["ready_for_merge"] for r in result)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

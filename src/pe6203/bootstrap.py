"""Fetch immutable releases and extract the two smoke servers' dependency closures."""

import hashlib
import json
import shutil
import stat
import subprocess
import urllib.request
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

from .benchmark import read_json, source, write_json


def verify_sha256(path, expected):
    with Path(path).open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != expected:
        raise ValueError(f"SHA256 mismatch for {Path(path).name}: {actual}")


def extract_packages(archive, destination, packages):
    destination = Path(destination).resolve()
    with ZipFile(archive) as z:
        entries = set(z.namelist())
        pending = [PurePosixPath("node_modules") / p for p in packages]
        selected = {}
        while pending:
            package = pending.pop()
            if str(package) in selected:
                continue
            metadata = json.loads(z.read(str(package / "package.json")))
            selected[str(package)] = metadata.get("version")
            dependencies = {
                **metadata.get("dependencies", {}),
                **metadata.get("optionalDependencies", {}),
            }
            for dep in dependencies:
                candidates = [
                    ancestor / "node_modules" / dep for ancestor in (package, *package.parents)
                ]
                found = next((p for p in candidates if str(p / "package.json") in entries), None)
                if found:
                    pending.append(found)
                elif dep not in metadata.get("optionalDependencies", {}):
                    raise ValueError(f"Missing released dependency {dep} of {package}")
        prefixes = tuple(p + "/" for p in selected)
        members = [info for info in z.infolist() if info.filename.startswith(prefixes)]
        for info in members:
            target = destination / info.filename
            if (
                not target.resolve().is_relative_to(destination)
                or ".." in PurePosixPath(info.filename).parts
            ):
                raise ValueError(f"Unsafe archive path: {info.filename}")
            if stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError(f"Unsafe archive symlink: {info.filename}")
        for info in members:
            z.extract(info, destination)
    return {"packages": selected, "files": len(members)}


def bootstrap(root, stages):
    root = Path(root).resolve()
    lock = read_json(root / "configs/benchmark.lock.json")
    cache = root / ".cache/mcpevol"
    cache.mkdir(parents=True, exist_ok=True)
    upstream = cache / "upstream"
    if not upstream.exists():
        subprocess.run(
            ["git", "clone", "--no-checkout", lock["repository"], str(upstream)], check=True
        )
        subprocess.run(
            ["git", "-C", str(upstream), "checkout", "--detach", lock["commit"]], check=True
        )
    source(root)
    results = {}
    for stage in stages:
        spec = lock["stages"][stage]
        archive = cache / spec["archive"]
        if not archive.exists():
            url = (
                f"https://huggingface.co/datasets/{lock['dataset']}/resolve/"
                f"{lock['dataset_revision']}/{spec['archive']}?download=true"
            )
            partial = archive.with_suffix(".partial")
            with urllib.request.urlopen(url, timeout=120) as response, partial.open("wb") as output:
                shutil.copyfileobj(response, output)
            verify_sha256(partial, spec["sha256"])
            partial.rename(archive)
        verify_sha256(archive, spec["sha256"])
        destination = cache / spec["directory"]
        extracted = extract_packages(archive, destination, list(lock["servers"]))
        results[stage] = {"archive_sha256": spec["sha256"], **extracted}
        write_json(destination / "extraction.json", results[stage])
    return results

"""Offline package controls; no archived code execution or model request."""

import hashlib
import io
import json
import tarfile

import pytest

from evaluation.manage import archive_files, check, extract, safe_relative


@pytest.mark.parametrize("name", ["/absolute", "../escape", "folder/../escape", "bad\\path", ""])
def test_evaluation_rejects_unsafe_paths(name):
    with pytest.raises(ValueError):
        safe_relative(name)


def package(tmp_path, *, status="ready", payload=b"print('not executed')\n"):
    directory = tmp_path / "v6"
    directory.mkdir()
    archive = directory / "runtime.tar.gz"
    with tarfile.open(archive, "w:gz") as stream:
        info = tarfile.TarInfo("src/example.py")
        info.size = len(payload)
        stream.addfile(info, io.BytesIO(payload))
    data = {
        "schema": "evaluation-package-1",
        "version": 6,
        "status": status,
        "status_reason": "Synthetic fixture",
        "batches": [],
        "code_provenance": [],
        "files": {archive.name: hashlib.sha256(archive.read_bytes()).hexdigest()},
        "archives": [
            {
                "id": "runtime",
                "path": archive.name,
                "role": "source",
                "members": {"src/example.py": hashlib.sha256(payload).hexdigest()},
            }
        ],
    }
    (directory / "manifest.json").write_text(json.dumps(data))
    return directory


def test_integrity_and_extraction_do_not_execute_source(tmp_path):
    package(tmp_path, payload=b"raise RuntimeError('must not execute')\n")
    result = check(6, tmp_path)
    assert result["ready_for_merge"] and result["new_model_calls"] == 0
    extract(6, "runtime", tmp_path / "out", tmp_path)
    assert (tmp_path / "out/src/example.py").exists()
    with pytest.raises(FileExistsError):
        extract(6, "runtime", tmp_path / "out", tmp_path)


def test_modified_archive_fails_before_extraction(tmp_path):
    directory = package(tmp_path)
    (directory / "runtime.tar.gz").write_bytes(b"corrupt archive")
    with pytest.raises(ValueError, match="hash mismatch"):
        extract(6, "runtime", tmp_path / "out", tmp_path)
    assert not (tmp_path / "out").exists()


def test_pending_version_cannot_be_declared_merge_ready(tmp_path):
    package(tmp_path, status="pending_not_validated")
    assert not check(6, tmp_path)["ready_for_merge"]
    with pytest.raises(ValueError, match="pending"):
        extract(6, "runtime", tmp_path / "out", tmp_path)


def test_archive_symlink_rejected(tmp_path):
    path = tmp_path / "link.tar.gz"
    with tarfile.open(path, "w:gz") as archive:
        info = tarfile.TarInfo("link")
        info.type, info.linkname = tarfile.SYMTYPE, "/etc/passwd"
        archive.addfile(info)
    with pytest.raises(ValueError, match="links"):
        list(archive_files(path))


def test_credential_pattern_stops_publication(tmp_path):
    package(tmp_path, payload=b"KEY = 'sk-or-v1-" + b"a" * 40 + b"'\n")
    result = check(6, tmp_path)
    assert not result["ready_for_merge"]
    assert any("credential" in p for p in result["problems"])

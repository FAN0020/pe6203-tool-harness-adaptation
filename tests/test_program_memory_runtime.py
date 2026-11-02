"""Shared-build boundary with the unchanged native stderr-sensitive code runner."""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
NODE = ROOT / ".cache/node-runtime/node_modules/node/bin/node"
COMMON = ROOT / "experiments/extensions/program-memory-dashboard-v1/common-input"


@pytest.mark.integration
def test_successful_common_build_does_not_report_stderr_as_native_failure(tmp_path):
    shutil.copytree(COMMON, tmp_path, dirs_exist_ok=True)
    (tmp_path / "src/main.tsx").write_text('document.body.textContent="generic runtime check";')
    result = subprocess.run(
        [str(NODE), "build.cjs"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        env={
            "PATH": str(NODE.parent) + ":/usr/bin:/bin",
            "HOME": str(tmp_path),
            "TMPDIR": str(tmp_path),
        },
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == "", "Native code runner treats nonempty stderr as an error receipt"
    assert (tmp_path / "public/app.js").stat().st_size > 0


@pytest.mark.integration
def test_failed_common_build_keeps_real_error_exit_and_diagnostics(tmp_path):
    shutil.copytree(COMMON, tmp_path, dirs_exist_ok=True)
    (tmp_path / "src/main.tsx").write_text("export const broken = <;")
    result = subprocess.run(
        [str(NODE), "build.cjs"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        env={
            "PATH": str(NODE.parent) + ":/usr/bin:/bin",
            "HOME": str(tmp_path),
            "TMPDIR": str(tmp_path),
        },
    )
    assert result.returncode != 0
    assert result.stderr

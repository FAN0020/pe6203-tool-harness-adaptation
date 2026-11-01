"""Archive generation rules and fixed code/data/native fingerprints before calls."""

import json
import tarfile
from datetime import UTC, datetime
from pathlib import Path

from pe6203.benchmark import write_json
from pe6203.experiment import freeze_files, sha, verify_files

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main():
    assert not (HERE / "generation-preexecution.json").exists()
    assert json.loads((HERE / "fixture-readiness.json").read_text())["passed"]
    paths = list((ROOT / "src/pe6203").glob("*.py")) + list((ROOT / "integration").glob("*.py"))
    paths += [
        ROOT / p
        for p in [
            "pyproject.toml",
            "uv.lock",
            "configs/benchmark.lock.json",
            "configs/server-profiles.json",
            "experiments/benchmark-v1.3.json",
            "experiments/relational-probe-memory-v1.json",
            "experiments/relational-probe-memory-feedback-v1.json",
            "tests/test_relational_probe_memory.py",
            "tests/test_active_contract_probing.py",
        ]
    ]
    paths += list((ROOT / "configs").glob("relational-probe-memory-*.json"))
    paths += [
        p
        for p in HERE.rglob("*")
        if p.is_file()
        and "__pycache__" not in p.parts
        and p.name not in {"pre-model-freeze.json", "generation-source.tar.gz"}
    ]
    native = []
    for stage in ["iter3", "iter5"]:
        d = ROOT / f".cache/mcpevol/{stage}/node_modules/@pimzino/agentic-tools-mcp"
        native += list((d / "dist").rglob("*.js")) + [
            d / "package.json",
            ROOT / f".cache/mcpevol/{stage}/extraction.json",
        ]
    native += [ROOT / ".cache/node-runtime/node_modules/node/bin/node"]
    files = freeze_files(ROOT, set(paths + native))
    archive = HERE / "generation-source.tar.gz"
    with tarfile.open(archive, "w:gz") as tf:
        for p in sorted(set(paths)):
            tf.add(p, arcname=str(p.relative_to(ROOT)), recursive=False)
    verify_files(ROOT, files)
    write_json(
        HERE / "pre-model-freeze.json",
        {
            "at": datetime.now(UTC).isoformat(),
            "phase": "generation only; exact candidate knowledge must separatelyfreeze beforeactor",
            "files": files,
            "archive_sha256": sha(archive),
            "native_archive_reference": "results/evidence/active-contract-probing-20261101/generation-source.tar.gz",
            "setup_calls": 2,
            "setup_catalogs": 2,
            "model_calls": 0,
            "tests": "Focused compiler/predecessor/audit tests; newmodule11tests red→green.",
            "independence": "10dev + conditional2x30validation schedules frozen; all task families exposed; independent executions not unseen tasks.",
        },
    )
    print(json.dumps({"frozen_files": len(files), "generation_model_calls": 0}))


if __name__ == "__main__":
    main()

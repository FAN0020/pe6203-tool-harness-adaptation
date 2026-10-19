"""Resolve task-139 pilot inputs across the team's metadata reorganization."""

from pathlib import Path


def task139_metadata_path(root, stage):
    if stage not in {"early", "middle", "late"}:
        raise ValueError(f"Unknown stage: {stage}")
    root = Path(root)
    current = root / f"examples/catalogs/task139/{stage}.json"
    return current if current.is_file() else root / f"examples/metadata/{stage}.json"


def pilot_config_path(root):
    root = Path(root)
    current = root / "configs/full-catalog-smoke.json"
    return current if current.is_file() else root / "configs/smoke.json"

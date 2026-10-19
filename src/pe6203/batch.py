"""Sequential batches with immutable identities and non-overwritten attempts."""

import hashlib
import os
import re
from pathlib import Path

from .benchmark import digest, read_json, write_json
from .runner import run


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def artifact_identity(root, plan, config):
    files = {}
    for path in sorted((root / "src/pe6203").glob("*.py")):
        files[str(path.relative_to(root))] = file_hash(path)
    for relative in ("configs/benchmark.lock.json", "configs/server-profiles.json", "uv.lock"):
        if (root / relative).exists():
            files[relative] = file_hash(root / relative)
    for cell in plan["runs"]:
        path = root / cell["knowledge_path"]
        files[str(path)] = file_hash(path)
        fixture = cell.get("fixture_dir", config.get("fixture_dir"))
        if fixture:
            directory = root / fixture
            if not directory.is_dir():
                raise ValueError(f"Missing fixture: {fixture}")
            for path in sorted(directory.rglob("*")):
                if path.is_symlink():
                    raise ValueError("Fixture symlink is not allowed")
                if path.is_file():
                    files[str(path)] = file_hash(path)
    endpoints = {
        role: os.environ.get(config.get(role, {}).get("base_url_env", ""))
        for role in ("agent", "judge")
    }
    return digest({"plan": plan, "config": config, "files": files, "endpoints": endpoints})


def run_batch(root, plan_path, output, resume=False):
    root, output = Path(root).resolve(), Path(output).resolve()
    plan = read_json(plan_path)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", plan["experiment_id"]):
        raise ValueError("Invalid experiment_id")
    config = read_json(root / plan["config_path"])
    keys = []
    for cell in plan["runs"]:
        if cell["version"] not in ("early", "middle", "late"):
            raise ValueError("Unknown stage")
        if cell["strategy"] not in (
            "no_update",
            "full_rewrite",
            "selective_patch",
            "current_metadata_smoke",
        ):
            raise ValueError("Unknown strategy")
        if type(cell["task_id"]) is not int or type(cell["seed"]) is not int:
            raise ValueError("Task ID and seed must be integers")
        keys.append(
            f"task{cell['task_id']}-{cell['version']}-{cell['strategy']}-seed{cell['seed']}"
        )
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate batch comparison cells")
    identity = artifact_identity(root, plan, config)
    ledger_path = output / "batch.json"
    if output.exists():
        if not resume:
            raise FileExistsError("Batch directory exists; use --resume for the same experiment")
        ledger = read_json(ledger_path)
        if ledger["identity_sha256"] != identity:
            raise ValueError("Batch identity changed; use a new experiment/output directory")
    else:
        output.mkdir(parents=True)
        ledger = {
            "schema_version": "1.0",
            "experiment_id": plan["experiment_id"],
            "identity_sha256": identity,
            "runs": [],
        }

    def save():
        temporary = ledger_path.with_suffix(".tmp")
        write_json(temporary, ledger)
        temporary.replace(ledger_path)

    save()
    by_key = {item["run_id"]: item for item in ledger["runs"]}
    for key, cell in zip(keys, plan["runs"], strict=True):
        item = by_key.get(key)
        if item and item["status"] != "running":
            if file_hash(output / item["result_path"]) != item["result_file_sha256"]:
                raise ValueError(f"Saved result modified: {key}")
            # Incomplete grading, blocked tasks and poor valid scores are retained, not retried.
            continue
        if item is None:
            item = {"run_id": key, "cell": cell, "status": "running", "attempts": []}
            ledger["runs"].append(item)
        previous = output / item["attempts"][-1] if item["attempts"] else None
        if previous and (previous / "result.json").exists():
            run_dir = previous
            result = read_json(previous / "result.json")
        else:
            if len(item["attempts"]) >= 2:
                raise ValueError(
                    f"Repeated interrupted attempt: {key}; inspect logs before a new experiment"
                )
            relative = Path(key) / f"attempt-{len(item['attempts']) + 1}"
            item["attempts"].append(str(relative))
            save()
            run_dir = output / relative
            settings = {
                **config,
                "root": str(root),
                "output_dir": str(run_dir),
                "knowledge_path": cell["knowledge_path"],
            }
            for field in ("fixture_dir", "update_cost"):
                if field in cell:
                    settings[field] = cell[field]
            _, result = run(
                cell["task_id"], cell["version"], cell["strategy"], cell["seed"], settings
            )
        for field in ("task_id", "version", "strategy", "seed"):
            if result[field] != cell[field]:
                raise ValueError(f"Saved result identity mismatch: {key}")
        item.update(
            {
                "status": "complete"
                if result["status"] == "evaluated" and result["judge_status"] == "complete"
                else "incomplete",
                "result_path": str((run_dir / "result.json").relative_to(output)),
                "result_file_sha256": file_hash(run_dir / "result.json"),
                "result": {
                    k: result.get(k)
                    for k in (
                        "status",
                        "execution_status",
                        "judge_status",
                        "TF",
                        "PE",
                        "cost",
                        "errors",
                    )
                },
            }
        )
        save()
    return ledger

"""Explicit V5 execution entry; historical baselines/configurations stay unchanged."""

from copy import deepcopy
from pathlib import Path

from .artifact_validation import settings
from .benchmark import digest, read_json
from .runner import run


def run_v5(
    root,
    task_id,
    stage,
    seed,
    config_path,
    adaptation_path,
    output,
    artifact_protocol=None,
    non_python_deliverable=False,
):
    if bool(artifact_protocol) == bool(non_python_deliverable):
        raise ValueError("Declare either a Python artifact protocol or a non-Python deliverable")
    artifact = read_json(adaptation_path)
    if artifact.get("pipeline_version") != "hybrid_v5" or artifact.get("status") != "validated":
        raise ValueError("run-v5 requires validated hybrid_v5 adaptation, not a V2 file")
    config = deepcopy(read_json(config_path))
    if config.get("artifact_validation") is not None:
        raise ValueError(
            "Pass the independent artifact protocol explicitly; do not hide it in config"
        )
    if any(
        config.get(key) is not None for key in ("knowledge_path", "adaptation_path", "update_cost")
    ):
        raise ValueError("V5 execution inputs must not override the validated adaptation")
    config.update(
        root=str(Path(root).resolve()),
        output_dir=str(Path(output).resolve()),
        adaptation_path=str(Path(adaptation_path).resolve()),
    )
    config["v5_protocol"] = {
        "version": "selective-execution-v5",
        "comparison_scope": "full_system_baselines_unchanged",
        "knowledge_update_effect_isolated": False,
        "artifact_scope": "python" if artifact_protocol else "non_python_not_applicable",
    }
    if artifact_protocol:
        protocol = settings(read_json(artifact_protocol))
        if not protocol["tests"]:
            raise ValueError("V5 Python validation requires independently prepared tests")
        config["artifact_validation"] = protocol
        config["v5_protocol"]["artifact_protocol_sha256"] = digest(protocol)
    return run(task_id, stage, "selective_patch", seed, config)

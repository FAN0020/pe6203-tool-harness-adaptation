"""Freeze a reviewable five-arm artifact experiment before generating task outputs."""

from pathlib import Path

from .artifact_validation import settings
from .benchmark import digest, read_json

ARMS = {"no_update", "full_rewrite", "deterministic_v1", "hybrid_v2", "hybrid_v3"}
OPERATIONAL = {"root", "output_dir", "knowledge_path", "adaptation_path", "update_cost"}


def freeze(path, output):
    path = Path(path).resolve()
    plan = read_json(path)
    if not isinstance(plan, dict) or set(plan) != {"version", "task_id", "stage", "seed", "arms"}:
        raise ValueError("Invalid artifact experiment plan")
    if (
        plan["version"] != "artifact-comparison-v1"
        or type(plan["task_id"]) is not int
        or type(plan["seed"]) is not int
        or plan["stage"] not in {"early", "middle", "late"}
    ):
        raise ValueError("Invalid frozen task/stage/seed")
    if not isinstance(plan["arms"], list) or len(plan["arms"]) != len(ARMS):
        raise ValueError("Plan must include all five updater arms")
    rows, seen, common = [], set(), None
    benchmark = None
    for row in plan["arms"]:
        if not isinstance(row, dict) or set(row) != {"arm", "knowledge", "config"}:
            raise ValueError("Invalid experiment arm")
        if row["arm"] not in ARMS or row["arm"] in seen:
            raise ValueError("Unknown/duplicate arm")
        seen.add(row["arm"])
        config = read_json(path.parent / row["config"])
        config["artifact_validation"] = settings(config["artifact_validation"])
        protocol = {k: v for k, v in config.items() if k not in OPERATIONAL}
        if common is None:
            common = protocol
        if protocol != common:
            raise ValueError("Unequal model/tool policy/execution/test/repair budget across arms")
        knowledge = read_json(path.parent / row["knowledge"])
        pin = knowledge["benchmark_commit"]
        if benchmark is None:
            benchmark = pin
        if pin != benchmark:
            raise ValueError("Knowledge benchmark mismatch")
        if row["arm"] == "no_update" and knowledge["version"] != "early":
            raise ValueError("No Update must freeze early knowledge")
        rows.append(
            {
                **row,
                "knowledge": str((path.parent / row["knowledge"]).resolve()),
                "config": str((path.parent / row["config"]).resolve()),
                "knowledge_sha256": digest(knowledge),
                "config_sha256": digest(config),
            }
        )
    frozen = {
        **plan,
        "arms": rows,
        "common_execution": common,
        "common_execution_sha256": digest(common),
        "benchmark_commit": benchmark,
        "scope": "Preflight only; no benchmark/model execution or scientific result",
    }
    output = Path(output)
    with output.open("x") as stream:
        import json

        json.dump(frozen, stream, indent=2)
        stream.write("\n")
    return frozen


def verify_frozen(path, arm):
    """Check actual files before execution; caller must use these frozen configs/knowledge."""
    path = Path(path).resolve()
    plan = read_json(path)
    row = next(r for r in plan["arms"] if r["arm"] == arm)
    knowledge = read_json(path.parent / row["knowledge"])
    config = read_json(path.parent / row["config"])
    config["artifact_validation"] = settings(config["artifact_validation"])
    if digest(knowledge) != row["knowledge_sha256"] or digest(config) != row["config_sha256"]:
        raise ValueError("Frozen experiment input changed")
    return knowledge, config


def run_arm(path, arm, root, output):
    from .runner import run

    path = Path(path).resolve()
    _, config = verify_frozen(path, arm)
    plan = read_json(path)
    row = next(r for r in plan["arms"] if r["arm"] == arm)
    config.pop("adaptation_path", None)
    config.update(
        root=str(Path(root).resolve()),
        output_dir=str(Path(output).resolve()),
        knowledge_path=str((path.parent / row["knowledge"]).resolve()),
    )
    strategy = arm if arm in {"no_update", "full_rewrite"} else "selective_patch"
    trace, result = run(plan["task_id"], plan["stage"], strategy, plan["seed"], config)
    from .benchmark import write_json

    write_json(
        Path(output) / "frozen-artifact-arm.json",
        {
            "arm": arm,
            "plan_sha256": digest(plan),
            "knowledge_sha256": row["knowledge_sha256"],
            "common_execution_sha256": plan["common_execution_sha256"],
        },
    )
    return trace, result

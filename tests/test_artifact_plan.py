import json

import pytest
from test_artifact_validation import protocol
from test_capability_v3 import catalogs

from pe6203 import artifact_plan


def plan_files(tmp_path):
    knowledge, _ = catalogs()
    (tmp_path / "knowledge.json").write_text(json.dumps(knowledge))
    arms = []
    for arm in sorted(artifact_plan.ARMS):
        (tmp_path / f"{arm}.json").write_text(
            json.dumps(
                {
                    "agent": {"model": "frozen", "temperature": 0, "max_completion_tokens": 100},
                    "max_rounds": 2,
                    "tool_name_policy": "namespaced",
                    "artifact_validation": protocol(),
                }
            )
        )
        arms.append({"arm": arm, "knowledge": "knowledge.json", "config": f"{arm}.json"})
    plan = {
        "version": "artifact-comparison-v1",
        "task_id": 999,
        "stage": "late",
        "seed": 0,
        "arms": arms,
    }
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan))
    return path


def test_freeze_all_five_arms_and_verify_exact_inputs(tmp_path):
    path = plan_files(tmp_path)
    output = tmp_path / "frozen.json"
    frozen = artifact_plan.freeze(path, output)
    assert {r["arm"] for r in frozen["arms"]} == artifact_plan.ARMS
    for arm in artifact_plan.ARMS:
        knowledge, config = artifact_plan.verify_frozen(output, arm)
        assert knowledge["benchmark_commit"] == frozen["benchmark_commit"]
        assert config["artifact_validation"] == frozen["common_execution"]["artifact_validation"]
    (tmp_path / "knowledge.json").write_text("{}")
    with pytest.raises(ValueError, match="changed"):
        artifact_plan.verify_frozen(output, "hybrid_v3")


@pytest.mark.parametrize(
    "field,value",
    [("max_repairs", 2), ("max_repair_tokens", 200), ("timeout_seconds", 2), ("tests", [])],
)
def test_unequal_execution_tests_and_repairs_rejected(tmp_path, field, value):
    path = plan_files(tmp_path)
    config_path = tmp_path / "hybrid_v3.json"
    config = json.loads(config_path.read_text())
    config["artifact_validation"][field] = value
    config_path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="Unequal"):
        artifact_plan.freeze(path, tmp_path / "frozen.json")


def test_frozen_arm_public_entry_uses_pinned_knowledge_not_adaptation(tmp_path, monkeypatch):
    from pe6203 import runner

    path = plan_files(tmp_path)
    output = tmp_path / "frozen.json"
    artifact_plan.freeze(path, output)

    def run(task, stage, strategy, seed, config):
        assert task == 999 and stage == "late" and seed == 0 and strategy == "selective_patch"
        assert config["knowledge_path"] == str(tmp_path / "knowledge.json")
        assert "adaptation_path" not in config
        return {}, {"status": "fixture_only"}

    monkeypatch.setattr(runner, "run", run)
    _, result = artifact_plan.run_arm(output, "hybrid_v3", tmp_path, tmp_path / "run")
    assert result["status"] == "fixture_only"
    assert json.loads((tmp_path / "run/frozen-artifact-arm.json").read_text())["arm"] == "hybrid_v3"

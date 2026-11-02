"""Frozen V6 execution and conservative post-run failure routing.

Diagnosis records hypotheses for future versions. It cannot mutate knowledge,
tests, judge rubrics or start unregistered retries in the current Evol run.
"""

import hashlib
from copy import deepcopy
from pathlib import Path

from .artifact_validation import settings
from .benchmark import digest, read_json, write_json
from .runner import run
from .selective_v6 import ACCEPTANCE


def diagnose(freeze, knowledge, injected_tools, calls, result, artifact_audit=None):
    """Only mechanically checkable observations become findings, not LLM causes.

    Correctness of natural language knowledge or an evaluator is not inferred
    from TF/PE or from a failed task. An injection mismatch is not established by
    absent data. No optional paid diagnostic LLM is enabled in this release.
    """
    findings = []
    if digest(knowledge) != freeze["knowledge_sha256"]:
        findings.append(
            {
                "route": "knowledge_stale_or_missing",
                "observation": "Frozen knowledge hash changed",
                "action": "Stop; independently investigate for a future version only",
            }
        )
    expected = {t["tool_id"] for t in knowledge["tools"]}
    if injected_tools is not None:
        actual = {t["tool_id"] for t in injected_tools}
        if actual != expected:
            findings.append(
                {
                    "route": "retrieval_or_injection",
                    "missing_ids": sorted(expected - actual),
                    "unexpected_ids": sorted(actual - expected),
                    "action": "Inspect actual injection; preserve knowledge content",
                }
            )
        elif digest(injected_tools) != digest(knowledge["tools"]):
            findings.append(
                {
                    "route": "retrieval_or_injection",
                    "observation": "Injected content differs from frozen records",
                    "action": "Inspect injection mapping; preserve knowledge content",
                }
            )
    if artifact_audit and artifact_audit.get("status") in {
        "repair_exhausted",
        "no_artifact",
        "test_failed",
        "static_failed",
    }:
        findings.append(
            {
                "route": "action_or_artifact",
                "observation": "Generated artifact failed frozen checks",
                "action": "Only predeclared code repair allowance; do not rewrite knowledge",
            }
        )
    if not findings:
        findings.append(
            {
                "route": "evidence_or_evaluator_uncertain",
                "observation": "Available observations do not establish a causal failure category",
                "action": "Preserve original outcome and all costs; collect independent evidence later",
            }
        )
    return {
        "version": "v6-post-run-diagnosis-1",
        "findings": findings,
        "knowledge_modified": False,
        "acceptance_modified": False,
        "automatic_retry": False,
        "actual_calls_observed": len(calls),
        "outcome_observed": deepcopy(result),
        "causality_proven": False,
        "scope": "post_run_only_future_versions",
    }


def run_v6(
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
        raise ValueError("Declare either Python artifact protocol or non-Python deliverable")
    path = Path(adaptation_path).resolve()
    artifact = read_json(path)
    if artifact.get("pipeline_version") != "hybrid_v6" or artifact.get("status") != "validated":
        raise ValueError("run-v6 requires a validated hybrid_v6 adaptation")
    if (
        artifact.get("acceptance_sha256") != digest(ACCEPTANCE)
        or artifact.get("acceptance") != ACCEPTANCE
    ):
        raise ValueError("Frozen V6 acceptance policy mismatch")
    knowledge_path = path.parent / artifact["output"]["knowledge_path"]
    raw = knowledge_path.read_bytes()
    knowledge = read_json(knowledge_path)
    if (
        hashlib.sha256(raw).hexdigest() != artifact["output"]["knowledge_file_sha256"]
        or digest(knowledge) != artifact["knowledge_sha256"]
    ):
        raise ValueError("Published knowledge hash mismatch")
    config = deepcopy(read_json(config_path))
    if any(
        config.get(key) is not None
        for key in ("artifact_validation", "knowledge_path", "adaptation_path", "update_cost")
    ):
        raise ValueError("V6 execution inputs cannot override frozen adaptation/protocol")
    freeze = {
        "version": "selective-execution-v6",
        "knowledge_sha256": digest(knowledge),
        "acceptance_sha256": digest(ACCEPTANCE),
        "task_id": task_id,
        "stage": stage,
        "config_sha256": digest(config),
        "current_task_feedback_updates_knowledge": False,
        "comparison_scope": "full_system_baselines_unchanged",
        "knowledge_update_effect_isolated": False,
        "artifact_scope": "python" if artifact_protocol else "non_python_not_applicable",
    }
    if artifact_protocol:
        protocol = settings(read_json(artifact_protocol))
        if not protocol["tests"] or protocol["max_repairs"] > 1:
            raise ValueError("Independent finite Python tests and at most one repair required")
        config["artifact_validation"] = protocol
        freeze["artifact_protocol_sha256"] = digest(protocol)
    config.update(
        root=str(Path(root).resolve()),
        output_dir=str(Path(output).resolve()),
        adaptation_path=str(path),
        v6_protocol=freeze,
    )
    # Sibling receipt is persisted before the first scored request. runner.run
    # creates output itself with exist_ok=False, preserving all prior runs.
    receipt = Path(output).with_name(Path(output).name + "-freeze.json")
    if receipt.exists():
        raise ValueError("Execution freeze receipt already exists")
    write_json(receipt, freeze)
    try:
        outcome, result = run(task_id, stage, "selective_patch", seed, config)
        run_path = Path(output)
        injected = (
            read_json(run_path / "knowledge.json")["tools"]
            if (run_path / "knowledge.json").exists()
            else None
        )
        trace = (
            read_json(run_path / "raw_trace.json") if (run_path / "raw_trace.json").exists() else []
        )
        # Saved knowledge is checked separately from actual wire injection. The
        # audit labels that distinction rather than claiming a full causal test.
        diagnosis = diagnose(
            freeze,
            read_json(knowledge_path),
            injected,
            trace if isinstance(trace, list) else trace.get("events", []),
            {k: result.get(k) for k in ("execution_status", "TF", "PE")},
            result.get("artifact_validation"),
        )
        diagnosis["injection_observation_scope"] = (
            "saved_runner_knowledge_not_full_wire_semantic_delivery_proof"
        )
        write_json(run_path.with_name(run_path.name + "-diagnosis.json"), diagnosis)
        return outcome, result
    finally:
        if (
            hashlib.sha256(knowledge_path.read_bytes()).hexdigest()
            != artifact["output"]["knowledge_file_sha256"]
        ):
            raise ValueError("Knowledge changed during frozen execution")
        if (
            artifact_protocol
            and digest(settings(read_json(artifact_protocol))) != freeze["artifact_protocol_sha256"]
        ):
            raise ValueError("Artifact acceptance changed during frozen execution")

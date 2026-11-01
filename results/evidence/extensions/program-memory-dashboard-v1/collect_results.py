"""Post-blind-review projection and archival; never changes agent runs or scores."""

import hashlib
import json
import statistics
import tarfile
from collections import Counter
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RAW = ROOT / "results/raw/extensions/program-memory-dashboard-v1/development"


def read(path):
    return json.loads(path.read_text())


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def main():
    assert not (HERE / "decision.json").exists(), "Preserve prior decision"
    plan = read(RAW / "plan.json")
    rows = []
    for cell in plan["cells"]:
        folder = RAW / "cells" / cell["id"] / "run"
        result = read(folder / "result.json")
        label = next(k for k, v in read(HERE / "review-map.json").items() if v == cell["id"])
        review = read(HERE / "blind-review" / (label + "-review.json"))
        events = read(folder / "raw_trace.json")["events"]
        tools = []
        responses = []
        for event in events:
            if event["type"] == "tool_result":
                native = event["result"]
                tools.append(
                    {
                        "name": event["call"]["function"]["name"],
                        "isError": native.get("isError"),
                        "returned_characters": len(json.dumps(native, ensure_ascii=False)),
                    }
                )
            elif event["type"] == "agent_response":
                response = event["response"]
                responses.append(
                    {
                        "finish_reason": response["choices"][0]["finish_reason"],
                        "prompt_tokens": response["usage"]["prompt_tokens"],
                        "completion_tokens": response["usage"]["completion_tokens"],
                        "reasoning_tokens": response["usage"]
                        .get("completion_tokens_details", {})
                        .get("reasoning_tokens"),
                    }
                )
        rows.append(
            {
                **cell,
                "scope": "synthetic_extension"
                if cell["task_id"] == 900101
                else "original_retention",
                "status": result["status"],
                "execution_status": result["execution_status"],
                "normal_completion": result["execution_status"] == "completed",
                "core": review["core"],
                "TF": result["TF"],
                "PE": result["PE"],
                "ECS": result["ECS"],
                "seconds": result["seconds"],
                "usd": result["cost"]["usd"],
                "update_cost": result["cost"]["update"],
                "tools": tools,
                "agent_responses": responses,
            }
        )
    groups = {}
    for scope in ["synthetic_extension", "original_retention"]:
        groups[scope] = {}
        for strategy in ["selective_patch", "verified_component_memory"]:
            group = [r for r in rows if r["scope"] == scope and r["strategy"] == strategy]
            groups[scope][strategy] = {
                "n": len(group),
                "completed": sum(r["normal_completion"] for r in group),
                "core": sum(r["core"] for r in group),
                "TF": statistics.mean(r["TF"] for r in group),
                "PE": statistics.mean(r["PE"] for r in group),
                "ECS": None,
            }
    ledger = read(RAW / "spend-ledger.json")
    known = sum(
        Decimal(str(r["actual_usd"])) for r in ledger["requests"] if r["actual_usd"] is not None
    )
    assert known == Decimal(ledger["known_usd"])
    costs = {
        "all_requests": len(ledger["requests"]),
        "agent_requests": sum(len(r["agent_responses"]) for r in rows),
        "judge_requests": 20,
        "preflight_requests": 2,
        "known_usd": str(known),
        "unknown_reserved_usd": ledger["unknown_reserved_usd"],
        "actual_providers": dict(Counter(r["actual_provider"] for r in ledger["requests"])),
        "actual_models": dict(Counter(r["actual_model"] for r in ledger["requests"])),
        "updater_model_calls": 0,
        "updater_usd": 0,
        "run_seconds_sum": sum(r["seconds"] for r in rows),
    }
    decision = {
        "id": "ext-program-memory-dashboard-v1-development",
        "freeze_commits": ["65543d0", "f049dd2", "316befc"],
        "score_masked_review_commit": "70d98a0",
        "group_results": groups,
        "rows": rows,
        "costs": costs,
        "development_gate_passed": all(
            groups["synthetic_extension"]["verified_component_memory"][k]
            > groups["synthetic_extension"]["selective_patch"][k]
            for k in ["completed", "core"]
        )
        and groups["synthetic_extension"]["verified_component_memory"]["TF"]
        >= groups["synthetic_extension"]["selective_patch"]["TF"]
        and all(
            groups["original_retention"]["verified_component_memory"][k]
            >= groups["original_retention"]["selective_patch"][k]
            for k in ["completed", "core", "TF"]
        ),
        "validation_started": False,
        "decision": "reject_exact_candidate_for_this_frozen_extension_protocol; no repeat-until-win",
        "mechanism_result": "See mechanism-projection.json; no requested files were produced in either arm. Token limits and actual calls are observations, not a demonstrated complete causal explanation.",
        "original_benchmark": "Task377 remains 原始输入缺失，当前不可评估. No new eligible original changed-task trial; original NU/FR/SP and all prior negative studies preserved. Original goal not completed.",
        "extension_only": "No completion or actual-quality gain established even on this controlled synthetic development case. No independent-validation claim.",
        "retention": "Both actual chart specs correct and final numeric interpretations false; equal K0, no adaptation-causal claim for stochastic narrative differences.",
        "ECS_reason": "Late-only experiment lacks matched Early/Middle task scores. ECS is null, not zero or an invented substitute.",
        "limitations": [
            "One development run per method, no independent confirmation because gate failed.",
            "Same coordinator masked scores until review commit; method identity was inferable from original absolute paths. Failed full-blinding is disclosed, no claim of independent review.",
            "Native code-runner pre-existing stdout debug warnings retained; calls returned results, source not repaired.",
        ],
        "goal_complete": False,
    }
    write(HERE / "decision.json", decision)
    files = [p for p in sorted(RAW.rglob("*")) if p.is_file() and p.name != ".writer.lock"]
    manifest = {str(p.relative_to(RAW)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    with tarfile.open(HERE / "development-raw.tar.gz", "w:gz") as archive:
        for p in files:
            archive.add(p, arcname=str(p.relative_to(RAW)), recursive=False)
    write(
        HERE / "raw-manifest.json",
        {
            "files": manifest,
            "file_count": len(files),
            "archive": "development-raw.tar.gz",
            "archive_bytes": (HERE / "development-raw.tar.gz").stat().st_size,
            "archive_sha256": hashlib.sha256(
                (HERE / "development-raw.tar.gz").read_bytes()
            ).hexdigest(),
        },
    )
    print(
        json.dumps({"results": groups, "costs": costs, "raw_files": len(files)}, ensure_ascii=False)
    )


if __name__ == "__main__":
    main()

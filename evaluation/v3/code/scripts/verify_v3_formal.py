"""Offline evidence audit; never runs or repairs an actor trajectory."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path

from pe6203.benchmark import digest, read_json, write_json


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dollars(values):
    if any(v is None for v in values):
        return None
    return sum((Decimal(str(v)) for v in values), Decimal(0))


def verify(root, out, destination):
    plan = read_json(out / "plan.json")
    freeze = read_json(out / "knowledge-freeze.json")
    receipts = [json.loads(line) for line in (out / "api/receipts.jsonl").read_text().splitlines()]
    checks = {}
    checks["frozen_source_hashes_match"] = all(
        sha(root / p) == h for p, h in plan["source_files_sha256"].items()
    )
    checks["preflight_hash_matches"] = sha(out / "preflight.json") == plan["preflight_sha256"]
    checks["frozen_capability_evidence_matches"] = all(
        sha(out / path) == fingerprint
        for path, fingerprint in plan["capability_evidence_sha256"].items()
    )
    checks["frozen_knowledge_files_match"] = all(
        sha(out / p) == v["sha256"] for p, v in freeze["files"].items()
    )
    checks["108_unique_planned_trajectories"] = (
        len(plan["cell_order"]) == len({x["id"] for x in plan["cell_order"]}) == 108
    )
    checks["all_receipts_known"] = all(r.get("usd") is not None for r in receipts)
    checks["all_receipts_expected_model_and_provider"] = all(
        r.get("model") == plan["model"] and r.get("provider") == "DigitalOcean" for r in receipts
    )
    checks["receipt_numbers_unique"] = len({r["request_number"] for r in receipts}) == len(receipts)
    api = [p for p in (out / "api").glob("request-*") if p.is_dir()]
    checks["all_api_requests_have_receipts"] = len(api) == len(receipts) and all(
        (p / "request.json").is_file()
        and (p / "response.json").is_file()
        and (p / "outcome.json").is_file()
        for p in api
    )
    checks["every_actual_request_pinned"] = all(
        read_json(p / "request.json")["body"].get("extra_body", {}).get("provider")
        == plan["provider_routing"]["provider"]
        for p in api
    )
    checks["no_model_seed_sent"] = all(
        "seed" not in read_json(p / "request.json")["body"] for p in api
    )
    checks["no_questions_in_updater"] = all(
        not any(
            task["question"]
            in json.dumps(
                read_json(out / "api" / f"request-{r['request_number']:05}" / "request.json")[
                    "body"
                ]["messages"],
                ensure_ascii=False,
            )
            for task in plan["tasks"].values()
        )
        for r in receipts
        if r["phase"] == "updater"
    )
    cell_results = []
    equality_controls = {}
    for tid in (430, 133, 90, 235):
        for stage in ("early", "middle", "late"):
            a = read_json(out / f"adaptations/{tid}/{stage}/no_update/knowledge.json")
            b = read_json(out / f"adaptations/{tid}/{stage}/selective_patch/knowledge.json")
            if stage == "early" or tid == 235:
                equality_controls[f"{tid}-{stage}"] = a["tools"] == [
                    {k: v for k, v in t.items() if k != "capability_boundary"} for t in b["tools"]
                ]
            if a != read_json(out / f"metadata/{tid}/early/catalog.json"):
                checks[f"no_update_K0_{tid}_{stage}"] = False
    checks["no_update_exact_K0_every_environment"] = not any(
        k.startswith("no_update_K0_") for k in checks
    )
    checks["control_base_records_identical_except_capability_layer"] = all(
        equality_controls.values()
    )
    for cell in plan["cell_order"]:
        directory = out / "runs" / cell["id"]
        result = read_json(directory / "result.json")
        trace = read_json(directory / "raw_trace.json")
        artifact = read_json(out / cell["adaptation"])
        catalog = read_json(out / f"metadata/{cell['task_id']}/{cell['stage']}/catalog.json")
        events = trace["events"]
        judged = read_json(directory / "EVAL" / f"{cell['task_id']}.json")["eval_result"]
        config = result["config"]
        group = [r for r in receipts if r["cell"] == cell["id"]]
        role_matches = {}
        for role in ("agent", "judge"):
            ledger_usd = dollars([r["usd"] for r in group if r["phase"] == role])
            result_usd = result["cost"][role].get("usd")
            role_matches[role] = (
                result_usd is not None
                and ledger_usd is not None
                and abs(ledger_usd - Decimal(str(result_usd))) < Decimal("0.000000000001")
            )
        facts = {
            "cell": cell["id"],
            "evaluated": result["status"] == "evaluated",
            "five_valid_ratings": result["judge_status"] == "complete"
            and judged["aggregate"]["successful_runs"] == 5
            and len(judged["runs"]) == 5,
            "judge_attempts_within_frozen_limit": all(
                a["attempt"] <= 2 for a in judged["attempts"]
            ),
            "question_hash_matches": hashlib.sha256(trace["question"].encode()).hexdigest()
            == plan["tasks"][str(cell["task_id"])]["question_sha256"],
            "environment_metadata_matches": digest(
                read_json(directory / "environment-metadata.json")
            )
            == digest(catalog),
            "knowledge_file_matches": sha(directory / "knowledge.json")
            == artifact["output"]["knowledge_file_sha256"],
            "same_actor_and_judge_settings": all(
                config[k] == v for k, v in plan["actor_and_judge"].items()
            ),
            "no_artifact_repair_protocol": config.get("artifact_validation") is None
            and not any(e.get("type", "").startswith("artifact_repair") for e in events),
            "one_actor_trajectory": sum(e.get("type") == "initial_messages" for e in events) == 1,
            "no_request_retries": not any(e.get("type") == "request_retry" for e in events),
            "known_actor_judge_charges_match_ledger": all(role_matches.values()),
        }
        if cell["strategy"] == "selective_patch":
            facts["expected_v3_pipeline"] = (
                artifact.get("pipeline_version") == "hybrid_v3"
                and artifact.get("updater_core_version") == "hybrid_v3_program_first_v1"
                and artifact.get("scope_policy") == "program_first_light_screen_local_review_v1"
            )
        else:
            facts["expected_v3_pipeline"] = True
        cell_results.append(facts)
    checks["all_108_saved"] = len(cell_results) == 108
    for key in cell_results[0]:
        if key != "cell":
            checks[key] = all(c[key] for c in cell_results)
    update_costs = []
    for p in (out / "adaptations").glob("*/*/*/adaptation.json"):
        artifact = read_json(p)
        update_costs.append(artifact["cost"]["usd"])
    checks["one_time_update_cost_matches_actual_receipts"] = abs(
        dollars(update_costs) - dollars([r["usd"] for r in receipts if r["phase"] == "updater"])
    ) < Decimal("0.000000000001")
    actor_receipts = [
        read_json(out / "api" / f"request-{r['request_number']:05}" / "request.json")
        for r in receipts
        if r["phase"] == "agent"
    ]
    checks["knowledge_frozen_before_first_actor"] = freeze["frozen_at"] < min(
        r["started_at"] for r in actor_receipts
    )
    tokens = {
        role: {
            field: sum(r.get("usage", {}).get(field, 0) for r in receipts if r["phase"] == role)
            for field in ("prompt_tokens", "completion_tokens")
        }
        for role in ("updater", "agent", "judge")
    }
    output = {
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "cell_checks": cell_results,
        "control_knowledge_equality": equality_controls,
        "request_counts": dict(Counter(r["phase"] for r in receipts)),
        "provider_tokens": tokens,
        "total_actual_usd": str(dollars([r["usd"] for r in receipts])),
        "scope": "Evidence consistency and protocol compliance; not a proof of semantic or functional correctness",
    }
    write_json(destination, output)
    print(
        json.dumps(
            {
                "status": output["status"],
                "failed": [k for k, v in checks.items() if not v],
                "calls": output["request_counts"],
                "usd": output["total_actual_usd"],
            },
            indent=2,
        )
    )
    return output["status"] == "passed"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(
        0 if verify(args.root.resolve(), args.input.resolve(), args.output.resolve()) else 1
    )

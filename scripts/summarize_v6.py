"""Offline integrity/cost/readout of a frozen V6 run. No inference requests."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from statistics import mean

from pe6203.benchmark import digest, read_json, write_json
from pe6203.payload_v6 import measure


def phase(request):
    messages = request["messages"]
    try:
        payload = json.loads(messages[-1].get("content", ""))
    except (ValueError, TypeError):
        payload = {}
    if isinstance(payload, dict):
        if payload.get("phase") in {"v6_global_screen", "v6_local_patch"}:
            return "updater"
        if "attempt" in payload and "source" in payload:
            return "repair"
    return "judge" if messages[0].get("role") != "system" else "actor"


def cost_rows(records, pricing):
    totals = {}
    for name in ("updater", "actor", "repair", "judge"):
        selected = [r for r in records if phase(r["request"]) == name]
        usages = [r.get("response", {}).get("usage", {}) for r in selected]
        charges = [u.get("cost") for u in usages]
        known = all(type(c) in (int, float) for c in charges)
        prompt = sum(u.get("prompt_tokens", 0) for u in usages)
        output = sum(u.get("completion_tokens", 0) for u in usages)
        totals[name] = {
            "requests": len(selected),
            "prompt_tokens": prompt,
            "completion_tokens": output,
            "cached_input_tokens": sum(
                (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0) or 0 for u in usages
            ),
            "billed_usd": sum(charges) if known else None,
            "known_usd": sum(c for c in charges if type(c) in (int, float)),
            "unknown_charges": sum(c is None for c in charges),
            "no_cache_counterfactual_usd": (
                prompt * pricing["input_per_million"] + output * pricing["output_per_million"]
            )
            / 1e6,
            "request_chars": sum(r["preflight"]["request_chars"] for r in selected),
        }
    return totals


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    home = args.run.resolve()
    plan = read_json(home / "frozen-plan.json")
    records = read_json(home / "transport-ledger.json")
    errors, cells = [], []

    def sha(p):
        return hashlib.sha256(p.read_bytes()).hexdigest()

    for path, expected in plan["files"].items():
        if sha(home / path) != expected:
            errors.append("Frozen input changed: " + path)
    for path, expected in plan["source_files"].items():
        if sha(home / "source-snapshot" / path) != expected:
            errors.append("Frozen source snapshot changed: " + path)
    for record in records:
        req = record["request"]
        if (
            record.get("http_status") != 200
            or record.get("response", {}).get("provider") != "Relace"
        ):
            errors.append("Transport/provider violation")
        if req.get("provider") != plan["provider"] or req.get("reasoning") != {"enabled": False}:
            errors.append("Provider/reasoning policy changed")
        if measure(req["messages"]) != {
            k: record["preflight"][k] for k in measure(req["messages"])
        }:
            errors.append("Preflight does not match actual wire request")
    for name in plan["cells"]:
        task, stage = name.split("/")
        cell = home / "cells" / f"task{task}-{stage}-r0"
        if not (cell / "cell.json").exists():
            continue
        status = read_json(cell / "cell.json")
        adaptation = read_json(cell / "adaptation/adaptation.json")
        audit = read_json(cell / "adaptation/updater-audit.json")
        cell_records = [r for r in records if r["cell"] == name]
        update_records = [r for r in cell_records if phase(r["request"]) == "updater"]
        charges = [r.get("response", {}).get("usage", {}).get("cost") for r in update_records]
        if len(update_records) != audit["cost"]["calls"]:
            errors.append("Updater native and wire call counts differ: " + name)
        if (
            all(type(c) in (int, float) for c in charges)
            and abs(sum(charges) - audit["cost"]["usd"]) > 1e-10
        ):
            errors.append("Updater native and wire cost differ: " + name)
        detail_ids = [p["tool_id"] for p in audit.get("semantic_patches", [])]
        if set(detail_ids) != {r["tool_id"] for r in audit.get("selected_candidates", [])}:
            errors.append("Candidate patch coverage mismatch: " + name)
        if len(detail_ids) != len(set(detail_ids)):
            errors.append("Duplicate local patch: " + name)
        if not set(audit["mandatory"]) <= set(detail_ids) and adaptation["status"] == "validated":
            errors.append("Program mandatory candidate omitted: " + name)
        if audit["review_basis_changes"] and adaptation["status"] == "validated":
            target = read_json(home / f"inputs/catalogs/{task}/{stage}.json")
            if set(audit["reviewed_tool_ids"]) != {t["tool_id"] for t in target["tools"]}:
                errors.append("Full screening coverage mismatch: " + name)
        result, trace = {}, {}
        if (cell / "run/result.json").exists():
            result = read_json(cell / "run/result.json")
            trace = read_json(cell / "run/raw_trace.json")
            freeze = read_json(cell / "run-freeze.json")
            if digest(read_json(cell / "adaptation/knowledge.json")) != freeze["knowledge_sha256"]:
                errors.append("Knowledge hash mismatch: " + name)
            if digest(read_json(cell / "run/knowledge.json")) != freeze["knowledge_sha256"]:
                errors.append("Runner did not use published snapshot: " + name)
            if freeze["acceptance_sha256"] != plan["acceptance_sha256"]:
                errors.append("Updater acceptance policy changed: " + name)
            if task == "133":
                if freeze.get("artifact_protocol_sha256") != plan["artifact_protocol_sha256"]:
                    errors.append("Code acceptance differs from preregistration: " + name)
            judged = [e for e in trace.get("events", []) if e.get("type") == "judge_result"]
            if len(judged) != 5 or status.get("judge_status") != "complete":
                errors.append("Five judge slots not complete: " + name)
        artifact = result.get("artifact_validation") or {}
        events = trace.get("events", [])
        cells.append(
            {
                **status,
                "adaptation_status": adaptation["status"],
                "selected_candidates": len(detail_ids),
                "update_calls": audit["cost"]["calls"],
                "update_chars": audit["cost"]["request_chars"],
                "artifact_status": artifact.get("status", "not_applicable"),
                "artifact_attempt_statuses": [r["status"] for r in artifact.get("attempts", [])],
                "tool_calls": sum(e.get("type") == "tool_result" for e in events),
                "cost": cost_rows(cell_records, plan["pricing"]),
            }
        )
    totals = cost_rows(records, plan["pricing"])
    unknown = sum(t["unknown_charges"] for t in totals.values())
    if unknown:
        errors.append("Unknown API charges remain")
    total = sum(t["known_usd"] for t in totals.values())
    if total > plan["max_usd"]:
        errors.append("Whole run spending cap exceeded")
    pilot = [r for r in records if r["cell"] == plan["pilot"]]
    if (
        sum(r.get("response", {}).get("usage", {}).get("cost") or 0 for r in pilot)
        > plan["pilot_max_usd"]
    ):
        errors.append("Pilot cap exceeded")
    scored = [c for c in cells if c.get("TF") is not None and c.get("PE") is not None]
    summary = {
        "method": "selective-V6",
        "method_commit": plan["method_commit"],
        "cells": cells,
        "completed_cells": len(cells),
        "planned_cells": len(plan["cells"]),
        "scored_cells": len(scored),
        "execution_status_counts": dict(
            Counter(c.get("execution_status", "not_executed") for c in cells)
        ),
        "TF": mean(c["TF"] for c in scored) if scored else None,
        "PE": mean(c["PE"] for c in scored) if scored else None,
        "cost_by_phase": totals,
        "all_api_usd": total,
        "task_system_usd": sum(totals[k]["known_usd"] for k in ("updater", "actor", "repair")),
        "API_requests": len(records),
        "unknown_API_charges": unknown,
        "all_API_no_cache_counterfactual_usd": sum(
            t["no_cache_counterfactual_usd"] for t in totals.values()
        ),
        "comparison_scope": plan["comparability"],
        "verification": {
            "passed": not errors,
            "errors": errors,
            "complete": len(cells) == len(plan["cells"]),
        },
        "limits": "One actor execution per condition; five judges are not five actor repeats. Finite code checks are not a security proof. Semantic recall/causality not established.",
    }
    write_json(home / "summary.json", summary)
    print(
        json.dumps(
            {
                k: v
                for k, v in summary.items()
                if k not in {"cells", "cost_by_phase", "comparison_scope"}
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

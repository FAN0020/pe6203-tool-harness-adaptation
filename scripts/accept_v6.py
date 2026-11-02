"""Offline real-catalog packing and worst-case candidate coverage; NO API calls.

Pass the frozen V5 evaluation inputs directory (catalogs/ and probes/). Outputs
are new receipts; originals are never edited. Synthetic all-candidate responses
measure packing capacity, not real LLM reasoning or task quality.
"""

import argparse
import json
from pathlib import Path

from pe6203.benchmark import digest, read_json, write_json
from pe6203.payload_v6 import detail_packet, prepare, screening_packet, selections
from pe6203.selective_v5 import REVIEW_PROMPT, _model_record
from pe6203.selective_v6 import DEFAULT_LIMITS, PATCH_PROMPT, SCREEN_PROMPT, batches, request_size


def v5_packets(state, old, target):
    changes = dict(state["changes"])
    for i, (key, source) in enumerate(state["sources"].items()):
        if source["kind"] != "catalog":
            changes[f"evidence-{i}"] = {
                "change_id": f"evidence-{i}",
                "tool_id": source["tool_id"],
                "kind": "independent_evidence",
                "evidence_id": key,
            }
    if not changes:
        return []
    changes = [
        {k: _model_record(v) if k in {"old", "new"} else v for k, v in c.items()}
        for c in changes.values()
        if not c["change_id"].startswith("obs-")
    ]
    old = {t["tool_id"]: t for t in old["tools"]}
    target = {t["tool_id"]: t for t in target["tools"]}
    records = sorted(state["records"].values(), key=lambda t: t["tool_id"])
    index = [
        {
            "tool_id": t["tool_id"],
            "old_description": old.get(t["tool_id"], {}).get("description"),
            "target_description": target[t["tool_id"]]["description"],
            "old_usage_rules": old.get(t["tool_id"], {}).get("usage_rules", []),
        }
        for t in records
    ]
    result = []
    for start in range(0, len(records), 6):
        group = records[start : start + 6]
        scope = {t["tool_id"] for t in group} | {c["tool_id"] for c in changes}
        payload = {
            "changes": changes,
            "evidence_registry": {
                k: v for k, v in state["sources"].items() if v["tool_id"] in scope
            },
            "knowledge_index": index,
            "deterministic_impacted": state["base"]["impacted_tool_ids"],
            "candidates": [
                {
                    "tool_id": t["tool_id"],
                    "old_record": _model_record(old.get(t["tool_id"])),
                    "target_record": _model_record(target[t["tool_id"]]),
                    "patched_record": _model_record(t),
                }
                for t in group
            ],
        }
        messages = [
            {"role": "system", "content": REVIEW_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
        result.append(len(json.dumps(messages, ensure_ascii=False)))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    rows = []
    for task in (133, 235, 283):
        for stage in ("early", "middle", "late"):
            old = read_json(args.inputs / f"catalogs/{task}/early.json")
            target = read_json(args.inputs / f"catalogs/{task}/{stage}.json")
            path = args.inputs / f"probes/{task}/{stage}/evidence.json"
            state = prepare(old, target, path if path.exists() else None)
            if state["changes"]:
                packet = screening_packet(state)
                assert {t["tool_id"] for t in packet["catalog"]} == set(state["records"])
                assert all(set(t) == {"tool_id", "purpose", "rules"} for t in packet["catalog"])
                write_json(args.output / f"task{task}-{stage}-screen.json", packet)
                screen = request_size(SCREEN_PROMPT, packet)
                # Stress every surviving tool plus every actual change as basis;
                # required candidates cannot disappear even under worst packing.
                fake = {
                    "covered_tool_ids": list(state["records"]),
                    "candidates": [
                        {
                            "tool_id": key,
                            "category": "uncertain",
                            "reason": "Offline worst-case stress, not model evidence",
                            "basis": list(state["changes"]),
                            "fields": [],
                        }
                        for key in state["records"]
                    ],
                }
                chosen = selections(fake, state)
                groups = batches(state, chosen, DEFAULT_LIMITS)
                assert {r["tool_id"] for g in groups for r in g} == set(state["records"])
                assert len([r for g in groups for r in g]) == len(state["records"])
                details = [request_size(PATCH_PROMPT, detail_packet(state, g)[0]) for g in groups]
                assert all(
                    s["request_chars"] <= DEFAULT_LIMITS["max_request_chars"] for s in details
                )
                assert 1 + 2 * len(groups) <= DEFAULT_LIMITS["max_calls"]
            else:
                screen, details = {"request_chars": 0, "estimated_input_tokens": 0}, []
            previous = v5_packets(state, old, target)
            rows.append(
                {
                    "task": task,
                    "stage": stage,
                    "tools": len(state["records"]),
                    "metadata_changes_or_anomalies": len(state["changes"]),
                    "mandatory": len(state["mandatory"]),
                    "screen": screen,
                    "all_candidate_detail_packets": details,
                    "all_candidate_initial_calls": 1 + len(details) if details else 0,
                    "all_candidate_initial_chars": screen["request_chars"]
                    + sum(s["request_chars"] for s in details),
                    "all_candidate_plus_one_revision_chars": screen["request_chars"]
                    + 2 * sum(s["request_chars"] for s in details),
                    "v5_first_review_chars": sum(previous),
                    "v5_max_request_chars": max(previous, default=0),
                    "old_sha256": digest(old),
                    "target_sha256": digest(target),
                    "coverage": "program_metadata_all_records_and_all_selected_ids_accounted",
                    "semantic_recall_proven": False,
                }
            )
    summary = {
        "version": "v6-offline-acceptance-1",
        "real_api_calls": 0,
        "passed": True,
        "input_dir": str(args.inputs.resolve()),
        "limits": DEFAULT_LIMITS,
        "cells": rows,
        "note": "Packing/structural coverage only, not proof the LLM discovers all dependencies",
    }
    write_json(args.output / "acceptance.json", summary)
    print(
        json.dumps(
            {
                "passed": True,
                "cells": len(rows),
                "max_screen_estimated_tokens": max(
                    r["screen"]["estimated_input_tokens"] for r in rows
                ),
                "v5_first_review_chars": sum(r["v5_first_review_chars"] for r in rows),
                "v6_screen_chars": sum(r["screen"]["request_chars"] for r in rows),
                "v6_worst_initial_all_candidate_chars": sum(
                    r["all_candidate_initial_chars"] for r in rows
                ),
            }
        )
    )


if __name__ == "__main__":
    main()

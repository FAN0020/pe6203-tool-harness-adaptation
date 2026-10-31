"""Offline corpus screening, not a claim of exhaustive semantic adjudication."""

import csv
import hashlib
import json
import os
from collections import Counter
from pathlib import Path

ROOT = Path(os.environ.get("PE6203_EVIDENCE_ROOT", Path(__file__).resolve().parents[2]))
OUT = Path(os.environ.get("PE6203_AUDIT_OUTPUT", Path(__file__).resolve().parents[1] / "evidence"))
FIELDS = ["name", "parameters", "description", "output_schema", "routing"]


def read(path):
    return json.loads(path.read_text()) if path and path.exists() else None


def records(catalog):
    return {t["tool_id"]: t for t in (catalog or {}).get("tools", [])}


def canonical(record):
    return {k: (record or {}).get(k) for k in FIELDS}


def screen(path):
    trace = read(path)
    directory = path.parent
    result = read(directory / "result.json") or {}
    task = result.get("task_id", trace.get("idx"))
    stage = result.get("version")
    method = result.get("strategy", "unrecorded")
    knowledge = read(directory / "knowledge.json")
    target = read(directory / "environment-metadata.json")
    old = None
    for parent in directory.parents:
        candidate = parent / "catalogs" / str(task) / "early.json"
        if candidate.exists():
            old = read(candidate)
            break
        if parent == ROOT:
            break
    k, a, b = records(knowledge), records(old), records(target)
    missed, unrelated = [], []
    if a and b and k:
        changed = {tid for tid in set(a) | set(b) if canonical(a.get(tid)) != canonical(b.get(tid))}
        missed = [tid for tid in changed if canonical(k.get(tid)) != canonical(b.get(tid))]
        unrelated = [
            tid
            for tid in (set(a) & set(b) & set(k)) - changed
            if canonical(k[tid]) != canonical(a[tid])
            or k[tid].get("usage_rules") != a[tid].get("usage_rules")
        ]
    events = trace.get("events", [])
    errors = [
        e for e in events if e.get("type") == "tool_result" and e.get("result", {}).get("isError")
    ]
    transports = [e for e in events if e.get("type") in ["agent_error", "request_retry"]]
    return {
        "trace": str(path.relative_to(ROOT)),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "task": task,
        "stage": stage,
        "method": method,
        "execution_status": result.get("execution_status", "unrecorded"),
        "TF": result.get("TF"),
        "PE": result.get("PE"),
        "tool_calls": sum(e.get("type") == "tool_result" for e in events),
        "tool_errors": len(errors),
        "transport_events": len(transports),
        "knowledge_comparison_available": bool(a and b and k),
        "metadata_mismatches_vs_changed_target": missed,
        "modified_metadata_unchanged_tools": unrelated,
        "review_rule": "Metadata mismatch and unrelated edits are screening signals, not causal failure verdicts. Usage-rule omissions absent from metadata need separate semantic review.",
    }


def main():
    paths = sorted((ROOT / "results").rglob("raw_trace.json"))
    rows = [screen(p) for p in paths]
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "trajectory-inventory.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    data = {
        "screened_paths": len(rows),
        "distinct_trace_hashes": len({r["sha256"] for r in rows}),
        "knowledge_comparison_available": sum(r["knowledge_comparison_available"] for r in rows),
        "unavailable_comparison": [
            r["trace"] for r in rows if not r["knowledge_comparison_available"]
        ],
        "original_selective_mismatches": [
            r
            for r in rows
            if r["method"] == "selective_patch" and r["metadata_mismatches_vs_changed_target"]
        ],
        "original_selective_unrelated_edits": [
            r
            for r in rows
            if r["method"] == "selective_patch" and r["modified_metadata_unchanged_tools"]
        ],
        "candidate_counts": dict(
            Counter(r["method"] for r in rows if r["modified_metadata_unchanged_tools"])
        ),
        "scope": "All raw_trace.json files currently accessible under results/, including duplicate archived copies. Structural and event screening of every trace; deep semantic review is limited to the explicitly indexed candidate case studies. Missing metadata is not evidence of correctness.",
    }
    (OUT / "trajectory-screening.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                k: v
                for k, v in data.items()
                if k
                not in [
                    "unavailable_comparison",
                    "scope",
                    "original_selective_mismatches",
                    "original_selective_unrelated_edits",
                ]
            },
            ensure_ascii=False,
        )
    )
    print(
        "selective mismatch/unrelated counts",
        len(data["original_selective_mismatches"]),
        len(data["original_selective_unrelated_edits"]),
    )


if __name__ == "__main__":
    main()

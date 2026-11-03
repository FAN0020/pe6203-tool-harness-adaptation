"""Read-only audit of original questions, recorded/live conditions and archives.

No actor, updater, judge, native server or task377 input search is invoked.
Only permitted question/server projections of the pinned benchmark are exported.
"""

import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/evidence/unified-reaudit-20261102"


def read(path):
    return json.loads(path.read_text())


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def main():
    cohorts, cells = [read(OUT / n) for n in ["cohorts.json", "cells.json"]]
    lock = read(ROOT / "configs/benchmark.lock.json")
    upstream = ROOT / ".cache/mcpevol/upstream"
    actual_commit = subprocess.check_output(
        ["git", "-C", str(upstream), "rev-parse", "HEAD"], text=True
    ).strip()
    assert actual_commit == lock["commit"]
    # No benchmark answer, reference trace or score enters output or any updater.
    allowed = {t["id"] for c in cohorts for t in c["tasks"] if t["id"] < 900000 and t["id"] != 377}
    source = {
        t["idx"]: {k: t[k] for k in ["question", "servers"]}
        for t in read(upstream / "src/custom/data/test_cases/test_cases.json")
        if t["idx"] in allowed
    }
    archive_rows = []
    for stage, spec in lock["stages"].items():
        archive = ROOT / ".cache/mcpevol" / spec["archive"]
        extraction = ROOT / ".cache/mcpevol" / spec["directory"] / "extraction.json"
        actual = sha(archive) if archive.exists() else None
        recorded = read(extraction)["archive_sha256"]
        archive_rows.append(
            {
                "stage": stage,
                "path": str(archive.relative_to(ROOT)),
                "exists": archive.exists(),
                "size": archive.stat().st_size if archive.exists() else None,
                "expected_sha256": spec["sha256"],
                "current_archive_sha256": actual,
                "extraction_record_sha256": sha(extraction),
                "recorded_archive_sha256": recorded,
                "matches": actual == recorded == spec["sha256"],
            }
        )
    grouped = defaultdict(list)
    for cell in cells:
        grouped[cell["cohort"]].append(cell)
    out = {}
    for cohort in cohorts:
        folder = ROOT / cohort["path"]
        rows = grouped[cohort["path"]]
        providers = Counter()
        catalogs = defaultdict(set)
        records = []
        for row in rows:
            providers.update(row.get("actor_providers", {}))
            env = folder / "cells" / row["cell_id"] / "run/environment-metadata.json"
            if not env.exists():
                continue
            d = read(env)
            key = f"{row['task_id']}/{row['stage']}"
            catalogs[key].add(sha(env))
            records.append(
                {
                    "cell_id": row["cell_id"],
                    "sha256": sha(env),
                    "source": d.get("source"),
                    "version": d.get("version"),
                    "catalog_tools": len(d.get("tools", [])),
                    "observed_native_calls": row.get("tool_calls", 0),
                }
            )
        questions = {}
        for t in cohort["tasks"]:
            tid = t["id"]
            if tid == 377:
                questions[str(tid)] = {
                    "eligible": False,
                    "reason": "Previously established missing original input; no renewed search.",
                }
                continue
            s = source.get(tid)
            questions[str(tid)] = {
                "question_sha256": t["question_sha256"],
                "class": "controlled_synthetic_extension"
                if tid >= 900000
                else "original_with_fixed_fixture"
                if tid == 457
                else "original_benchmark",
                "question_matches_pinned_original": t["text"] == s["question"] if s else None,
                "required_servers_match_pinned_original": t["servers"] == s["servers"]
                if s
                else None,
                "external_fixture_required": tid == 457 or tid >= 900000,
                "input_boundary": "133 has no supplied Python files: advisory task;283 requests project/task planning, not actual CSV/log analysis;235 all data inline."
                if tid in (133, 283, 235)
                else "Use cohort-specific frozen fixture manifest and original run readiness evidence; not inferred from TF.",
            }
        config = cohort.get("config") or {}
        out[cohort["path"]] = {
            "actor_provider_counts": dict(providers),
            "fixed_DigitalOcean_route": (
                config.get("agent", {}).get("extra_body", {}).get("provider", {}).get("only")
                == ["digitalocean"]
            ),
            "plan_sha256": cohort["plan_sha256"],
            "benchmark_commit": cohort["benchmark_commit"],
            "dataset_revision": cohort["dataset_revision"],
            "questions": questions,
            "knowledge_lock_checked": cohort["knowledge_lock_exists"]
            and not cohort["invalid_lock_files"],
            "environment_records": len(records),
            "started": sum(r["execution_status"] != "not_started" for r in rows),
            "catalog_hashes_by_task_stage": {k: sorted(v) for k, v in catalogs.items()},
            "within_condition_catalog_mismatches": {
                k: sorted(v) for k, v in catalogs.items() if len(v) > 1
            },
            "environment_record_details": records,
            "fixture_dir": config.get("fixture_dir"),
            "task_context": config.get("task_context"),
            "full_fixture_semantic_audit": "457 fixed-fixture preparation versions separated; synthetic rules independent. No claim all historical per-run executable/dependency hashes were captured.",
        }
    (OUT / "comparability.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    report = {
        "benchmark_lock_sha256": sha(ROOT / "configs/benchmark.lock.json"),
        "actual_upstream_commit": actual_commit,
        "archives": archive_rows,
        "limitations": [
            "Fresh archive hashing verifies current ZIPs, not every historical extracted runtime byte.",
            "Environment records are live catalog snapshots, not process startup logs.",
            "Successful native calls establish startup for the servers actually called; no proof of every declared server execution.",
            "Task/family overlap and provider differences remain visible; no pooled causal ranking.",
        ],
    }
    (OUT / "environment-archive-audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "cohorts": len(out),
                "archive_matches": sum(r["matches"] for r in archive_rows),
                "original_question_mismatches": sum(
                    q.get("question_matches_pinned_original") is False
                    for c in out.values()
                    for q in c["questions"].values()
                ),
                "catalog_mismatch_groups": sum(
                    len(c["within_condition_catalog_mismatches"]) for c in out.values()
                ),
            }
        )
    )


if __name__ == "__main__":
    main()

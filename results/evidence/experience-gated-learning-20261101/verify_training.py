"""Independent stdlib verification of frozen training, raw ratings and costs."""
import json
import statistics
import tarfile
from decimal import Decimal
from pathlib import Path

from raw_cell_verifier import archive_files, inspect_cell, sha

FOLDER = Path(__file__).resolve().parent


def main():
    files, manifest = archive_files(FOLDER)
    prefix = manifest["prefix"] + "/"
    read = lambda name: json.loads(files[prefix + name])
    plan = read("plan.json")
    assert sha(files[prefix + "plan.json"]) == files[prefix + "plan.sha256"].decode().strip()
    assert [(c["task_id"], c["seed"]) for c in plan["cells"]] == [(900201, 0), (900202, 0), (900202, 1), (900201, 1)]
    assert all(c["strategy"] == "selective_patch" and c["version"] == "late" for c in plan["cells"])
    lock = read("knowledge-lock.json")
    assert lock["plan_sha256"] == sha(files[prefix + "plan.json"])
    for name, digest in lock["files"].items():
        assert sha(files[prefix + name]) == digest
    assert read("knowledge-review.json")["lock_sha256"] == sha(files[prefix + "knowledge-lock.json"])
    frozen = json.loads((FOLDER / "prefreeze-manifest.json").read_text())
    archive = FOLDER / "training-prefreeze.tar.gz"
    assert sha(archive.read_bytes()) == frozen["archive_sha256"]
    with tarfile.open(archive) as tar:
        source = {m.name: tar.extractfile(m).read() for m in tar if m.isfile()}
    for name, digest in plan["files"].items():
        assert sha(source[name]) == digest
    for task in (900201, 900202):
        base = f"adaptations/{task}-late-selective_patch/"
        knowledge = read(base + "knowledge.json")
        assert knowledge == read("adaptations/900201-late-selective_patch/knowledge.json")
        # Preserve the exact SP construction, not an inferred candidate.
        assert read(base + "adaptation.json")["status"] == "validated"
    state = read("experiment.json")
    assert len(state["cells"]) == 4
    for item in state["cells"].values():
        assert item["status"] == "evaluated"
        for name, digest in item["files"].items():
            assert sha(files[prefix + name]) == digest
    review_path = FOLDER / "reviews.json"
    freeze = json.loads((FOLDER / "review-freeze.json").read_text())
    assert sha(review_path.read_bytes()) == freeze["reviews_sha256"]
    reviews = json.loads(review_path.read_text())
    assert len(reviews) == 4
    rows, response_ids = [], []
    expected_properties = {"artifact", "facts", "calculations", "decision", "coverage", "render", "delivery"}
    for i, cell in enumerate(plan["cells"], 1):
        row, ids = inspect_cell(files, prefix, cell, "synthetic_adaptation_training")
        response_ids.extend(ids)
        review = reviews[i-1]
        assert review["episode"] == f"E{i:02}"
        assert review["normal_completion"] == (row["execution_status"] == "completed")
        assert set(review["properties"]) == expected_properties
        assert set(review["properties"].values()) <= {"pass", "fail", "unknown"}
        assert review["core_pass"] == all(v == "pass" for v in review["properties"].values())
        packet_path = FOLDER / "review-inputs" / f"E{i:02}.json"
        assert sha(packet_path.read_bytes()) == review["input_sha256"]
        packet = json.loads(packet_path.read_text())
        for artifact in packet["artifacts"]:
            assert sha(files[prefix + f"cells/{cell['id']}/run/workspace/" + artifact["path"]]) == artifact["sha256"]
        row.update(episode=review["episode"], properties=review["properties"], core_pass=review["core_pass"])
        rows.append(row)
    ledger = read("spend-ledger.json")
    assert ledger["policy"]["limit_usd"] is None and not ledger["blocked"]
    assert Decimal(ledger["unknown_reserved_usd"]) == 0
    for req in ledger["requests"]:
        assert req["status"] == "settled" and req["actual_provider"] == "DigitalOcean"
        assert req["actual_model"] == ledger["policy"]["model"]
        assert req["provider"] == ledger["policy"]["provider_route"]
    preflight = [r for r in ledger["requests"] if r["max_completion_tokens"] == 32]
    assert len(preflight) == 2
    assert len(response_ids) == len(set(response_ids))
    assert set(response_ids) == {r["response_id"] for r in ledger["requests"] if r not in preflight}
    spent = sum((Decimal(r["actual_usd"]) for r in ledger["requests"]), Decimal(0))
    assert spent == Decimal(ledger["known_usd"])
    positive = [r["episode"] for r in rows if r["execution_status"] == "completed" and r["core_pass"]]
    failure = [r["episode"] for r in rows if r["execution_status"] != "completed" or not r["core_pass"]]
    result = {"verified": True, "raw_files": len(files), "source_files": len(plan["files"]), "rows": rows,
              "normal_completion": sum(r["execution_status"] == "completed" for r in rows),
              "core_pass": sum(r["core_pass"] for r in rows), "episodes": 4,
              "TF": statistics.mean(r["TF"] for r in rows), "PE": statistics.mean(r["PE"] for r in rows), "ECS": None,
              "training_gate": {"admit_reflection": bool(positive and failure), "positive_episodes": positive, "failed_episodes": failure},
              "api_requests": len(ledger["requests"]), "judge_slots": 20, "known_usd": str(spent), "unknown_cost_items": 0,
              "updater_calls": 0, "goal_complete": False, "scope": "Synthetic adaptation training only, no original candidate evaluation."}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

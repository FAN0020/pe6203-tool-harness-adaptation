"""Offline, standard-library verification of frozen source, scores, costs and gates."""

import hashlib
import json
import statistics
import tarfile
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def sha(data):
    return hashlib.sha256(data).hexdigest()


def archived_json(archive, name):
    return json.load(archive.extractfile(name))


def verify():
    plan = read(HERE / "development-plan.json")
    pre = read(HERE / "preexecution.json")
    assert sha((HERE / "development-plan.json").read_bytes()) == pre["plan_sha256"]
    assert sha((HERE / pre["archive"]).read_bytes()) == pre["archive_sha256"]
    with tarfile.open(HERE / pre["archive"]) as source:
        for name, wanted in plan["files"].items():
            assert sha(source.extractfile(name).read()) == wanted, name
        base = "experiments/extensions/program-memory-dashboard-v1/"
        protocol = archived_json(source, base + "protocol.json")
        assert "development_gate" not in protocol["acceptance"]
        assert "strictly higher" in protocol["acceptance"]["dev_gate"]
        fixture = archived_json(source, base + "datasets/development/manifest.json")
        task = archived_json(source, base + "task-development.json")
        assert task["idx"] == 900101 and task["dataset_kind"] == "controlled_synthetic_extension"
        assert set(task) == {"idx", "extension_id", "dataset_kind", "question", "servers"}
        env = archived_json(
            source, "results/evidence/program-memory-runtime-20261101/environment-proof.json"
        )
        dep_root = ".cache/program-memory-runtime-v1/"
        for name, record in env["dependencies"].items():
            if "sha256" in record:
                assert sha(source.extractfile(dep_root + name).read()) == record["sha256"]
        for name, wanted in fixture["input_files"].items():
            assert (
                sha(source.extractfile(base + "datasets/development/input/" + name).read())
                == wanted
            )
    lock = read(HERE / "blind-review/review-lock.json")
    assert lock["all_reviews_complete"] and lock["scores_hidden"]
    for mapping in ["reviews", "packets"]:
        for name, wanted in lock[mapping].items():
            assert sha((HERE / "blind-review" / name).read_bytes()) == wanted
    review_map = read(HERE / "review-map.json")
    assert sha((HERE / "review-map.json").read_bytes()) == lock["mapping_sha256"]
    manifest = read(HERE / "raw-manifest.json")
    assert sha((HERE / manifest["archive"]).read_bytes()) == manifest["archive_sha256"]
    decision = read(HERE / "decision.json")
    with tarfile.open(HERE / manifest["archive"]) as raw:
        assert {m.name for m in raw.getmembers() if m.isfile()} == set(manifest["files"])
        for name, wanted in manifest["files"].items():
            assert sha(raw.extractfile(name).read()) == wanted, name
        assert archived_json(raw, "plan.json") == plan
        rows = []
        for cell in plan["cells"]:
            prefix = f"cells/{cell['id']}/run/"
            result = archived_json(raw, prefix + "result.json")
            evaluation = archived_json(raw, prefix + f"EVAL/{cell['task_id']}.json")["eval_result"]
            assert result["status"] == "evaluated" and result["ECS"] is None
            assert len(evaluation["runs"]) == 5
            for slot, item in enumerate(evaluation["runs"], 1):
                first = next(
                    x
                    for x in evaluation["attempts"]
                    if x["slot"] == slot and "result" in x and "error" not in x
                )
                assert first == item
                assert item["response"]["choices"][0]["finish_reason"] == "stop"
                parsed = json.loads(item["response"]["choices"][0]["message"]["content"])
                for dim in ["task_fulfillment", "planning_and_efficiency", "grounding"]:
                    assert (
                        type(parsed[dim]) is int
                        and 1 <= parsed[dim] <= 10
                        and parsed[dim] == item["result"][dim]
                    )
            tf = statistics.mean(x["result"]["task_fulfillment"] for x in evaluation["runs"])
            pe = statistics.mean(x["result"]["planning_and_efficiency"] for x in evaluation["runs"])
            assert tf == result["TF"] and pe == result["PE"]
            label = next(k for k, v in review_map.items() if v == cell["id"])
            review = read(HERE / "blind-review" / (label + "-review.json"))
            row = next(r for r in decision["rows"] if r["id"] == cell["id"])
            assert row["TF"] == tf and row["PE"] == pe and row["core"] == review["core"]
            assert row["normal_completion"] == (result["execution_status"] == "completed")
            assert result["cost"]["update"]["calls"] == 0 and result["cost"]["update"]["usd"] == 0
            if cell["task_id"] == 900101:
                assert result["dataset_kind"] == "controlled_synthetic_extension"
                hashes_ok = all(
                    sha(raw.extractfile(prefix + "workspace/" + name).read()) == wanted
                    for name, wanted in fixture["input_files"].items()
                )
                packet = read(HERE / "blind-review" / (label + "-packet.json"))
                assert hashes_ok == packet["input_hashes_match"]
            rows.append(row)
        ledger = archived_json(raw, "spend-ledger.json")
        known = sum(
            Decimal(str(r["actual_usd"])) for r in ledger["requests"] if r["actual_usd"] is not None
        )
        assert known == Decimal(ledger["known_usd"]) == Decimal(decision["costs"]["known_usd"])
        assert len(ledger["requests"]) == decision["costs"]["all_requests"]
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
    assert groups == decision["group_results"]
    changed = groups["synthetic_extension"]
    retained = groups["original_retention"]
    sp = "selective_patch"
    c = "verified_component_memory"
    gate = (
        all(changed[c][k] > changed[sp][k] for k in ["completed", "core"])
        and changed[c]["TF"] >= changed[sp]["TF"]
        and all(retained[c][k] >= retained[sp][k] for k in ["completed", "core", "TF"])
    )
    assert gate == decision["development_gate_passed"]
    assert decision["goal_complete"] is False
    return {
        "verified": True,
        "source_files": len(plan["files"]),
        "raw_files": len(manifest["files"]),
        "cells": len(rows),
        "first_valid_judge_slots": 20,
        "strict_dual_development_gate": gate,
        "original_goal_complete": False,
        "known_usd": str(known),
    }


if __name__ == "__main__":
    result = verify()
    (HERE / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))

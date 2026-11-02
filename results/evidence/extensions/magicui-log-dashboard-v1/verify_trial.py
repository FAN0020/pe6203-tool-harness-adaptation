"""Offline standard-library verification of frozen inputs, blinded reviews and trial results."""

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
            digest = hashlib.sha256()
            with source.extractfile(name) as stream:
                while block := stream.read(1024 * 1024):
                    digest.update(block)
            assert digest.hexdigest() == wanted, name
        fixture = archived_json(
            source,
            "experiments/extensions/magicui-log-dashboard-v1/datasets/development/manifest.json",
        )
        task = archived_json(
            source, "experiments/extensions/magicui-log-dashboard-v1/task-development.json"
        )
        assert task["idx"] == 900001 and task["dataset_kind"] == "controlled_synthetic_extension"
        assert set(task) == {"idx", "extension_id", "dataset_kind", "question", "servers"}
    review_lock = read(HERE / "blind-review/review-lock.json")
    assert review_lock["all_reviews_complete"] and review_lock["method_and_scores_hidden"]
    for mapping in ["reviews", "packets"]:
        for name, wanted in review_lock[mapping].items():
            assert sha((HERE / "blind-review" / name).read_bytes()) == wanted
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
                for dimension in ("task_fulfillment", "planning_and_efficiency", "grounding"):
                    assert type(parsed[dimension]) is int and 1 <= parsed[dimension] <= 10
                    assert parsed[dimension] == item["result"][dimension]
            tf = statistics.mean(x["result"]["task_fulfillment"] for x in evaluation["runs"])
            pe = statistics.mean(x["result"]["planning_and_efficiency"] for x in evaluation["runs"])
            assert tf == result["TF"] and pe == result["PE"]
            review = read(HERE / "blind-review" / f"{cell['id']}-review.json")
            row = next(r for r in decision["rows"] if r["id"] == cell["id"])
            assert row["TF"] == tf and row["PE"] == pe and row["core"] == review["core"]
            assert row["normal_completion"] == (result["execution_status"] == "completed")
            assert result["cost"]["update"]["calls"] == 0 and result["cost"]["update"]["usd"] == 0
            if cell["task_id"] == 900001:
                assert result["dataset_kind"] == "controlled_synthetic_extension"
                for filename, wanted in fixture["input_files"].items():
                    assert sha(raw.extractfile(prefix + "workspace/" + filename).read()) == wanted
                for absent in ["parse-logs.cjs", "public/data.json", "public/index.html"]:
                    assert prefix + "workspace/" + absent not in manifest["files"]
                events = archived_json(raw, prefix + "raw_trace.json")["events"]
                initial = json.dumps(next(x for x in events if x["type"] == "initial_messages"))
                assert not any(
                    x in initial for x in ["oracle.json", "/datasets/", "check_artifacts.py"]
                )
                last = [e for e in events if e["type"] == "agent_response"][-1]["response"]
                assert last["choices"][0]["finish_reason"] == "length"
                assert last["usage"]["completion_tokens"] == 4096
                assert last["usage"]["completion_tokens_details"]["reasoning_tokens"] == 4096
            rows.append(row)
        for scope in ("synthetic_extension", "original_retention"):
            for strategy in ("selective_patch", "native_argument_routing"):
                subset = [r for r in rows if r["scope"] == scope and r["strategy"] == strategy]
                actual = {
                    "n": len(subset),
                    "completed": sum(r["normal_completion"] for r in subset),
                    "core": sum(r["core"] for r in subset),
                    "TF": statistics.mean(r["TF"] for r in subset),
                    "PE": statistics.mean(r["PE"] for r in subset),
                    "ECS": None,
                }
                assert actual == decision["group_results"][scope][strategy]
        sp = decision["group_results"]["synthetic_extension"]["selective_patch"]
        candidate = decision["group_results"]["synthetic_extension"]["native_argument_routing"]
        dev_pass = (
            candidate["completed"] >= sp["completed"]
            and candidate["core"] >= sp["core"]
            and (candidate["completed"] > sp["completed"] or candidate["core"] > sp["core"])
            and candidate["TF"] >= sp["TF"]
        )
        retention = decision["group_results"]["original_retention"]
        dev_pass &= all(
            retention["native_argument_routing"][k] >= retention["selective_patch"][k]
            for k in ("completed", "core", "TF")
        )
        assert dev_pass is False and decision["development_gate_passed"] is False
        assert not decision["validation_started"] and not decision["goal_complete"]
        ledger = archived_json(raw, "spend-ledger.json")
        total = sum(Decimal(str(r["actual_usd"])) for r in ledger["requests"])
        assert total == Decimal(ledger["known_usd"]) == Decimal(decision["costs"]["known_usd"])
        assert Decimal(ledger["unknown_reserved_usd"]) == 0
        assert len(ledger["requests"]) == 37
        assert all(
            r["actual_provider"] == "DigitalOcean"
            and r["actual_model"] == "deepseek/deepseek-v4.1-flash-1017"
            for r in ledger["requests"]
        )
        for task_id in [235, 900001]:
            sp = archived_json(raw, f"adaptations/{task_id}-late-selective_patch/knowledge.json")
            candidate = archived_json(
                raw, f"adaptations/{task_id}-late-native_argument_routing/knowledge.json"
            )
            if task_id == 235:
                assert sp == candidate == archived_json(raw, "catalogs/235/early.json")
            else:
                a, b = [{t["tool_id"]: t for t in k["tools"]} for k in (sp, candidate)]
                delta = [(i, k) for i in a for k in a[i] if a[i][k] != b[i][k]]
                assert len(delta) == 7 and all(k == "description" for _, k in delta)
    summary = {
        "verified": True,
        "source_files": len(plan["files"]),
        "raw_files": len(manifest["files"]),
        "cells": 4,
        "judge_slots": 20,
        "requests": 37,
        "usd": str(total),
        "pilot_passed": False,
        "original_goal_complete": False,
        "requires_network": False,
    }
    (HERE / "verification.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    verify()

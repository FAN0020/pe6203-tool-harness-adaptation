"""Verify a terminal interrupted snapshot; never infer16-cell or promotion success."""

import json, tarfile
from decimal import Decimal
from pathlib import Path
from raw_cell_verifier import archive_files, inspect_cell, sha

E = Path(__file__).resolve().parent


def main():
    files, manifest = archive_files(E / "interruption-1")
    prefix = manifest["prefix"] + "/"

    def read(name):
        return json.loads(files[prefix + name])

    plan = read("plan.json")
    assert len(plan["cells"]) == 16 and plan["cells"] == plan["diagnostic_spec"]["schedule"]
    assert sha(files[prefix + "plan.json"]) == files[prefix + "plan.sha256"].decode().strip()
    sm = json.loads((E / "prefreeze-manifest.json").read_text())
    assert sha((E / sm["archive"]).read_bytes()) == sm["archive_sha256"]
    with tarfile.open(E / sm["archive"]) as tf:
        source = {m.name: tf.extractfile(m).read() for m in tf if m.isfile()}
    assert all(sha(source[k]) == v for k, v in plan["files"].items())
    lock = read("knowledge-lock.json")
    assert lock["plan_sha256"] == sha(files[prefix + "plan.json"])
    assert all(sha(files[prefix + k]) == v for k, v in lock["files"].items())
    kr = read("knowledge-review.json")
    assert kr["accepted"] and kr["lock_sha256"] == sha(files[prefix + "knowledge-lock.json"])
    for x in kr["equalities"]:
        b = files[prefix + f"adaptations/{x['task']}-late-{x['arm']}/knowledge.json"]
        assert b == source[x["prior_knowledge"]] and sha(b) == x["knowledge_sha256"]
    state = read("experiment.json")
    assert state["stop_reason"] == "spend_guard" and len(state["cells"]) == 7
    assert [state["cells"][f"cell-{i:03d}"]["status"] for i in range(1, 8)] == ["evaluated"] * 6 + [
        "judge_incomplete"
    ]
    for x in state["cells"].values():
        assert all(sha(files[prefix + k]) == v for k, v in x["files"].items())
    freeze = json.loads((E / "review-freeze-at-stop.json").read_text())
    assert freeze["all_reviews_before_scores"] is False
    assert freeze["per_review_before_own_scores"] == {f"F{i:02d}": i < 7 for i in range(1, 8)}
    assert all(sha((E / k).read_bytes()) == v for k, v in freeze["files"].items())
    api = {}
    exec(
        compile(source["src/pe6203/project_episode_projection.py"], "frozen_auditor.py", "exec"),
        api,
    )
    rows = []
    ids = []
    cases = {c["task_id"]: c for c in plan["diagnostic_spec"]["cases"]}
    for i, cell in enumerate(plan["cells"][:7], 1):
        rid = f"F{i:02d}"
        review = json.loads((E / "individual-reviews" / f"{rid}.json").read_text())
        packet = json.loads((E / "review-inputs" / f"{rid}.json").read_text())
        assert review["input_sha256"] == sha((E / "review-inputs" / f"{rid}.json").read_bytes())
        assert set(review["properties"]) == {"records", "fields", "structure", "delivery"}
        assert set(review["properties"].values()) <= {"pass", "fail", "unknown"} and review[
            "core_pass"
        ] == all(v == "pass" for v in review["properties"].values())
        names = [
            n
            for n in files
            if n.startswith(prefix + f"cells/{cell['id']}/run/workspace/")
            and n.endswith("/tasks.json")
        ]
        assert len(names) == 1
        store = json.loads(files[names[0]])
        oracle = json.loads(
            source[
                f"experiments/extensions/dependency-factorial-v1/evaluation/oracle-{cell['task_id']}.json"
            ]
        )
        assert api["audit_store"](oracle, store) == packet["properties"] and all(
            review["properties"][k] == v for k, v in packet["properties"].items()
        )
        assert (
            sha(files[names[0]]) == packet["store_sha256"]
            and files[names[0]] == (E / packet["store_path"]).read_bytes()
        )
        assert (
            sha(files[prefix + f"cells/{cell['id']}/run/raw_trace.json"]) == packet["trace_sha256"]
        )
        row, response_ids = inspect_cell(
            files,
            prefix,
            cell,
            "controlled_factorial_interrupted_snapshot",
            allow_incomplete=i == 7,
        )
        ids.extend(response_ids)
        row.update(
            review_id=rid,
            properties=review["properties"],
            core_pass=review["core_pass"],
            block_index=cell["seed"],
            topology=cases[cell["task_id"]]["topology"],
            payload=cases[cell["task_id"]]["payload"],
            review_before_own_scores=i < 7,
        )
        rows.append(row)
    ledger = read("spend-ledger.json")
    assert (
        ledger["policy"]["limit_usd"] is None
        and ledger["blocked"]
        and ledger["stop_reason"] == "unknown_charge"
    )
    settled = [r for r in ledger["requests"] if r["status"] == "settled"]
    unknown = [r for r in ledger["requests"] if r["status"] != "settled"]
    assert len(unknown) == 1 and unknown[0]["status"] == "unknown_charge"
    assert (
        unknown[0]["error_type"] == "APITimeoutError"
        and unknown[0]["actual_usd"] is None
        and "response_id" not in unknown[0]
    )
    assert all(
        r["actual_provider"] == "DigitalOcean" and r["actual_model"] == ledger["policy"]["model"]
        for r in settled
    )
    pre = [r for r in settled if r["max_completion_tokens"] == 32]
    assert len(pre) == 2
    assert len(ids) == len(set(ids)) and set(ids) == {
        r["response_id"] for r in settled if r not in pre
    }
    known = sum((Decimal(r["actual_usd"]) for r in settled), Decimal(0))
    reserve = sum((Decimal(r["reserved_usd"]) for r in unknown), Decimal(0))
    assert known == Decimal(ledger["known_usd"]) and reserve == Decimal(
        ledger["unknown_reserved_usd"]
    )
    for cell in plan["cells"][7:]:
        assert not any(k.startswith(prefix + f"cells/{cell['id']}/") for k in files)
    print(
        json.dumps(
            {
                "verified_partial_snapshot": True,
                "complete_study": False,
                "raw_files": len(files),
                "source_files": len(source),
                "planned_cells": 16,
                "executed_actors": 7,
                "evaluated_cells": 6,
                "incomplete_judge_cells": 1,
                "not_started_cells": 9,
                "normal_completed_actors": sum(r["execution_status"] == "completed" for r in rows),
                "core_pass_actors": sum(r["core_pass"] for r in rows),
                "rows": rows,
                "known_usd": str(known),
                "unknown_charge_items": 1,
                "unknown_reserved_usd": str(reserve),
                "reserve_is_actual_charge": False,
                "api_requests": len(ledger["requests"]),
                "settled_requests": len(settled),
                "completed_judge_slots": 32,
                "planned_judge_slots": 80,
                "updater_calls": 0,
                "original_candidate_reopened": False,
                "validation_started": False,
                "goal_complete": False,
                "decision": "Inconclusive factorial study, held at actual unknown-charge stop. Preserve exact schedule and all data; no actor restart or extra sampling.",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

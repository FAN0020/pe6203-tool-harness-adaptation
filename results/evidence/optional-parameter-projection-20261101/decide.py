"""Verify the frozen nine-cell trial only after all blind property reviews exist."""

import json
from decimal import Decimal
from pathlib import Path
from statistics import mean

from pe6203.experiment import freeze_files, sha, summarize, verify_files
from pe6203.strategy_search import check_knowledge

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
RAW = ROOT / "results/raw/optional-parameter-projection-pilot-20261101"


def save(p, d):
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n")


def main():
    mapping = json.loads((HERE / "blind-map.json").read_text())
    reviews = {
        rid: json.loads((HERE / "blind-reviews" / (rid + ".json")).read_text()) for rid in mapping
    }
    assert len(reviews) == 9
    for rid, review in reviews.items():
        assert review["input_sha256"] == sha(HERE / "blind-inputs" / (rid + ".json"))
        assert review["core_pass"] == all(v == "pass" for v in review["properties"].values())
    if not (HERE / "review-freeze.json").exists():
        save(
            HERE / "review-freeze.json",
            {
                "before_unblinding": True,
                "files": freeze_files(
                    ROOT,
                    list((HERE / "blind-reviews").glob("*.json"))
                    + list((HERE / "blind-inputs").glob("*.json")),
                ),
            },
        )
    verify_files(ROOT, json.loads((HERE / "review-freeze.json").read_text())["files"])
    plan = json.loads((RAW / "plan.json").read_text())
    verify_files(ROOT, plan["files"])
    check_knowledge(RAW)
    summary = summarize(RAW)
    assert summary["planned"] == summary["scored"] == 9
    reverse = {v: k for k, v in mapping.items()}
    rows = []
    for row in summary["rows"]:
        review = reviews[reverse[row["id"]]]
        trace = json.loads((RAW / "cells" / row["id"] / "run/raw_trace.json").read_text())
        counts = {}
        for event in trace["events"]:
            if event["type"] == "tool_result":
                name = event["call"]["function"]["name"]
                counts[name] = counts.get(name, 0) + 1
        rows.append(
            {
                **row,
                "review_id": reverse[row["id"]],
                "properties": review["properties"],
                "core_pass": review["core_pass"],
                "tool_counts": counts,
            }
        )
    metrics = {}
    for strategy in ["selective_patch", "semantic_contract_direct", "optional_parameter_projection"]:
        metrics[strategy] = {}
        for group, task in [("changed", 133), ("retention", 235)]:
            rs = [r for r in rows if r["strategy"] == strategy and r["task_id"] == task]
            metrics[strategy][group] = {
                "n": len(rs),
                "completed": sum(r["execution_status"] == "completed" for r in rs),
                "core_pass": sum(r["core_pass"] for r in rs),
                "TF": mean(r["TF"] for r in rs),
                "PE": mean(r["PE"] for r in rs),
            }
    b = metrics["selective_patch"]
    c = metrics["optional_parameter_projection"]
    gates = {
        "completion_strict_gain": c["changed"]["completed"] > b["changed"]["completed"],
        "quality_strict_gain": c["changed"]["core_pass"] > b["changed"]["core_pass"],
        "TF_nondecrease": c["changed"]["TF"] >= b["changed"]["TF"],
        "retention_nondecrease": all(
            c["retention"][k] >= b["retention"][k] for k in ["completed", "core_pass", "TF"]
        ),
    }
    ledgers = {}
    ids = []
    for label, path in [("actor_judge_preflight", "results/raw/optional-parameter-projection-costs-20261101/spend-ledger.json")]:
        d = json.loads((ROOT / path).read_text())
        req = d["requests"]
        known = sum(Decimal(x.get("actual_usd") or "0") for x in req)
        assert known == Decimal(d["known_usd"])
        assert all(
            x["actual_model"] == "deepseek/deepseek-v4.1-flash-1017"
            and x["actual_provider"] == "DigitalOcean"
            for x in req
            if x["status"] == "settled"
        )
        ids += [x["response_id"] for x in req if x.get("response_id")]
        ledgers[label] = {
            "path": path,
            "sha256": sha(ROOT / path),
            "requests": len(req),
            "known_usd": str(known),
            "unknown_reserved_usd": d["unknown_reserved_usd"],
            "unsettled": sum(x["status"] != "settled" for x in req),
        }
    assert len(ids) == len(set(ids))
    result = {
        "rows": rows,
        "metrics": metrics,
        "gates": gates,
        "decision": "advance_frozen_candidate"
        if all(gates.values())
        else "reject_optional_projection_v1_no_validation",
        "goal_complete": False,
        "validation_started": False,
        "ledgers": ledgers,
        "round_total_usd": str(sum(Decimal(v["known_usd"]) for v in ledgers.values())),
        "ECS": None,
        "scope": "Original benchmark development only; exposed133M/L+235L,1repeat each; no unseen-task or population causal claim; v2 direct contemporaneous diagnostic only; no syntheticbenchmarkrun.",
        "reused_updater_cost_usd": "0.003234600; prior v2 one-time generation, not new marginal spend",
    }
    save(HERE / "decision.json", result)
    print(
        json.dumps({k: v for k, v in result.items() if k != "rows"}, ensure_ascii=False, indent=2)
    )


if __name__ == "__main__":
    main()

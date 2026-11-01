"""Read only visible outputs and response metadata; never expose hidden reasoning."""
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RAW = ROOT / "results/raw/evidence-dispatch-pilot-20261101"


def main():
    decision = json.loads((HERE / "decision.json").read_text())
    rows = []
    for row in decision["rows"]:
        trace = json.loads((RAW / "cells" / row["cell_id"] / "run/raw_trace.json").read_text())
        responses = [e["response"] for e in trace["events"] if e["type"] == "agent_response"]
        last = responses[-1]
        calls = [e for e in trace["events"] if e["type"] == "tool_result"]
        counts = Counter(e["call"]["function"]["name"].split("__")[0] for e in calls)
        errors = [{"tool": e["call"]["function"]["name"].split("__")[0], "result": e["result"]} for e in calls if e["result"].get("isError")]
        rows.append({
            "review_id": row["review_id"], "task_id": row["task_id"], "stage": row["stage"],
            "strategy": row["strategy"], "execution_status": row["execution_status"],
            "response_count": len(responses), "finish_reason": last["choices"][0].get("finish_reason"),
            "last_completion_tokens": last.get("usage", {}).get("completion_tokens"),
            "last_reasoning_token_count": last.get("usage", {}).get("completion_tokens_details", {}).get("reasoning_tokens"),
            "visible_final_characters": len(trace.get("answer") or ""), "call_counts": dict(counts),
            "thinking_tool_calls": sum(v for k, v in counts.items() if k in {"sequentialthinking", "parallel-thinking", "convergent-synthesis"}),
            "tool_errors": errors,
        })
    ledger = json.loads((ROOT / "results/raw/evidence-dispatch-dev-costs-20261101/spend-ledger.json").read_text())
    before = json.loads((HERE / "credential-readiness.json").read_text())
    after = json.loads((HERE / "balance-after.json").read_text())
    usage_delta = Decimal(str(after["usage_usd"])) - Decimal(str(before["keys"]["backup"]["usage_usd"]))
    sensitivity = json.loads((HERE / "review-sensitivity.json").read_text())
    overrides = {x["review_id"]: x["most_permissive_override"] for x in sensitivity["alternatives"]}
    alternate = {}
    for arm in ("selective_patch", "evidence_dispatch"):
        alternate[arm] = {}
        for group, tasks in (("project", {283}), ("changed", {133, 283}), ("retention", {235})):
            rs = [r for r in decision["rows"] if r["strategy"] == arm and r["task_id"] in tasks]
            alternate[arm][group] = sum(all(v == "pass" for v in {**r["properties"], **overrides.get(r["review_id"], {})}.values()) for r in rs)
    output = {
        "hidden_reasoning_read": False, "interpretation": "Stop fields establish stopping/truncation, not their cause.",
        "rows": rows, "actor_requests": sum(r["response_count"] for r in rows),
        "judge_slots": decision["judge_slots"], "preflight_requests": 2,
        "ledger_statuses": dict(Counter(r["status"] for r in ledger["requests"])),
        "known_usd": ledger["known_usd"], "remaining_backup_usd": after["remaining_usd"],
        "aggregate_usage_delta_usd": str(usage_delta),
        "aggregate_matches_new_ledger": usage_delta == Decimal(ledger["known_usd"]),
        "old_unknown_charge_settled": False,
        "sensitivity_core_counts": alternate,
        "sensitivity_promotes": False,
        "sensitivity_reason": "All four project executions lack final delivery and normal completion. Even permissive R01 code acceptance cannot satisfy the project strict dual gate.",
    }
    assert output["actor_requests"] + 50 + 2 == decision["api_requests"]
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

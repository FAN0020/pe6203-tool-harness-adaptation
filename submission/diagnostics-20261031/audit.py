"""Independent, standard-library-only audit. Never imports the experiment runner."""

import argparse
import hashlib
import json
import math
from collections import Counter
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/raw/course-targeted-diagnostics-20261031"
DELIVERY = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument("--raw", type=Path, default=OUT)
parser.add_argument("--output", type=Path, default=DELIVERY)
parser.add_argument("--previous-root", type=Path, default=ROOT)
parser.add_argument(
    "--skip-prior-evidence",
    action="store_true",
    help="Audit the four trajectories only; explicitly omit the separate historical-preservation check",
)
options = parser.parse_args()
OUT, DELIVERY = options.raw.resolve(), options.output.resolve()
DELIVERY.mkdir(parents=True, exist_ok=True)


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p, v):
    p.write_text(json.dumps(v, ensure_ascii=False, indent=2) + "\n")


def tool(k, name):
    return next(x for x in k["tools"] if x["tool_id"] == name)


def differences(a, b, path=""):
    if isinstance(a, dict) and isinstance(b, dict):
        found = []
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                found.append({"path": path + "/" + k, "A": a.get(k), "B": b.get(k)})
            else:
                found.extend(differences(a[k], b[k], path + "/" + k))
        return found
    if a != b:
        return [{"path": path, "A": a, "B": b}]
    return []


def knowledge_diffs(a, b):
    assert {k: v for k, v in a.items() if k != "tools"} == {
        k: v for k, v in b.items() if k != "tools"
    }
    assert [x["tool_id"] for x in a["tools"]] == [x["tool_id"] for x in b["tools"]]
    return [
        d
        for x, y in zip(a["tools"], b["tools"], strict=True)
        for d in differences(x, y, x["tool_id"])
    ]


plan = read(OUT / "plan.json")
assert sha(OUT / "plan.json") == (OUT / "plan.sha256").read_text().strip()
pairs = {}
for key, aa, bb in [
    ("under", "under_omitted", "under_complete"),
    ("over", "over_note", "over_reverted"),
]:
    a, b = [read(OUT / f"knowledge/{x}.json") for x in [aa, bb]]
    pairs[key] = knowledge_diffs(a, b)
assert {d["path"] for d in pairs["under"]} == {
    "math-mcp::validate_syntax/parameters/properties/allow_variables",
    "math-mcp::validate_syntax/parameters/required",
}
assert [d["path"] for d in pairs["over"]] == ["math-mcp::evaluate/usage_rules"]
write(DELIVERY / "exact-knowledge-diffs.json", pairs)

rows = []
unknown_requests = []
known_usd = 0.0
ledger = read(OUT / "ledger.json")
for cell in plan["cells"]:
    p = OUT / "cells" / cell["id"] / "run"
    if not (p / "result.json").exists():
        continue
    for name, h in ledger["cells"][cell["id"]]["files"].items():
        assert sha(OUT / name) == h, name
    result, trace = read(p / "result.json"), read(p / "raw_trace.json")
    operational = {
        "root",
        "output_dir",
        "knowledge_path",
        "update_cost",
        "experiment_kind",
        "diagnostic_plan_sha256",
    }
    assert {k: v for k, v in result["config"].items() if k not in operational} == plan["config"]
    assert result["model_endpoints"] == plan["endpoints"]
    assert read(p / "knowledge.json") == read(OUT / f"knowledge/{cell['id']}.json")
    assert read(p / "environment-metadata.json") == read(OUT / f"catalogs/133/{cell['stage']}.json")
    assert {k: trace[k] for k in plan["task"]} == plan["task"]
    events = trace["events"]
    responses = [e for e in events if e["type"] == "agent_response"]
    last = responses[-1]["response"]["choices"][0] if responses else None
    if any(e["type"] == "agent_error" for e in events):
        actual = "failed"
    elif last and last["finish_reason"] == "length":
        actual = "output_truncated"
    elif last and last["finish_reason"] == "content_filter":
        actual = "content_filtered"
    elif last and not last["message"].get("tool_calls"):
        actual = "completed" if last["message"].get("content") else "empty_answer"
    elif len(responses) == plan["config"]["max_rounds"]:
        actual = "max_rounds"
    else:
        actual = "unresolved"
    assert actual == result["execution_status"], cell["id"]
    eval_data = read(p / "EVAL/133.json")["eval_result"] if (p / "EVAL/133.json").exists() else None
    ratings = []
    agent_usd = []
    judge_usd = []
    if eval_data:
        assert len(eval_data["runs"]) == 5
        for slot, selected in enumerate(eval_data["runs"], 1):
            attempts = [a for a in eval_data["attempts"] if a["slot"] == slot]
            assert next(a for a in attempts if "result" in a and not a.get("error")) == selected
            for a in attempts:
                folder = p / "judge-attempts" / f"slot-{slot}-attempt-{a['attempt']}"
                assert read(folder / "outcome.json") == a
                if "response" in a:
                    assert read(folder / "response.json") == a["response"]
                    usage = a["response"].get("usage") or {}
                    cost = usage.get("cost")
                    judge_usd.append(cost)
                    if cost is None:
                        unknown_requests.append(
                            {
                                "cell": cell["id"],
                                "role": "judge",
                                "slot": slot,
                                "attempt": a["attempt"],
                            }
                        )
                else:
                    judge_usd.append(None)
                    unknown_requests.append(
                        {"cell": cell["id"], "role": "judge", "slot": slot, "attempt": a["attempt"]}
                    )
            content = json.loads(selected["response"]["choices"][0]["message"]["content"])
            for k in ["task_fulfillment", "planning_and_efficiency"]:
                assert type(content[k]) is int and 1 <= content[k] <= 10
                assert content[k] == selected["result"][k]
            ratings.append(
                {"TF": content["task_fulfillment"], "PE": content["planning_and_efficiency"]}
            )
    for e in events:
        if e["type"] == "agent_response":
            cost = (e["response"].get("usage") or {}).get("cost")
            agent_usd.append(cost)
            if cost is None:
                unknown_requests.append({"cell": cell["id"], "role": "agent", "round": e["round"]})
        if e["type"] in ["request_retry", "agent_error"] and e.get("role", "agent") == "agent":
            agent_usd.append(None)
            unknown_requests.append(
                {"cell": cell["id"], "role": "agent", "round": e["round"], "type": e["type"]}
            )
    for role, amounts in [("agent", agent_usd), ("judge", judge_usd)]:
        usages = (
            [(e["response"].get("usage") or {}) for e in responses]
            if role == "agent"
            else [
                (attempt.get("response", {}).get("usage") or {})
                for attempt in (eval_data or {}).get("attempts", [])
            ]
        )
        for field in ["prompt_tokens", "completion_tokens", "total_tokens"]:
            total = (
                sum(usage[field] for usage in usages)
                if usages
                and all(type(usage.get(field)) is int for usage in usages)
                and None not in amounts
                else None
            )
            assert total == result["cost"][role][field], (cell["id"], role, field)
        known = sum(x for x in amounts if x is not None)
        known_usd += known
        assert math.isclose(known, result["cost"][role]["known_usd"], abs_tol=1e-12)
        assert (result["cost"][role]["usd"] is None) == (not amounts or None in amounts)
    assert result["cost"]["update"]["usd"] == result["cost"]["update"]["total_tokens"] == 0
    scores = {
        k: float(sum(Fraction(r[k]) for r in ratings) / 5) if ratings else None
        for k in ["TF", "PE"]
    }
    assert all(scores[k] == result[k] for k in scores)
    calls = []
    proposed = []
    for e in events:
        if e["type"] == "agent_response":
            proposed.extend(e["response"]["choices"][0]["message"].get("tool_calls") or [])
        if e["type"] != "tool_result":
            continue
        assert e["call"] in proposed
        f = e["call"]["function"]
        route = result["model_tool_routes"][f["name"]]
        args = json.loads(f["arguments"])
        calls.append(
            {
                "round": e["round"],
                "tool": route["server_id"] + "::" + route["tool_name"],
                "arguments": args,
                "observation": e["result"],
            }
        )
    val = [c for c in calls if c["tool"] == "math-mcp::validate_syntax"]
    ev = [c for c in calls if c["tool"] == "math-mcp::evaluate"]
    first_round = min((c["round"] for c in val), default=999)
    row = {
        **cell,
        **scores,
        "ratings": ratings,
        "actual_completion": actual,
        "agent_rounds": len(responses),
        "tool_calls": len(calls),
        "tool_errors": sum(bool(c["observation"].get("isError")) for c in calls),
        "validate_calls": len(val),
        "missing_allow_variables_calls": sum("allow_variables" not in c["arguments"] for c in val),
        "missing_allow_variables_rejections": sum(
            "allow_variables" not in c["arguments"]
            and bool(c["observation"].get("isError"))
            and "allow_variables" in json.dumps(c["observation"])
            for c in val
        ),
        "evaluate_calls": len(ev),
        "evaluate_later_than_first_validation_round": sum(c["round"] > first_round for c in ev),
        "tool_counts": dict(Counter(c["tool"] for c in calls)),
        "first_validation": val[0] if val else None,
        "calls": calls,
        "known_agent_usd": sum(x for x in agent_usd if x is not None),
        "agent_tokens": result["cost"]["agent"]["total_tokens"],
        "judge_tokens": result["cost"]["judge"]["total_tokens"],
        "model_requests": len(agent_usd) + len(judge_usd),
        "known_judge_usd": sum(x for x in judge_usd if x is not None),
        "seconds": result["seconds"],
        "answer": trace.get("answer", ""),
    }
    rows.append(row)

preserved_count = None
if not options.skip_prior_evidence:
    old = read(options.previous_root / "submission/evidence/corpus-manifest.json")
    for item in old:
        p = options.previous_root / item["path"]
        assert p.stat().st_size == item["bytes"] and sha(p) == item["sha256"], item["path"]
    preserved_count = len(old)
result = {
    "kind": plan["kind"],
    "plan_sha256": sha(OUT / "plan.json"),
    "verified_cells": len(rows),
    "valid_judge_ratings": sum(len(r["ratings"]) for r in rows),
    "rows": rows,
    "known_usd": known_usd,
    "unknown_requests": unknown_requests,
    "elapsed_execution_seconds": sum(r["seconds"] for r in rows),
    "prior_evidence_members_unchanged": preserved_count,
    "control_differences": pairs,
    "interpretation": "Controlled diagnostics, separate from natural benchmark observations. Classification requires reviewing the exact calls and outcomes. No ECS is defined for a two-condition single-stage diagnostic.",
}
write(DELIVERY / "audit.json", result)
print(
    json.dumps(
        {
            k: result[k]
            for k in [
                "verified_cells",
                "valid_judge_ratings",
                "known_usd",
                "unknown_requests",
                "elapsed_execution_seconds",
                "prior_evidence_members_unchanged",
            ]
        }
    )
)
print(
    json.dumps(
        [
            {
                k: r[k]
                for k in [
                    "id",
                    "TF",
                    "PE",
                    "actual_completion",
                    "tool_calls",
                    "tool_errors",
                    "missing_allow_variables_rejections",
                    "evaluate_calls",
                ]
            }
            for r in rows
        ]
    )
)

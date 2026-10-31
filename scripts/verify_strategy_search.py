"""Audit saved research executions without issuing model or MCP requests."""

import argparse
import json
import math
import statistics
from collections import Counter
from pathlib import Path

from pe6203.benchmark import read_json, write_json
from pe6203.evaluation import judge_scores
from pe6203.experiment import adaptation_path, sha, verify_files
from pe6203.runner import digest, prepare_tools, protocol_hash
from pe6203.selective import diff_catalogs, validate_adaptation
from pe6203.strategy_search import check_knowledge


def audit(root, output, partial=False):
    root, output = Path(root).resolve(), Path(output).resolve()
    plan = read_json(output / "plan.json")
    assert sha(output / "plan.json") == (output / "plan.sha256").read_text().strip()
    verify_files(root, plan["files"])
    check_knowledge(output)
    ledger = read_json(output / "experiment.json")
    expected_protocol = protocol_hash(
        plan["config"], {k: v for k, v in plan["endpoints"].items() if k != "updater"}
    )
    artifacts, executions = [], []
    seen = set()
    for cell in plan["cells"]:
        a_path = adaptation_path(output, plan, cell)
        a = read_json(a_path)
        knowledge = read_json(a_path.parent / "knowledge.json")
        if a_path not in seen:
            seen.add(a_path)
            old = read_json(output / "catalogs" / str(cell["task_id"]) / "early.json")
            target = read_json(
                output / "catalogs" / str(cell["task_id"]) / f"{cell['version']}.json"
            )
            diff = diff_catalogs(old, target)
            if cell["strategy"] == "no_update" or cell["version"] == "early":
                assert knowledge == old
            elif cell["strategy"] == "full_rewrite":
                restored = json.loads(json.dumps(knowledge))
                descriptions = {t["tool_id"]: t["description"] for t in target["tools"]}
                for tool in restored["tools"]:
                    tool["description"] = descriptions[tool["tool_id"]]
                assert restored == target
            elif not any(diff[f] for f in ["added", "removed", "changed"]):
                assert knowledge == old
            else:
                modified = {
                    c["tool_id"]
                    for c in a["patch"]
                    if c.get("operation") in ["append_delta_note", "append_semantic_note"]
                }
                assert not validate_adaptation(knowledge, old, target, diff, modified)["errors"]
            artifacts.append(
                {"path": str(a_path.relative_to(output)), "sha256": sha(a_path), "cost": a["cost"]}
            )
        directory = output / "cells" / cell["id"] / "run"
        item = ledger["cells"].get(cell["id"], {})
        if item.get("status") != "evaluated":
            if partial:
                continue
            raise AssertionError(f"Nonterminal or unevaluated cell: {cell['id']}")
        verify_files(output, item["files"])
        result = read_json(directory / "result.json")
        assert result["protocol_sha256"] == expected_protocol
        assert result["knowledge_sha256"] == digest(knowledge)
        assert result["adaptation_file_sha256"] == sha(a_path)
        assert read_json(directory / "knowledge.json") == knowledge
        assert result["strategy"] == cell["strategy"] and result["version"] == cell["version"]
        _, routes = prepare_tools(knowledge["tools"], cell["strategy"], "namespaced")
        assert result["model_tool_routes"] == routes
        evaluation = read_json(directory / "EVAL" / f"{cell['task_id']}.json")
        scores, issue = judge_scores(evaluation)
        assert scores is not None, issue
        for dimension, field in [("TF", "task_fulfillment"), ("PE", "planning_and_efficiency")]:
            raw_scores = [
                json.loads(r["response"]["choices"][0]["message"]["content"])[field]
                for r in evaluation["eval_result"]["runs"]
            ]
            assert len(raw_scores) == 5
            assert math.isclose(statistics.mean(raw_scores), scores[dimension], abs_tol=1e-12)
            assert math.isclose(result[dimension], scores[dimension], abs_tol=1e-12)
        trace = read_json(directory / "raw_trace.json")
        selected, executed = Counter(), Counter()

        def signature(call):
            return call["id"], call["function"]["name"], call["function"]["arguments"]

        for event in trace["events"]:
            if event["type"] == "agent_response":
                for call in event["response"]["choices"][0]["message"].get("tool_calls") or []:
                    selected[signature(call)] += 1
            if event["type"] == "tool_result":
                executed[signature(event["call"])] += 1
        assert not executed - selected, "Executed tool call not selected by the agent"
        executions.append(
            {
                "id": cell["id"],
                **scores,
                "execution_status": result["execution_status"],
                "model_selected_calls": sum(selected.values()),
                "executed_calls": sum(executed.values()),
            }
        )
    report = {
        "status": "partial_verified" if partial else "verified",
        "planned": len(plan["cells"]),
        "verified": len(executions),
        "valid_rating_slots": len(executions) * 5,
        "checks": [
            "frozen sources and artifacts",
            "schema/routing/description boundaries",
            "exact K0 where required",
            "identical agent/judge protocol",
            "raw five judge scores",
            "every executed tool call was agent-selected",
        ],
        "artifacts": artifacts,
        "executions": executions,
    }
    write_json(output / "verification.json", report)
    print(
        json.dumps(
            {k: v for k, v in report.items() if k not in ["artifacts", "executions"]},
            ensure_ascii=False,
        )
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--partial", action="store_true")
    args = parser.parse_args()
    audit(args.root, args.output, args.partial)

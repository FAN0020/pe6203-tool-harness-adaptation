"""Standard-library independent audit of the archived intervention; zero API calls."""

import copy
import hashlib
import json
import statistics
import tarfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    manifest = json.loads((HERE / "raw-manifest.json").read_text())
    archive = HERE / "raw-trial.tar.gz"
    assert sha(archive.read_bytes()) == manifest["archive_sha256"]
    with tarfile.open(archive) as tar:
        files = {m.name: tar.extractfile(m).read() for m in tar if m.isfile()}
    assert {n: sha(b) for n, b in files.items()} == manifest["files"]
    prefix = manifest["prefix"] + "/"

    def read(name):
        return json.loads(files[prefix + name])

    plan = read("plan.json")
    assert sha(files[prefix + "plan.json"]) == files[prefix + "plan.sha256"].decode().strip()
    assert plan["config"]["spend_guard"]["limit_usd"] is None
    for name, digest in plan["knowledge_files"].items():
        assert sha(files[prefix + name]) == digest
    for state in read("state.json")["cells"].values():
        assert state["status"] == "evaluated"
        for name, digest in state["files"].items():
            assert sha(files[prefix + name]) == digest
    control, fault = read("knowledge/control.json"), read("knowledge/fault.json")
    changed = copy.deepcopy(control)
    tool = next(t for t in changed["tools"] if t["tool_id"] == "wikipedia-mcp::readArticle")
    tool["routing"]["tool_name"] = "read_article"
    assert changed == fault
    assert [{k: v for k, v in t.items() if k != "routing"} for t in control["tools"]] == [
        {k: v for k, v in t.items() if k != "routing"} for t in fault["tools"]
    ]
    replays = read("same-input-replay.json")["observations"]
    assert [r["condition"] for r in replays] == ["control", "fault"]
    assert replays[0]["arguments"] == replays[1]["arguments"] == {"pageId": 210648}
    assert replays[0]["model_tool_name"] == replays[1]["model_tool_name"]
    assert not replays[0]["result"].get("isError")
    content = "\n".join(c.get("text", "") for c in replays[0]["result"]["content"])
    assert len(content) > 1000 and "declarative programming" in content.lower()
    assert "Tool read_article not found" in replays[1]["exception"]
    all_ids, rows, protocols = [], [], set()
    for cell in plan["cells"]:
        base = f"cells/{cell['id']}/run/"
        result, trace = read(base + "result.json"), read(base + "raw_trace.json")
        assert result["status"] == "evaluated" and result["judge_status"] == "complete"
        assert (result["task_id"], result["version"], result["strategy"]) == (
            430,
            "late",
            "budget_feedback",
        )
        assert trace["question"] == plan["task"]["question"]
        assert read(base + "knowledge.json") == read(f"knowledge/{cell['condition']}.json")
        assert read(base + "environment-metadata.json") == read("catalog.json")
        for key, value in plan["config"].items():
            assert result["config"][key] == value
        protocols.add(result["protocol_sha256"])
        agents = [e["response"] for e in trace["events"] if e["type"] == "agent_response"]
        last = agents[-1]["choices"][0]
        status = (
            "output_truncated"
            if last["finish_reason"] == "length"
            else "max_rounds"
            if trace["exceeded"] and not trace["stop"]
            else "completed"
            if trace["stop"]
            else "unknown"
        )
        assert status == result["execution_status"]
        slots = read(base + "EVAL/430.json")["eval_result"]["runs"]
        assert sorted(s["slot"] for s in slots) == [1, 2, 3, 4, 5]
        judges, values = [], []
        for slot in slots:
            attempt = base + f"judge-attempts/slot-{slot['slot']}-attempt-{slot['attempt']}/"
            response = read(attempt + "response.json")
            parsed = json.loads(response["choices"][0]["message"]["content"])
            assert parsed == slot["result"] == read(attempt + "outcome.json")["result"]
            request = read(attempt + "request.json")
            assert request["settings"] == {
                k: v for k, v in plan["config"]["judge"].items() if not k.endswith("_env")
            }
            values.append(
                {"TF": parsed["task_fulfillment"], "PE": parsed["planning_and_efficiency"]}
            )
            judges.append(response)
        assert len(judges) == 5
        means = {metric: statistics.mean(v[metric] for v in values) for metric in ("TF", "PE")}
        assert all(abs(result[k] - v) < 1e-10 for k, v in means.items())
        charges = {}
        for role, responses in (("agent", agents), ("judge", judges)):
            assert all(
                r["model"] == plan["config"][role]["model"] and r["provider"] == "DigitalOcean"
                for r in responses
            )
            charges[role] = str(
                sum((Decimal(str(r["usage"]["cost"])) for r in responses), Decimal(0))
            )
            assert abs(
                Decimal(charges[role]) - Decimal(str(result["cost"][role]["usd"]))
            ) < Decimal("1e-12")
            all_ids.extend(r["id"] for r in responses)
        assert result["cost"]["update"]["usd"] == 0
        calls = [e for e in trace["events"] if e["type"] == "tool_result"]
        article = [e for e in calls if e["call"]["function"]["name"].startswith("readArticle__")]
        route = result["model_tool_routes"][article[0]["call"]["function"]["name"]]
        assert route["tool_name"] == (
            "read_article" if cell["condition"] == "fault" else "readArticle"
        )
        if cell["condition"] == "fault":
            assert len(article) == 2 and all(
                e["result"].get("isError")
                and "Tool read_article not found" in e["result"].get("error", "")
                for e in article
            )
        else:
            assert len(article) == 1 and not article[0]["result"].get("isError")
        rows.append(
            {
                **cell,
                **means,
                "judge_values": values,
                "execution_status": status,
                "agent_rounds": len(agents),
                "tool_calls": len(calls),
                "article_calls": [
                    {
                        "round": e["round"],
                        "function": e["call"]["function"],
                        "isError": bool(e["result"].get("isError")),
                    }
                    for e in article
                ],
                "structured_tool_errors": sum(bool(e["result"].get("isError")) for e in calls),
                "cost_usd": charges,
                "seconds": result["seconds"],
                "answer_characters": len(trace["answer"]),
                "trace_member": prefix + base + "raw_trace.json",
            }
        )
    assert len(protocols) == 1
    ledger = read("spend-ledger.json")
    assert not ledger["blocked"] and Decimal(ledger["unknown_reserved_usd"]) == 0
    assert len(all_ids) == len(set(all_ids)) == len(ledger["requests"]) == 19
    assert set(all_ids) == {r["response_id"] for r in ledger["requests"]}
    assert all(
        r["status"] == "settled" and r["actual_provider"] == "DigitalOcean"
        for r in ledger["requests"]
    )
    total = sum((Decimal(r["actual_usd"]) for r in ledger["requests"]), Decimal(0))
    assert total == Decimal(ledger["known_usd"])
    assert total == sum((Decimal(v) for row in rows for v in row["cost_usd"].values()), Decimal(0))
    elapsed = (
        datetime.fromisoformat(ledger["requests"][-1]["finished_at"])
        - datetime.fromisoformat(ledger["requests"][0]["started_at"])
    ).total_seconds()
    print(
        json.dumps(
            {
                "verified": True,
                "archive_sha256": manifest["archive_sha256"],
                "archive_files": len(files),
                "single_field_diff": True,
                "model_facing_knowledge_equal_except_nonvisible_route": True,
                "same_input_replay": {
                    "control_article_characters": len(content),
                    "fault": replays[1]["exception"],
                },
                "cells": rows,
                "API_requests": 19,
                "agent_requests": 9,
                "judge_requests": 10,
                "known_usd": str(total),
                "unknown_cost_items": 0,
                "elapsed_seconds": elapsed,
                "ECS": None,
                "ECS_reason": "Late-only controlled diagnostic, not three-stage method comparison",
                "local_retrieval_damage": "confirmed controlled intervention",
                "whole_task_failure": "contradicted: both executions completed and supplied requested explanation/examples",
                "score_regression_causality": "suggestive only; single stochastic pair and judge discrepancies require separate review",
                "natural_method_over_update": "not demonstrated; normal guard rejects this artifact",
                "course_acceptance": "not presumed; unsent TA clarification retained",
                "new_verification_model_calls": 0,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

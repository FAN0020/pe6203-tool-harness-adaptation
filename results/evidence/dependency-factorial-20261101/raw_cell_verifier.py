"""Independent raw-cell verification copied from the prior audited reader; no pipeline imports."""

import hashlib
import json
import statistics
import tarfile
from collections import Counter
from decimal import Decimal


def sha(data):
    return hashlib.sha256(data).hexdigest()


def archive_files(folder):
    archive = folder / "raw-trial.tar.gz"
    manifest = json.loads((folder / "raw-manifest.json").read_text())
    assert sha(archive.read_bytes()) == manifest["archive_sha256"]
    with tarfile.open(archive) as tar:
        files = {m.name: tar.extractfile(m).read() for m in tar if m.isfile()}
    assert {k: sha(v) for k, v in files.items()} == manifest["files"]
    return (files, manifest)


def inspect_cell(files, prefix, cell, block, allow_incomplete=False, allow_unknown_cost=False):

    def read(name):
        return json.loads(files[prefix + name])

    plan = read("plan.json")
    base = f"cells/{cell['id']}/run/"
    r, t = (read(base + "result.json"), read(base + "raw_trace.json"))
    assert (r["task_id"], r["version"], r["strategy"]) == (
        cell["task_id"],
        cell["version"],
        cell["strategy"],
    )
    if allow_incomplete:
        assert r["judge_status"] == "incomplete" and r["status"] == "judge_incomplete"
        assert r["TF"] is None and r["PE"] is None
    else:
        assert r["judge_status"] == "complete" and r["status"] == "evaluated"
    assert r["ECS"] is None
    for k, v in plan["config"].items():
        assert r["config"][k] == v
    operational = {"root", "output_dir", "knowledge_path", "update_cost", "adaptation_path"}
    execution_protocol = {
        "settings": {k: v for k, v in r["config"].items() if k not in operational},
        "endpoints": r["model_endpoints"],
    }
    assert sha(json.dumps(execution_protocol, sort_keys=True).encode()) == r["protocol_sha256"]
    question = next(q["question"] for q in plan["tasks"] if q["idx"] == cell["task_id"])
    assert question == t["question"]
    initial = next(e["messages"] for e in t["events"] if e["type"] == "initial_messages")
    assert not any(
        arm in json.dumps(initial)
        for arm in (
            "document_sequence",
            "observed_contract",
            "budget_feedback",
            "selective_patch",
            "full_rewrite",
            "no_update",
        )
    )
    knowledge = f"adaptations/{cell['task_id']}-{cell['version']}-{cell['strategy']}/knowledge.json"
    assert read(base + "knowledge.json") == read(knowledge)
    if cell["task_id"] == 235:
        assert read(knowledge) == read("catalogs/235/early.json")
    responses = [e["response"] for e in t["events"] if e["type"] == "agent_response"]
    assert len(responses) <= 12
    last = responses[-1]["choices"][0]
    expected = (
        "output_truncated"
        if last["finish_reason"] == "length"
        else "max_rounds"
        if not t["stop"] and t["exceeded"]
        else "completed"
        if t["stop"]
        else "unknown"
    )
    assert r["execution_status"] == expected
    slots = read(base + f"EVAL/{cell['task_id']}.json")["eval_result"]["runs"]
    assert sorted(s["slot"] for s in slots) == [1, 2, 3, 4, 5]
    if allow_incomplete:
        by_slot = {s["slot"]: s for s in slots}
        assert sorted(s["slot"] for s in slots if "result" in s) == [1, 2]
        assert by_slot[3]["attempt"] == 1
        assert by_slot[3]["error"] == "BudgetStopped: model request failed"
        assert by_slot[3]["failure_category"] == "model_request"
        assert by_slot[3]["retryable"] is False
        assert by_slot[4] == {"slot": 4, "error": "not_attempted"}
        assert by_slot[5] == {"slot": 5, "error": "not_attempted"}
        outcome = read(base + "judge-attempts/slot-3-attempt-1/outcome.json")
        assert outcome["error"] == by_slot[3]["error"] and outcome["retryable"] is False
        assert prefix + base + "judge-attempts/slot-3-attempt-1/response.json" not in files
        slots = [s for s in slots if "result" in s]
    else:
        assert all("result" in s for s in slots)
    scores = []
    for slot in slots:
        attempt = base + f"judge-attempts/slot-{slot['slot']}-attempt-{slot['attempt']}/"
        response = read(attempt + "response.json")
        parsed = json.loads(response["choices"][0]["message"]["content"])
        assert parsed == slot["result"] == read(attempt + "outcome.json")["result"]
        request = read(attempt + "request.json")
        assert request["settings"] == {
            k: v for k, v in plan["config"]["judge"].items() if not k.endswith("_env")
        }
        scores.append({"TF": parsed["task_fulfillment"], "PE": parsed["planning_and_efficiency"]})
    judges = [
        json.loads(content)
        for name, content in files.items()
        if name.startswith(prefix + base + "judge-attempts/") and name.endswith("/response.json")
    ]
    means = {k: statistics.mean(s[k] for s in scores) for k in ("TF", "PE")}
    for k, value in means.items():
        if not allow_incomplete:
            assert abs(value - r[k]) < 1e-10
    costs, tokens, providers, ids = ({}, {}, {}, [])
    for role, values in [("agent", responses), ("judge", judges)]:
        cost = sum((Decimal(str(v["usage"]["cost"])) for v in values), Decimal(0))
        if (allow_incomplete or allow_unknown_cost) and role == "judge":
            assert r["cost"][role]["usd"] is None
            assert all(
                r["cost"][role][k] is None
                for k in ("prompt_tokens", "completion_tokens", "total_tokens")
            )
            assert abs(cost - Decimal(str(r["cost"][role]["known_usd"]))) < Decimal("1e-12")
        else:
            assert abs(cost - Decimal(str(r["cost"][role]["usd"]))) < Decimal("1e-12")
        costs[role] = str(cost)
        tokens[role] = {
            k: sum(v["usage"][k] for v in values)
            for k in ("prompt_tokens", "completion_tokens", "total_tokens")
        }
        providers[role] = dict(Counter(v.get("provider", "unknown") for v in values))
        for v in values:
            assert v["provider"] == "DigitalOcean" and v["model"] == plan["config"][role]["model"]
            ids.append(v["id"])
    if cell["strategy"] != "full_rewrite" or cell["version"] == "early":
        assert r["cost"]["update"]["calls"] == r["cost"]["update"]["usd"] == 0
    calls = [e for e in t["events"] if e["type"] == "tool_result"]
    row = {
        "cell_id": cell["id"],
        "block": block,
        "task_id": cell["task_id"],
        "stage": cell["version"],
        "strategy": cell["strategy"],
        "execution_status": expected,
        **({"TF": None, "PE": None} if allow_incomplete else means),
        "judge_slots_completed": len(scores),
        "official_judging_complete": not allow_incomplete,
        "judge_values": scores,
        "rounds": len(responses),
        "tool_calls": len(calls),
        "tool_errors": sum(bool(e["result"].get("isError")) for e in calls),
        "cost_usd": costs,
        "cost_complete": not (allow_incomplete or allow_unknown_cost),
        "tokens": tokens,
        "providers": providers,
        "seconds": r["seconds"],
        "update_seconds": r["cost"]["update"]["seconds"],
        "update": r["cost"]["update"],
        "evidence_member": prefix + base + "result.json",
        "protocol_sha256": r["protocol_sha256"],
    }
    return (row, ids)

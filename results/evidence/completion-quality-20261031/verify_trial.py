"""Offline-only verification of the approved 12-cell trial; no project imports.

Reads tar members without extraction. Original judge responses are parsed again;
semantic quality review is separate. Prints JSON and never changes source data.
"""

import hashlib
import json
import statistics
import sys
import tarfile
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    folder = Path(__file__).resolve().parent
    archive = Path(sys.argv[1]) if len(sys.argv) > 1 else folder / "raw-trial.tar.gz"
    manifest = json.loads((folder / "raw-manifest.json").read_text())
    assert sha(archive.read_bytes()) == manifest["archive_sha256"]
    with tarfile.open(archive) as tar:
        files = {m.name: tar.extractfile(m).read() for m in tar if m.isfile()}
    assert {k: sha(v) for k, v in files.items()} == manifest["files"]
    prefix = manifest["prefix"] + "/"

    def read(name):
        return json.loads(files[prefix + name])

    plan = read("plan.json")
    assert sha(files[prefix + "plan.json"]) == files[prefix + "plan.sha256"].decode().strip()
    assert len(plan["cells"]) == 12
    lock = read("knowledge-lock.json")
    assert lock["plan_sha256"] == sha(files[prefix + "plan.json"])
    for name, digest in lock["files"].items():
        assert sha(files[prefix + name]) == digest, name
    state = read("experiment.json")
    assert set(state["cells"]) == {c["id"] for c in plan["cells"]}
    for cell in state["cells"].values():
        assert cell["status"] == "evaluated"
        for name, digest in cell["files"].items():
            assert sha(files[prefix + name]) == digest, name

    rows, grouped, protocol_hashes = [], defaultdict(list), set()
    total_cost, response_ids = Decimal(0), set()
    for c in plan["cells"]:
        base = f"cells/{c['id']}/run/"
        r, t = read(base + "result.json"), read(base + "raw_trace.json")
        assert (r["task_id"], r["version"], r["strategy"]) == (
            c["task_id"],
            c["version"],
            c["strategy"],
        )
        assert r["status"] == "evaluated" and r["judge_status"] == "complete"
        assert r["ECS"] is None  # Two stages cannot establish three-stage ECS.
        for k, v in plan["config"].items():
            assert r["config"][k] == v, (c["id"], k)
        protocol_hashes.add(r["protocol_sha256"])
        question = next(q["question"] for q in plan["tasks"] if q["idx"] == c["task_id"])
        assert t["question"] == question
        knowledge = f"adaptations/{c['task_id']}-{c['version']}-{c['strategy']}/knowledge.json"
        assert read(base + "knowledge.json") == read(knowledge)
        if c["task_id"] == 235:
            assert read(knowledge) == read("catalogs/235/early.json")
        agent = [e["response"] for e in t["events"] if e["type"] == "agent_response"]
        assert len(agent) <= 12
        last = agent[-1]["choices"][0]
        expected = (
            "output_truncated"
            if last["finish_reason"] == "length"
            else "max_rounds"
            if not t["stop"] and t["exceeded"]
            else "completed"
            if t["stop"]
            else "unknown"
        )
        assert r["execution_status"] == expected, c["id"]
        slots = read(base + f"EVAL/{c['task_id']}.json")["eval_result"]["runs"]
        assert sorted(s["slot"] for s in slots) == [1, 2, 3, 4, 5]
        scores, judges = [], []
        for slot in slots:
            attempt = base + f"judge-attempts/slot-{slot['slot']}-attempt-{slot['attempt']}/"
            response = read(attempt + "response.json")
            parsed = json.loads(response["choices"][0]["message"]["content"])
            assert parsed == slot["result"] == read(attempt + "outcome.json")["result"]
            request = read(attempt + "request.json")
            settings = {k: v for k, v in plan["config"]["judge"].items() if not k.endswith("_env")}
            assert request["settings"] == settings
            scores.append(
                {"TF": parsed["task_fulfillment"], "PE": parsed["planning_and_efficiency"]}
            )
            judges.append(response)
        means = {k: statistics.mean(s[k] for s in scores) for k in ("TF", "PE")}
        for k, value in means.items():
            assert abs(value - r[k]) < 1e-10
        costs, tokens, providers = {}, {}, {}
        for role, responses in (("agent", agent), ("judge", judges)):
            cost = sum((Decimal(str(x["usage"]["cost"])) for x in responses), Decimal(0))
            assert abs(cost - Decimal(str(r["cost"][role]["usd"]))) < Decimal("1e-12")
            total_cost += cost
            costs[role] = str(cost)
            tokens[role] = {
                k: sum(x["usage"][k] for x in responses)
                for k in ("prompt_tokens", "completion_tokens", "total_tokens")
            }
            providers[role] = dict(Counter(x.get("provider", "unknown") for x in responses))
            for response in responses:
                assert response["model"] == plan["config"][role]["model"]
                assert response["id"] not in response_ids
                response_ids.add(response["id"])
        assert r["cost"]["update"]["calls"] == r["cost"]["update"]["usd"] == 0
        calls = [e for e in t["events"] if e["type"] == "tool_result"]
        row = {
            "cell_id": c["id"],
            "task_id": c["task_id"],
            "stage": c["version"],
            "strategy": c["strategy"],
            "execution_status": expected,
            **means,
            "judge_values": scores,
            "rounds": len(agent),
            "tool_calls": len(calls),
            "tool_errors": sum(bool(e["result"].get("isError")) for e in calls),
            "cost_usd": costs,
            "tokens": tokens,
            "providers": providers,
            "seconds": r["seconds"],
            "update_seconds": r["cost"]["update"]["seconds"],
        }
        rows.append(row)
        grouped[c["strategy"]].append(row)
    assert len(protocol_hashes) == 1
    ledger = read("spend-ledger.json")
    assert ledger["policy"]["limit_usd"] == "1.00"
    assert not ledger["blocked"] and Decimal(ledger["unknown_reserved_usd"]) == 0
    assert all(x["status"] == "settled" for x in ledger["requests"])
    spent = sum((Decimal(x["actual_usd"]) for x in ledger["requests"]), Decimal(0))
    assert spent == Decimal(ledger["known_usd"]) <= Decimal("1")
    preflights = [x for x in ledger["requests"] if x["max_completion_tokens"] == 32]
    assert len(preflights) == 2
    assert len(ledger["requests"]) == len(response_ids) + len(preflights)
    preflight_cost = sum((Decimal(x["actual_usd"]) for x in preflights), Decimal(0))
    assert abs(total_cost + preflight_cost - spent) < Decimal("1e-12")
    summary = {}
    for arm, cells in grouped.items():
        summary[arm] = {
            "cells": len(cells),
            "completed": sum(c["execution_status"] == "completed" for c in cells),
            "changed_completed": sum(
                c["task_id"] != 235 and c["execution_status"] == "completed" for c in cells
            ),
            "retention_completed": sum(
                c["task_id"] == 235 and c["execution_status"] == "completed" for c in cells
            ),
            "TF": statistics.mean(c["TF"] for c in cells),
            "PE": statistics.mean(c["PE"] for c in cells),
            "changed_TF": statistics.mean(c["TF"] for c in cells if c["task_id"] != 235),
            "changed_PE": statistics.mean(c["PE"] for c in cells if c["task_id"] != 235),
            "cost_usd": {
                role: str(sum((Decimal(c["cost_usd"][role]) for c in cells), Decimal(0)))
                for role in ("agent", "judge")
            },
            "update_seconds": sum(c["update_seconds"] for c in cells),
            "tokens": {
                role: {
                    k: sum(c["tokens"][role][k] for c in cells)
                    for k in ("prompt_tokens", "completion_tokens", "total_tokens")
                }
                for role in ("agent", "judge")
            },
            "seconds_sum": sum(c["seconds"] for c in cells),
        }
    requests = ledger["requests"]
    elapsed = (
        datetime.fromisoformat(requests[-1]["finished_at"])
        - datetime.fromisoformat(requests[0]["started_at"])
    ).total_seconds()
    print(
        json.dumps(
            {
                "verified": True,
                "raw_archive_sha256": manifest["archive_sha256"],
                "file_count": len(files),
                "cells": rows,
                "summary": summary,
                "judge_slots": sum(len(r["judge_values"]) for r in rows),
                "api_requests": len(requests),
                "known_total_usd": str(spent),
                "unknown_cost_items": 0,
                "preflight_usd": str(preflight_cost),
                "ledger_elapsed_seconds": elapsed,
                "new_verification_model_calls": 0,
                "ECS": None,
                "decision": "Semantic quality review required separately; no automatic promotion",
                "fairness_limit": "Same protocol/config; workspace paths differ and expose arm names. Provider routing is not pinned; see observed provider counts. Same K0 retention differences cannot establish an adaptation effect.",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

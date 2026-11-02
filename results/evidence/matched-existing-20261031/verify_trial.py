"""Offline independent recheck of nine new cells and three identified reused cells.

Reads immutable archive members only; no project imports, networks or model calls.
Original scores and execution completion are checked separately from semantic quality.
"""

import hashlib
import json
import statistics
import tarfile
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FOLDER = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def archive_files(folder):
    archive = folder / "raw-trial.tar.gz"
    manifest = json.loads((folder / "raw-manifest.json").read_text())
    assert sha(archive.read_bytes()) == manifest["archive_sha256"]
    with tarfile.open(archive) as tar:
        files = {m.name: tar.extractfile(m).read() for m in tar if m.isfile()}
    assert {k: sha(v) for k, v in files.items()} == manifest["files"]
    return files, manifest


def inspect_cell(files, prefix, cell, block):
    def read(name):
        return json.loads(files[prefix + name])

    plan = read("plan.json")
    base = f"cells/{cell['id']}/run/"
    r, t = read(base + "result.json"), read(base + "raw_trace.json")
    assert (r["task_id"], r["version"], r["strategy"]) == (
        cell["task_id"],
        cell["version"],
        cell["strategy"],
    )
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
    assert not any(arm in json.dumps(initial) for arm in ("budget_feedback", "selective_patch"))
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
        assert abs(value - r[k]) < 1e-10
    costs, tokens, providers, ids = {}, {}, {}, []
    for role, values in [("agent", responses), ("judge", judges)]:
        cost = sum((Decimal(str(v["usage"]["cost"])) for v in values), Decimal(0))
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
    assert r["cost"]["update"]["calls"] == r["cost"]["update"]["usd"] == 0
    calls = [e for e in t["events"] if e["type"] == "tool_result"]
    row = {
        "cell_id": cell["id"],
        "block": block,
        "task_id": cell["task_id"],
        "stage": cell["version"],
        "strategy": cell["strategy"],
        "execution_status": expected,
        **means,
        "judge_values": scores,
        "rounds": len(responses),
        "tool_calls": len(calls),
        "tool_errors": sum(bool(e["result"].get("isError")) for e in calls),
        "cost_usd": costs,
        "tokens": tokens,
        "providers": providers,
        "seconds": r["seconds"],
        "update_seconds": r["cost"]["update"]["seconds"],
        "evidence_member": prefix + base + "result.json",
        "protocol_sha256": r["protocol_sha256"],
    }
    return row, ids


def main():
    files, manifest = archive_files(FOLDER)
    prefix = manifest["prefix"] + "/"

    def read(n):
        return json.loads(files[prefix + n])

    plan = read("plan.json")
    assert sha(files[prefix + "plan.json"]) == files[prefix + "plan.sha256"].decode().strip()
    assert len(plan["cells"]) == 9 and "max_preflight_calls" not in plan
    lock = read("knowledge-lock.json")
    assert lock["plan_sha256"] == sha(files[prefix + "plan.json"])
    for name, digest in lock["files"].items():
        assert sha(files[prefix + name]) == digest
    state = read("experiment.json")
    assert set(state["cells"]) == {c["id"] for c in plan["cells"]}
    for cell in state["cells"].values():
        assert cell["status"] == "evaluated"
        for name, digest in cell["files"].items():
            assert sha(files[prefix + name]) == digest
    rows, ids = [], []
    for c in plan["cells"]:
        row, cell_ids = inspect_cell(files, prefix, c, "new_extension")
        rows.append(row)
        ids.extend(cell_ids)
    assert len(ids) == len(set(ids))
    ledger = read("spend-ledger.json")
    assert ledger["policy"]["limit_usd"] is None
    assert not ledger["blocked"] and Decimal(ledger["unknown_reserved_usd"]) == 0
    for r in ledger["requests"]:
        assert r["status"] == "settled" and r["actual_provider"] == "DigitalOcean"
        assert r["actual_model"] == ledger["policy"]["model"]
        assert (
            r["provider"] == ledger["policy"]["provider_route"] and "max_price" not in r["provider"]
        )
    spent = sum((Decimal(r["actual_usd"]) for r in ledger["requests"]), Decimal(0))
    assert spent == Decimal(ledger["known_usd"])
    preflights = [r for r in ledger["requests"] if r["max_completion_tokens"] == 32]
    assert len(preflights) == 2
    assert set(ids) == {r["response_id"] for r in ledger["requests"] if r not in preflights}
    pf_cost = sum((Decimal(r["actual_usd"]) for r in preflights), Decimal(0))
    assert abs(
        spent
        - pf_cost
        - sum(
            (Decimal(c["cost_usd"][role]) for c in rows for role in ("agent", "judge")), Decimal(0)
        )
    ) < Decimal("1e-12")
    old, old_manifest = archive_files(ROOT / "results/evidence/budget-contract-20261031")
    old_prefix = old_manifest["prefix"] + "/"
    old_plan = json.loads(old[old_prefix + "plan.json"])
    for role in ("agent", "judge"):
        settings = json.loads(json.dumps(old_plan["config"][role]))
        settings["extra_body"]["provider"].pop("max_price")
        assert settings == plan["config"][role]
    for key in plan["config"]:
        if key not in ("agent", "judge", "spend_guard"):
            assert plan["config"][key] == old_plan["config"][key]
    assert plan["tasks"] == old_plan["tasks"]
    assert plan["files"]["src/pe6203/judge.py"] == old_plan["files"]["src/pe6203/judge.py"]
    assert (
        plan["files"]["configs/benchmark.lock.json"]
        == old_plan["files"]["configs/benchmark.lock.json"]
    )
    for spec in plan["research"]["spec"]["reused_cells"]:
        assert spec["archive_sha256"] == old_manifest["archive_sha256"]
        cid = spec["member"].split("/cells/")[1].split("/")[0]
        c = next(c for c in old_plan["cells"] if c["id"] == cid)
        assert (c["task_id"], c["version"], c["strategy"]) == (
            spec["task_id"],
            spec["stage"],
            spec["strategy"],
        )
        row, _ = inspect_cell(old, old_prefix, c, "reused_prior_pilot")
        knowledge = json.loads(
            old[
                old_prefix
                + f"adaptations/{c['task_id']}-{c['version']}-{c['strategy']}/knowledge.json"
            ]
        )
        assert sha(json.dumps(knowledge, sort_keys=True).encode()) == spec["knowledge_sha256"]
        assert row["evidence_member"] == spec["member"]
        rows.append(row)
    assert len(rows) == 12
    expected = {
        (t, v, s)
        for t in (133, 235, 283)
        for v in ("middle", "late")
        for s in ("selective_patch", "budget_feedback")
    }
    assert {(r["task_id"], r["stage"], r["strategy"]) for r in rows} == expected
    protocol_hashes = {
        block: sorted({r["protocol_sha256"] for r in rows if r["block"] == block})
        for block in ("new_extension", "reused_prior_pilot")
    }
    assert all(len(values) == 1 for values in protocol_hashes.values())
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["strategy"]].append(row)
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
            "agent_and_judge_usd": str(
                sum(
                    (Decimal(c["cost_usd"][role]) for c in cells for role in ("agent", "judge")),
                    Decimal(0),
                )
            ),
            "update_seconds": sum(c["update_seconds"] for c in cells),
            "seconds_sum": sum(c["seconds"] for c in cells),
        }
    requests = ledger["requests"]
    elapsed = (
        datetime.fromisoformat(requests[-1]["finished_at"])
        - datetime.fromisoformat(requests[0]["started_at"])
    ).total_seconds()
    result = {
        "verified": True,
        "new_archive_sha256": manifest["archive_sha256"],
        "reused_archive_sha256": old_manifest["archive_sha256"],
        "new_file_count": len(files),
        "new_trajectories": 9,
        "reused_trajectories": 3,
        "new_judge_slots": 45,
        "combined_judge_slots": 60,
        "new_api_requests": len(requests),
        "new_known_usd": str(spent),
        "new_unknown_cost_items": 0,
        "new_preflight_usd": str(pf_cost),
        "new_elapsed_seconds": elapsed,
        "cells": rows,
        "summary": summary,
        "ECS": None,
        "verification_model_calls": 0,
        "execution_protocol_hashes": protocol_hashes,
        "protocol_hash_difference": "Full config hash includes ledger path and financial admission caps. These differ across blocks; judge implementation, rubric revision and scoring settings are unchanged apart from removal of max_price routing admission ceilings.",
        "limits": "Two blocks, one execution per exposed condition; removed financial admission ceilings in new block. No statistical or isolated causal claim. Semantic quality reviewed separately; no automatic promotion.",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

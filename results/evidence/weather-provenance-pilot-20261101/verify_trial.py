"""Offline raw-response, knowledge, cost and frozen-quality verification; no API calls."""
import json
import statistics
import tarfile
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from raw_cell_verifier import archive_files, inspect_cell, sha

FOLDER = Path(__file__).resolve().parent


def main():
    files, manifest = archive_files(FOLDER)
    prefix = manifest["prefix"] + "/"

    def read(name):
        return json.loads(files[prefix + name])

    plan = read("plan.json")
    assert sha(files[prefix + "plan.json"]) == files[prefix + "plan.sha256"].decode().strip()
    expected = {(task, stage, arm) for task, stage in [(26, "middle"), (26, "late"), (235, "late")]
                for arm in ("selective_patch", "weather_provenance")}
    assert {(c["task_id"], c["version"], c["strategy"]) for c in plan["cells"]} == expected
    assert len(plan["cells"]) == 6
    lock = read("knowledge-lock.json")
    assert lock["plan_sha256"] == sha(files[prefix + "plan.json"])
    for name, digest in lock["files"].items():
        assert sha(files[prefix + name]) == digest
    for task, stage in [(26, "middle"), (26, "late"), (235, "late")]:
        a, b = [read(f"adaptations/{task}-{stage}-{arm}/knowledge.json")
                for arm in ("selective_patch", "weather_provenance")]
        differences = []
        for left, right in zip(a["tools"], b["tools"], strict=True):
            assert {k: v for k, v in left.items() if k != "usage_rules"} == {
                k: v for k, v in right.items() if k != "usage_rules"}
            if left != right:
                assert right["usage_rules"][:-1] == left["usage_rules"]
                differences.append(left["tool_id"])
        assert set(differences) == ({"mcp-weather-demo::get-weather-advice", "mcp-weather-demo::get-forecast"} if task == 26 else set())
        if task == 235:
            assert a == b == read("catalogs/235/early.json")
    source_manifest = json.loads((FOLDER / "source-manifest.json").read_text())
    source_archive = FOLDER / "source-4e54a66.tar"
    assert sha(source_archive.read_bytes()) == source_manifest["archive_sha256"]
    with tarfile.open(source_archive) as tar:
        source = {m.name: tar.extractfile(m).read() for m in tar if m.isfile()}
    assert {k: sha(v) for k, v in source.items()} == source_manifest["files"]
    for name, digest in plan["files"].items():
        assert sha(source[name]) == digest
    prefreeze = json.loads((FOLDER / "pre-execution-freeze.json").read_text())
    for name, digest in prefreeze["files"].items():
        assert sha(source[name]) == digest
    spec = json.loads(source["experiments/weather-provenance-v1.json"])
    for stage in ("middle", "late"):
        base = read(f"adaptations/26-{stage}-selective_patch/knowledge.json")
        candidate = read(f"adaptations/26-{stage}-weather_provenance/knowledge.json")
        for tool in base["tools"]:
            if tool["tool_id"] in spec["mechanism"]["frozen_rules"]:
                tool["usage_rules"].append(spec["mechanism"]["frozen_rules"][tool["tool_id"]])
        assert base == candidate
    state = read("experiment.json")
    assert set(state["cells"]) == {c["id"] for c in plan["cells"]}
    for cell in state["cells"].values():
        assert cell["status"] == "evaluated"
        for name, digest in cell["files"].items():
            assert sha(files[prefix + name]) == digest
    mapping = json.loads((FOLDER / "blind-map.json").read_text())
    freeze = json.loads((FOLDER / "review-freeze.json").read_text())
    assert freeze["complete"] and freeze["review_count"] == 6
    reverse = {cell: review for review, cell in mapping.items()}
    rows, ids = [], []
    for cell in plan["cells"]:
        row, response_ids = inspect_cell(files, prefix, cell, "pilot")
        name = reverse[cell["id"]]
        review_path = FOLDER / "blind-reviews" / f"{name}.json"
        assert sha(review_path.read_bytes()) == freeze["review_sha256"][review_path.name]
        review = json.loads(review_path.read_text())
        packet_path = FOLDER / "blind-inputs" / f"{name}.json"
        assert sha(packet_path.read_bytes()) == review["input_sha256"]
        packet = json.loads(packet_path.read_text())
        for artifact in packet["artifacts"]:
            raw_path = prefix + f"cells/{cell['id']}/run/workspace/" + artifact["path"]
            assert sha(files[raw_path]) == artifact["sha256"]
        assert review["task_id"] == cell["task_id"]
        row.update(review_id=name, properties=review["properties"], core_pass=review["core_pass"])
        rows.append(row)
        ids.extend(response_ids)
    assert len(ids) == len(set(ids))
    assert len({row["protocol_sha256"] for row in rows}) == 1
    ledger = read("spend-ledger.json")
    assert ledger["policy"]["limit_usd"] is None and not ledger["blocked"]
    assert Decimal(ledger["unknown_reserved_usd"]) == 0
    for request in ledger["requests"]:
        assert request["status"] == "settled" and request["actual_provider"] == "DigitalOcean"
        assert request["actual_model"] == ledger["policy"]["model"]
        assert request["provider"] == ledger["policy"]["provider_route"]
    preflight = [r for r in ledger["requests"] if r["max_completion_tokens"] == 32]
    assert len(preflight) == 2
    assert set(ids) == {r["response_id"] for r in ledger["requests"] if r not in preflight}
    spent = sum((Decimal(r["actual_usd"]) for r in ledger["requests"]), Decimal(0))
    preflight_usd = sum((Decimal(r["actual_usd"]) for r in preflight), Decimal(0))
    assert spent == Decimal(ledger["known_usd"])
    assert abs(spent - preflight_usd - sum(
        (Decimal(r["cost_usd"][role]) for r in rows for role in ("agent", "judge")), Decimal(0)
    )) < Decimal("1e-12")
    summary = {}
    for arm in ("selective_patch", "weather_provenance"):
        group = [r for r in rows if r["strategy"] == arm]
        summary[arm] = {}
        for scope, subset in [("all", group), ("changed", [r for r in group if r["task_id"] == 26]),
                              ("retention", [r for r in group if r["task_id"] == 235])]:
            summary[arm][scope] = {
                "n": len(subset), "completed": sum(r["execution_status"] == "completed" for r in subset),
                "core_pass": sum(r["core_pass"] for r in subset),
                "TF": statistics.mean(r["TF"] for r in subset),
                "PE": statistics.mean(r["PE"] for r in subset),
            }
    weather = []
    for cell in plan["cells"]:
        if cell["task_id"] != 26:
            continue
        base = f"cells/{cell['id']}/run/"
        trace, result = read(base + "raw_trace.json"), read(base + "result.json")
        events = [event for event in trace["events"] if event["type"] == "tool_result"
                  and event["call"]["function"]["name"].startswith("get-forecast__")]
        assert len(events) == 1
        event = events[0]
        args = json.loads(event["call"]["function"]["arguments"])
        assert args["latitude"] == 34.05 and args["longitude"] == -118.24
        assert not event["result"].get("isError")
        text = "\n".join(c.get("text", "") for c in event["result"]["content"])
        assert text.startswith("Forecast for 34.05, -118.24:")
        body = text.split("\n\n", 1)[1]
        periods = [part.strip() for part in body.split("---") if part.strip()]
        assert len(periods) == args.get("periods", 14)
        assert all("Temperature:" in part and "Wind:" in part for part in periods)
        acquired = datetime.fromisoformat(result["started_at"]) + timedelta(
            seconds=event["elapsed_seconds"])
        weather.append({"cell_id": cell["id"], "stage": cell["version"],
                        "strategy": cell["strategy"], "returned_periods": len(periods),
                        "requested_periods": args.get("periods"), "periods": periods,
                        "acquired_utc_approx": acquired.isoformat(),
                        "text_sha256": sha(text.encode())})
    source_equivalent = True
    for left in weather:
        for right in weather:
            shared = min(len(left["periods"]), len(right["periods"]))
            source_equivalent &= left["periods"][:shared] == right["periods"][:shared]
    assert source_equivalent
    # Different requested period counts are agent choices; overlapping upstream data match.
    for row in weather:
        row.pop("periods")
    control, candidate = summary["selective_patch"], summary["weather_provenance"]
    a, b = control["changed"], candidate["changed"]
    gate = (b["completed"] >= a["completed"] and b["core_pass"] >= a["core_pass"]
            and (b["completed"] > a["completed"] or b["core_pass"] > a["core_pass"])
            and b["TF"] >= a["TF"] and all(
                candidate["retention"][k] >= control["retention"][k]
                for k in ("completed", "core_pass", "TF")))
    gate = gate and source_equivalent
    output = {
        "verified": True, "file_count": len(files), "source_files": len(source),
        "review_freeze_commit": "cc702c4", "rows": rows, "summary": summary,
        "pilot_gate": gate, "decision": "enter_validation" if gate else "reject_candidate",
        "api_requests": len(ledger["requests"]), "judge_slots": 30, "known_usd": str(spent),
        "preflight_usd": str(preflight_usd), "unknown_cost_items": 0,
        "elapsed_seconds": (datetime.fromisoformat(ledger["requests"][-1]["finished_at"])
                            - datetime.fromisoformat(ledger["requests"][0]["started_at"])).total_seconds(),
        "ECS": None, "verification_model_calls": 0,
        "plan_inputs_verified": len(plan["files"]),
        "extra_inputs_verified": len(prefreeze["files"]),
        "weather_source_equivalent_on_all_shared_periods": source_equivalent,
        "weather_observations": weather,
        "agent_requests": sum(r["rounds"] for r in rows),
        "judge_requests": sum(len(r["judge_values"]) for r in rows),
        "scope": "Six-cell development pilot, no population or causal claim from same-K0 retention noise.",
        "goal_complete": False,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

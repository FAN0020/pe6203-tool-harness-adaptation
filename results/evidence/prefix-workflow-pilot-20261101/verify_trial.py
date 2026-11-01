"""Offline raw-response, knowledge, cost and frozen-quality verification; no API calls."""
import json
import statistics
import tarfile
from datetime import datetime
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
    expected = {(task, stage, arm) for task, stage in [(457, "middle"), (457, "late"), (235, "late")]
                for arm in ("selective_patch", "prefix_workflow_memory")}
    assert {(c["task_id"], c["version"], c["strategy"]) for c in plan["cells"]} == expected
    assert len(plan["cells"]) == 6
    lock = read("knowledge-lock.json")
    assert lock["plan_sha256"] == sha(files[prefix + "plan.json"])
    for name, digest in lock["files"].items():
        assert sha(files[prefix + name]) == digest
    for task, stage in [(457, "middle"), (457, "late"), (235, "late")]:
        a, b = [read(f"adaptations/{task}-{stage}-{arm}/knowledge.json")
                for arm in ("selective_patch", "prefix_workflow_memory")]
        differences = []
        lefts, rights = [{t["tool_id"]: t for t in k["tools"]} for k in (a,b)]
        for identity in lefts:
            left,right=lefts[identity],rights[identity]
            assert {k:v for k,v in left.items() if k!="description"} == {k:v for k,v in right.items() if k!="description"}
            if left != right:
                assert right["description"].startswith(left["description"] + "\nVerified procedural memory:\n")
                program=json.loads(right["description"].split("\nVerified procedural memory:\n")[1])
                assert len(program["steps"])==7 and "repeat" in program["steps"][2]
                assert all(v not in json.dumps(program) for v in ["CANARY", "heldout", "PaLM", "772519"])
                differences.append(identity)
        assert set(differences) == ({"slidev-mcp::create_bulk_slides"} if task==457 else set())
        if task == 235:
            assert a == b == read("catalogs/235/early.json")
    source_manifest = json.loads((FOLDER / "source-packaging.json").read_text())
    source_archive = FOLDER / "pre-execution-source.tar.gz"
    assert sha(source_archive.read_bytes()) == source_manifest["archive_sha256"]
    with tarfile.open(source_archive) as tar:
        source = {m.name: tar.extractfile(m).read() for m in tar if m.isfile()}
    frozen = json.loads((FOLDER / "pre-execution-freeze.json").read_text())
    assert {k: sha(v) for k, v in source.items()} == frozen["files"]
    for name,wanted in plan["files"].items():
        assert sha(source[name])==wanted
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
    reconciliation = json.loads((FOLDER / "ledger-reconciliation.json").read_text())
    merged_bytes=(FOLDER / "shared-ledger-preserved.json").read_bytes()
    prior_bytes=(FOLDER / "prior-ledger-preserved.json").read_bytes()
    assert sha(merged_bytes)==reconciliation["merged_sha256"]
    assert sha(prior_bytes)==reconciliation["original_sha256"]
    merged,prior=json.loads(merged_bytes),json.loads(prior_bytes)
    assert merged["requests"][:len(prior["requests"])]==prior["requests"]
    ledger = json.loads((FOLDER / "trial-ledger-projection.json").read_text())
    assert ledger["requests"]==merged["requests"][len(prior["requests"]):]
    assert len(ledger["requests"])==reconciliation["new_requests"]
    assert ledger["policy"]==merged["policy"]==prior["policy"]

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
    for arm in ("selective_patch", "prefix_workflow_memory"):
        group = [r for r in rows if r["strategy"] == arm]
        summary[arm] = {}
        for scope, subset in [("all", group), ("changed", [r for r in group if r["task_id"] == 457]),
                              ("retention", [r for r in group if r["task_id"] == 235])]:
            summary[arm][scope] = {
                "n": len(subset), "completed": sum(r["execution_status"] == "completed" for r in subset),
                "core_pass": sum(r["core_pass"] for r in subset),
                "TF": statistics.mean(r["TF"] for r in subset),
                "PE": statistics.mean(r["PE"] for r in subset),
            }
    control, candidate = summary["selective_patch"], summary["prefix_workflow_memory"]
    a, b = control["changed"], candidate["changed"]
    gate = (b["completed"] > a["completed"] and b["core_pass"] > a["core_pass"]
            and b["TF"] >= a["TF"] and all(
                candidate["retention"][k] >= control["retention"][k]
                for k in ("completed", "core_pass", "TF")))
    output = {
        "verified": True, "file_count": len(files), "source_files": len(source),
        "review_freeze_commit": json.loads((FOLDER / "review-commit.json").read_text())["commit"], "rows": rows, "summary": summary,
        "pilot_gate": gate, "decision": "enter_validation" if gate else "reject_candidate",
        "api_requests": len(ledger["requests"]), "judge_slots": 30, "known_usd": str(spent),
        "preflight_usd": str(preflight_usd), "unknown_cost_items": 0,
        "elapsed_seconds": (datetime.fromisoformat(ledger["requests"][-1]["finished_at"])
                            - datetime.fromisoformat(ledger["requests"][0]["started_at"])).total_seconds(),
        "ECS": None, "verification_model_calls": 0,
        "scope": "Six-cell development pilot, no population or causal claim from same-K0 retention noise.",
        "goal_complete": False,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

"""Offline, read-only re-audit of registered candidates; never starts an experiment.

Reads planned cells, raw rating responses and a metadata-only projection of actor
records. It does not expose reasoning text or infer product correctness from TF.
Historical review decisions are imported with provenance, never overwritten.
"""
import ast
import csv
import hashlib
import json
import statistics
import subprocess
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/evidence/unified-reaudit-20261102"


def read(p, default=None):
    return json.loads(p.read_text()) if p.exists() else default


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def registry():
    # The requested 36 are the pre-request registry, not later additions.
    tree = ast.parse(subprocess.check_output(
        ["git", "show", "d6b60d2:src/pe6203/patch_variants.py"], cwd=ROOT, text=True))
    return next(ast.literal_eval(n.value) for n in tree.body
                if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and
                t.id == "VARIANTS" for t in n.targets))


def normalized_properties(review):
    p = review.get("properties", review.get("criteria", review.get("findings")))
    if isinstance(p, dict):
        return {k: (v if isinstance(v, str) else ("pass" if v else "fail")
                    if isinstance(v, bool) else v.get("status", "unknown"))
                for k, v in p.items()}
    if isinstance(p, list):
        # These two historical findings were explicitly reported as limitations,
        # not frozen task acceptance requirements. Preserve them in the source.
        optional = {"Rendered appearance", "Complete security verification"}
        values = {v.get("id", v.get("criterion", v.get("property", str(i)))):
                  v.get("status", "unknown") for i, v in enumerate(p)
                  if v.get("property") not in optional}
        return values or None
    return None


def review_index(folder):
    """Exact cohort directory only; cross-cohort evidence is not silently merged."""
    aliases = {
        "completion-quality-v1-20261031": "completion-quality-20261031",
        "paired-pilot-20261031": "budget-contract-20261031",
        "artifact-contract-pilot-ready-20261031": "artifact-contract-pilot-20261031",
        "artifact-contract-pilot-runtime-20261031": "artifact-contract-runtime-pilot-20261031",
        "semantic-claim-repair-pilot-20261101-exec": "semantic-claim-repair-20261101",
        "native-record-batch-pilot-20261101": "native-batch-knowledge-20261101",
        "dependency-factorial-v1": "dependency-factorial-20261101",
        "observation-selection-v1": "observation-selection-20261101",
    }
    evidence = ROOT / "results/evidence" / aliases.get(folder.name, folder.name)
    if not evidence.exists():
        stem = folder.name.replace("-pilot-", "-")
        if (ROOT / "results/evidence" / stem).exists():
            evidence = ROOT / "results/evidence" / stem
    if "extensions" in folder.parts:
        extension = folder.parent.name if folder.name == "development" else folder.name
        evidence = ROOT / "results/evidence" / aliases.get(extension, "extensions/" + extension)
    found = {}
    if folder.name == "paired-extension-20261031":
        p = ROOT / "results/evidence/matched-existing-20261031/quality-review.json"
        for row in read(p, {}).get("cells", []):
            member = row.get("evidence", {}).get("trajectory_member", "")
            if not member.startswith(folder.name + "/cells/"):
                continue
            props = normalized_properties(row)
            if props:
                found[row["cell_id"]] = {"properties": props,
                    "core_pass": all(v == "pass" for v in props.values()),
                    "review_source":str(p.relative_to(ROOT)), "review_source_sha256":sha(p)}
    for name in ["quality-review.json", "reviews.json", "decision.json", "decision-after-a2.json",
                 "validation-verification.json", "verification.json", "trial-verification.json"]:
        p = evidence / name
        d = read(p, {})
        if not isinstance(d, dict):
            continue
        rows = d.get("cells", d.get("rows", d.get("reviews", [])))
        if not isinstance(rows, list):
            continue
        for row in rows:
            rid = row.get("cell_id", row.get("id"))
            review = row.get("review", row)
            props = normalized_properties(review)
            if rid and props:
                found[rid] = {"properties": props, "core_pass": all(v == "pass" for v in props.values()),
                              "review_source": str(p.relative_to(ROOT)), "review_source_sha256": sha(p)}
    mapping_path = evidence / "blind-map.json"
    if not mapping_path.exists():
        mapping_path = evidence / "review-map.json"
    mapping = read(mapping_path, {})
    if isinstance(mapping, dict):
        for rid, cell in mapping.items():
            if not isinstance(cell, str):
                continue
            for base in ["blind-reviews", "blind-review"]:
                p = evidence / base / (rid + ".json")
                if not p.exists():
                    p = evidence / base / (rid + "-review.json")
                d = read(p, {})
                props = normalized_properties(d)
                if props:
                    found[cell] = {"properties": props, "core_pass": all(v == "pass" for v in props.values()),
                                   "review_source": str(p.relative_to(ROOT)), "review_source_sha256": sha(p)}
    # Some original extension reviews use cell IDs directly and have no map.
    # Read only the exact derived cohort evidence directory; preserve originals.
    if not mapping:
        for base in ["blind-review", "blind-reviews"]:
            for p in (evidence / base).glob("cell-*-review.json"):
                d = read(p)
                cell = d.get("cell", d.get("cell_id"))
                props = normalized_properties(d)
                if cell and p.name == cell + "-review.json" and props and cell not in found:
                    found[cell] = {"properties": props,
                                   "core_pass": all(v == "pass" for v in props.values()),
                                   "review_source": str(p.relative_to(ROOT)),
                                   "review_source_sha256": sha(p)}
    # New supplemental reviews remain separately sourced. Never replace an old
    # property decision or silently turn post-hoc review into blinded validation.
    supplemental_name = "registry-development" if folder == ROOT / "results/raw/extensions/magicui-log-dashboard-v1/development" else folder.name
    supplemental = OUT / "historical-products" / supplemental_name
    for p in (supplemental / "reviews").glob("*.json"):
        d = read(p)
        rid = d["cell_id"]
        packet = supplemental / (rid + ".json")
        trace = folder / "cells" / rid / "run/raw_trace.json"
        assert sha(packet) == d["input_sha256"] and sha(trace) == d["trace_sha256"]
        if rid not in found:
            props = normalized_properties(d)
            found[rid] = {"properties":props, "core_pass":all(v == "pass" for v in props.values()),
                          "review_source":str(p.relative_to(ROOT)), "review_source_sha256":sha(p),
                          "review_phase":"supplemental_posthoc_scores_exposed"}
    return found


def judge_scores(run, task_id, recorded):
    eval_record = read(run / "EVAL" / f"{task_id}.json", {})
    slots = eval_record.get("eval_result", {}).get("runs", [])
    scores = []
    errors = []
    if recorded.get("judge_status") == "complete" and sorted(s["slot"] for s in slots) != [1,2,3,4,5]:
        errors.append("five_slots_missing_or_duplicated")
    for slot in slots:
        base = run / "judge-attempts" / f"slot-{slot['slot']}-attempt-{slot['attempt']}"
        response = read(base / "response.json", {})
        try:
            value = json.loads(response["choices"][0]["message"]["content"])
            if value != slot["result"]:
                errors.append("raw_rating_differs_from_slot")
            scores.append((value["task_fulfillment"], value["planning_and_efficiency"]))
        except (KeyError, ValueError, IndexError, TypeError):
            errors.append("raw_rating_unreadable")
    means = {k: statistics.mean(v[i] for v in scores) if scores else None
             for i, k in enumerate(["TF", "PE"])}
    for k, v in means.items():
        if v is not None and (recorded.get(k) is None or abs(v-recorded[k]) > 1e-10):
            errors.append(k + "_mean_mismatch")
    return means, len(scores), errors


def inspect_cell(folder, plan, cell, reviews):
    run = folder / "cells" / cell["id"] / "run"
    result = read(run / "result.json", {})
    row = {"cohort": str(folder.relative_to(ROOT)), "cell_id": cell["id"],
           "task_id": cell["task_id"], "stage": cell["version"], "strategy": cell["strategy"],
           "repeat": cell.get("seed"), "status": result.get("status", "not_started"),
           "execution_status": result.get("execution_status", "not_started"),
           "core_pass": None, "properties": None, "review_source": None, "audit_errors": []}
    # Preparation-only plans can share cell IDs with a later executed cohort.
    # They must never inherit its product judgment.
    if result:
        row.update(reviews.get(cell["id"], {}))
    means, slots, errors = judge_scores(run, cell["task_id"], result)
    row.update(means, judge_slots=slots)
    row["audit_errors"].extend(errors)
    if not result:
        return row, []
    row["result_sha256"] = sha(run / "result.json")
    row["protocol_sha256"] = result.get("protocol_sha256")
    row["knowledge_sha256"] = result.get("knowledge_sha256")
    row["question_sha256"] = next((hashlib.sha256(t["question"].encode()).hexdigest()
           for t in plan["tasks"] if t["idx"] == cell["task_id"]), None)
    trace = read(run / "raw_trace.json", {})
    row["trace_present"] = bool(trace)
    row["question_matches_plan"] = trace.get("question") == next(
        (t["question"] for t in plan["tasks"] if t["idx"] == cell["task_id"]), None)
    row["environment_record_present"] = (run / "environment-metadata.json").exists()
    row["has_final_answer"] = bool((trace.get("answer") or "").strip())
    events = trace.get("events", [])
    responses = [e["response"] for e in events if e["type"] == "agent_response"]
    calls = [e for e in events if e["type"] == "tool_result"]
    row["rounds"] = len(responses)
    row["tool_calls"] = len(calls)
    row["tool_outer_errors"] = sum(bool(e["result"].get("isError")) for e in calls)
    row["tool_inner_errors"] = None  # Tool-specific contracts require directed analysis.
    row["transport_events"] = sum(e["type"] in ("request_retry", "agent_error") for e in events)
    row["finish_reason"] = responses[-1]["choices"][0]["finish_reason"] if responses else None
    row["actor_providers"] = dict(Counter(r.get("provider", "unknown") for r in responses))
    receipts = []
    for role, values in [("actor", responses), ("judge", [read(p) for p in sorted((run / "judge-attempts").glob("*/response.json"))])]:
        known = Decimal(0)
        missing = 0
        for v in values:
            amount = (v.get("usage") or {}).get("cost")
            if amount is None:
                missing += 1
            else:
                known += Decimal(str(amount))
            receipts.append({"id": v.get("id"), "role": role, "known_usd": str(amount) if amount is not None else None,
                             "cohort": row["cohort"], "cell_id": cell["id"]})
        row[role+"_known_usd"] = str(known)
        row[role+"_unpriced_responses"] = missing
    row["result_unknown_cost"] = result.get("cost", {}).get("usd") is None
    adaptation = folder / "adaptations" / f"{cell['task_id']}-{cell['version']}-{cell['strategy']}" / "knowledge.json"
    row["knowledge_matches_frozen_adaptation"] = ((run / "knowledge.json").exists() and adaptation.exists()
        and read(run / "knowledge.json") == read(adaptation))
    return row, receipts


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    names = registry()
    assert len(names) == 36 and len(set(names)) == 36
    rows, cohorts, receipts = [], [], []
    plans = sorted((ROOT / "results/raw").glob("*/plan.json"))
    plans += sorted((ROOT / "results/raw/extensions").glob("*/plan.json"))
    plans += sorted((ROOT / "results/raw/extensions").glob("*/development/plan.json"))
    for p in plans:
        plan = read(p)
        cells = plan.get("cells", [])
        if not any(c.get("strategy") in names for c in cells):
            continue
        folder = p.parent
        reviews = review_index(folder)
        lock = read(folder / "knowledge-lock.json", {})
        invalid_lock_files = [n for n, h in lock.get("files", {}).items()
                              if not (folder/n).exists() or sha(folder/n) != h]
        spec = plan.get("research", {}).get("spec", {})
        c = {"path": str(folder.relative_to(ROOT)), "plan_sha256": sha(p),
             "recorded_plan_hash_matches": (folder / "plan.sha256").exists() and
                 (folder/"plan.sha256").read_text().strip() == sha(p),
             "protocol": spec.get("id"), "created_at": plan.get("created_at"),
             "benchmark_commit": plan.get("benchmark_commit"), "dataset_revision": plan.get("dataset_revision"),
             "scientific_phase": spec.get("evaluation_stage", plan.get("research", {}).get("phase")),
             "planned": len(cells), "knowledge_lock_exists": bool(lock), "invalid_lock_files": invalid_lock_files,
             "config": plan.get("config"), "fixture_spec": {k: v for k, v in spec.items() if "fixture" in k or "input" in k},
             "tasks": [{"id": t["idx"], "question_sha256": hashlib.sha256(t["question"].encode()).hexdigest(),
                        "text":t["question"], "servers": t.get("servers")} for t in plan.get("tasks", [])],
             "source_hashes": plan.get("files", {})}
        cohorts.append(c)
        for cell in cells:
            row, rs = inspect_cell(folder, plan, cell, reviews)
            row["protocol"] = c["protocol"]
            row["condition_class"] = ("controlled_synthetic_extension" if row["task_id"] >= 900000
                 else "original_with_fixed_fixture" if row["task_id"] in (457,) else "original_benchmark")
            if row["task_id"] == 377:
                row["condition_class"] = "original_missing_input_ineligible"
            rows.append(row)
            receipts += rs
    groups = defaultdict(list)
    for row in rows:
        key = (row["cohort"], row["task_id"], row["stage"], row["strategy"])
        groups[key].append(row)
    summary = []
    for (cohort, task, stage, method), values in groups.items():
        executed = [v for v in values if v["status"] != "not_started"]
        reviewed = [v for v in executed if v["core_pass"] is not None]
        d = {"cohort":cohort, "task_id":task, "stage":stage, "strategy":method,
             "planned":len(values), "executed":len(executed),
             "completed":sum(v["execution_status"] == "completed" for v in executed),
             "product_reviewed":len(reviewed), "core_pass":sum(v["core_pass"] for v in reviewed),
             "unreviewed_products":len(executed)-len(reviewed),
             "condition_class":values[0]["condition_class"],
             "valid_rating_slots":sum(v["judge_slots"] for v in values),
             "tool_calls":sum(v.get("tool_calls", 0) for v in values),
             "tool_outer_errors":sum(v.get("tool_outer_errors", 0) for v in values),
             "transport_events":sum(v.get("transport_events", 0) for v in values),
             "actor_judge_known_usd":str(sum((Decimal(v.get(k,"0")) for v in values
                 for k in ("actor_known_usd", "judge_known_usd")), Decimal(0))),
             "unknown_cost_cells":sum(v.get("result_unknown_cost",False) for v in values)}
        for metric in ["TF", "PE"]:
            scored = [v[metric] for v in executed if v[metric] is not None]
            d[metric] = statistics.mean(scored) if scored and len(scored)==len(values) else None
            d[metric+"_available_mean"] = statistics.mean(scored) if scored else None
            d[metric+"_n"] = len(scored)
        summary.append(d)
    inventory = []
    for method in names:
        selected = [r for r in rows if r["strategy"] == method]
        executed = [r for r in selected if r["status"] != "not_started"]
        by_class = {c:sum(r["condition_class"] == c for r in executed) for c in
                    sorted({r["condition_class"] for r in executed})}
        inventory.append({"candidate":method, "cohorts":sorted({r["cohort"] for r in selected}),
            "protocols":sorted({r["protocol"] for r in selected if r["protocol"]}),
            "executed_cells":len(executed), "evaluated_cells":sum(r["judge_slots"] == 5 for r in executed),
            "products_reviewed":sum(r["core_pass"] is not None for r in executed),
            "condition_classes":by_class, "evidence_level": "actor_and_official_scoring" if executed else "pre_actor_only_needs_directed_review"})
    def write(name, data):
        (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
    write("cohorts.json", cohorts)
    write("cells.json", rows)
    write("condition-comparison.json",summary)
    write("candidate-inventory.json",inventory)
    write("response-receipts.json",receipts)
    with (OUT/"condition-comparison.csv").open("w") as f:
        writer=csv.DictWriter(f,fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    audit={"registered_candidates":len(names),"cohorts":len(cohorts),"planned_cells":len(rows),
           "executed_cells":sum(r["status"]!="not_started" for r in rows),"judge_slots":sum(r["judge_slots"] for r in rows),
           "reviewed_products":sum(r["core_pass"] is not None for r in rows),
           "raw_score_errors":[{k:r[k] for k in ["cohort","cell_id","audit_errors"]} for r in rows if r["audit_errors"]],
           "invalid_knowledge_locks":[c["path"] for c in cohorts if c["invalid_lock_files"]],
           "limits":["Imported review judgments are not independent re-judgments; unknown does not pass.",
                     "No complete-cohort metric is imputed from available cases.",
                     "No cross-task ranking. Actor/judge receipt costs exclude shared updater/preflight costs pending global accounting.",
                     "Outer tool error flags do not capture inner semantic failure; task-specific audit remains necessary.",
                     "Top5 provenance supplied by user; fifth item explicitly names shared_contract_refs but leaves its other recent members unspecified.",
                     "No new model, benchmark, judge or MCP calls."]}
    write("audit.json",audit)
    print(json.dumps(audit,ensure_ascii=False))


if __name__ == "__main__":
    main()

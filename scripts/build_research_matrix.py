"""Versioned maturity and failure-evidence matrices; no model calls or ranking."""

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / "results/evidence/unified-reaudit-20261102"


def main():
    def read(n):
        return json.loads((E / n).read_text())
    inventory, rows, cohorts = (
        read("candidate-inventory.json"),
        read("cells.json"),
        read("cohorts.json"),
    )
    phases = {c["path"]: c["scientific_phase"] for c in cohorts}
    maturity = []
    for item in inventory:
        own = [
            r for r in rows if r["strategy"] == item["candidate"] and r["status"] != "not_started"
        ]
        assert len(own) == item["products_reviewed"] == item["executed_cells"]
        observed = Counter(phases[r["cohort"]] or "phase_unspecified" for r in own)
        changed_original = sum(
            r["condition_class"] == "original_benchmark" and r["task_id"] != 235 for r in own
        )
        if not own:
            layer = "generation/admission only; no actor result"
        elif observed["independent_validation"]:
            layer = "independent execution blocks run; joint gates failed"
        elif not changed_original and item["condition_classes"].get("original_with_fixed_fixture", 0):
            layer = "original with fixed fixture development/products; retention separate"
        elif not changed_original and item["condition_classes"].get("controlled_synthetic_extension", 0):
            layer = "synthetic execution/products plus original retention only"
        elif not changed_original:
            layer = "original retention-only execution; no changed-task evidence"
        elif observed["confirmation"]:
            layer = "historical research confirmation; not current independent Goal validation"
        else:
            layer = "original development with product review"
        maturity.append(
            dict(
                candidate=item["candidate"],
                layer=layer,
                executed=len(own),
                five_slot_scored=item["evaluated_cells"],
                products_reviewed=len(own),
                changed_original=changed_original,
                original_fixed_fixture=item["condition_classes"].get(
                    "original_with_fixed_fixture", 0
                ),
                controlled_synthetic=item["condition_classes"].get(
                    "controlled_synthetic_extension", 0
                ),
                phases=dict(observed),
                protocols=item["protocols"],
                cohorts=item["cohorts"],
                goal_validated=False,
                review_limit="Historical supplemental judgments are posthoc/exposed; original blind judgments reused where available.",
            )
        )
    (E / "candidate-maturity.json").write_text(
        json.dumps(maturity, ensure_ascii=False, indent=2) + "\n"
    )
    with (E / "candidate-maturity.csv").open("w") as f:
        w = csv.DictWriter(f, fieldnames=list(maturity[0]))
        w.writeheader()
        w.writerows(maturity)
    condition = read("condition-comparison.json")
    baseline = {
        (r["cohort"], r["task_id"], r["stage"]): r
        for r in condition
        if r["strategy"] == "selective_patch"
    }
    paired = []
    registry = {r["candidate"] for r in inventory}
    for candidate in condition:
        if (
            candidate["strategy"] not in registry
            or not candidate["executed"]
            or candidate["task_id"] == 377
        ):
            continue
        key = (candidate["cohort"], candidate["task_id"], candidate["stage"])
        sp = baseline.get(key)
        if not sp or not sp["executed"]:
            continue
        members = [
            r
            for r in rows
            if (r["cohort"], r["task_id"], r["stage"]) == key
            and r["strategy"] in ["selective_patch", candidate["strategy"]]
            and r["status"] != "not_started"
        ]
        providers = sorted({provider for r in members for provider in r.get("actor_providers", [])})
        pair = {
            "cohort": key[0],
            "task_id": key[1],
            "stage": key[2],
            "candidate": candidate["strategy"],
            "condition_class": candidate["condition_class"],
            "actual_actor_providers": providers,
            "knowledge_attribution": "retention; identical knowledge, variability only"
            if key[1] == 235
            else "within-cohort paired observations; small/exposed samples, not causal proof",
            "provider_limit": "multiple actual providers; cannot pool with pinned provider experiments"
            if len(providers) > 1
            else "single actual provider within this pair",
        }
        for label, r in [("SP", sp), ("candidate", candidate)]:
            for name in [
                "executed",
                "planned",
                "completed",
                "core_pass",
                "product_reviewed",
                "valid_rating_slots",
                "TF",
                "PE",
                "tool_outer_errors",
                "tool_calls",
                "transport_events",
                "actor_judge_known_usd",
                "unknown_cost_cells",
            ]:
                pair[label + "_" + name] = r[name]
        paired.append(pair)
    (E / "pairwise-comparison.json").write_text(
        json.dumps(paired, ensure_ascii=False, indent=2) + "\n"
    )
    with (E / "pairwise-comparison.csv").open("w") as f:
        w = csv.DictWriter(f, fieldnames=list(paired[0]))
        w.writeheader()
        w.writerows(paired)
    # Group by exact cohort/task, never pool them into a ranking or causal estimate.
    grouped = defaultdict(list)
    for r in rows:
        if r["task_id"] in (133, 283, 235) and r["status"] != "not_started":
            grouped[(r["cohort"], r["task_id"])].append(r)
    facts = []
    for (cohort, task), items in grouped.items():
        reviewed = [r for r in items if r["core_pass"] is not None]
        facts.append(
            {
                "cohort": cohort,
                "task_id": task,
                "n": len(items),
                "arms": dict(Counter(r["strategy"] for r in items)),
                "execution_status": dict(Counter(r["execution_status"] for r in items)),
                "empty_final": sum(not r.get("has_final_answer", False) for r in items),
                "reviewed": len(reviewed),
                "core_fail": sum(not r["core_pass"] for r in reviewed),
                "high_TF_but_core_fail": sum(
                    not r["core_pass"] and r.get("TF") is not None and r["TF"] >= 9
                    for r in reviewed
                ),
                "outer_tool_errors": sum(r.get("tool_outer_errors", 0) for r in items),
                "transport_events": sum(r.get("transport_events", 0) for r in items),
            }
        )
    (E / "failure-counts-by-cohort-task.json").write_text(
        json.dumps(facts, ensure_ascii=False, indent=2) + "\n"
    )
    categories = [
        {
            "category": "knowledge adaptation",
            "direct_facts": [
                "Source/native evidence establishes ignored optional parameters, parser-specific rather than Python semantics, lossy task reads and native faulty examples. Successful tool receipt does not certify generated code."
            ],
            "observations": [
                "Some notes reduce invalid/redundant calls or improve PE, but exact paired product gates remain negative."
            ],
            "hypotheses": [
                "Whether a richer structured contract or replay-selected memory changes final reasoning remains testable; one failed version does not reject the class."
            ],
            "sources": [
                "../semantic-contract-maintenance-20261101/review-decision.json",
                "../relational-probe-memory-20261102/research-decision.json",
                "swift-static-checks/",
            ],
        },
        {
            "category": "execution and budget",
            "direct_facts": [
                "finish_reason=length records truncation; max_rounds with exceeded records exhaustion. Empty final text is separately audited."
            ],
            "observations": [
                "283 recurrent empty delivery can coexist with valid substantial task graphs. New relationalMiddle38vs82calls still12rounds/emptyfinal."
            ],
            "hypotheses": [
                "Planning expansion, token use per turn, evidence utilization or redundant work may explain exhaustion; stop fields alone do not identify the cause."
            ],
            "sources": [
                "failure-counts-by-cohort-task.json",
                "../relational-probe-memory-20261102/trial-verification.json",
            ],
        },
        {
            "category": "artifact generation",
            "direct_facts": [
                "Static code checks locate arithmetic/resource-control contradictions; Swift compiler distinguishes copied native bad code from actor-introduced List.onDelete error. Persisted task IDs/edges and final claims are checked separately."
            ],
            "observations": [
                "High official TF often coexists with required-property failure; this is a rubric/product mismatch, not proof the official protocol was executed incorrectly."
            ],
            "hypotheses": [
                "General code-generation or factual-summary capability may dominate when tool contracts are already correct."
            ],
            "sources": [
                "historical-products/",
                "swift-static-checks/",
                "failure-counts-by-cohort-task.json",
            ],
        },
        {
            "category": "environment and data",
            "direct_facts": [
                "377 lacks required original input and is excluded; no further search.457 conditions distinguish missing PDFs, fixed PDFs and shared render-runtime readiness. Original archives hash-match.",
                "Native review_project_status/workspace health source calls missing getTasksByProject in nonempty workspace; native implementation not changed to aid candidate.",
            ],
            "observations": [
                "Catalog identity cannot prove every old process startup or historical executable byte. Some earlier runs mix providers."
            ],
            "hypotheses": [
                "Environment/fixture effects cannot be conflated with knowledge effects across different cohorts."
            ],
            "sources": [
                "comparability.json",
                "../active-contract-probing-20261101/",
                "../relational-probe-memory-20261102/preparation-deviation.json",
            ],
        },
        {
            "category": "evaluation uncertainty",
            "direct_facts": [
                "All2555available slots recomputed; zero score/hash mismatches. Historical supplemental product reviews are exposed. Relationalv1 last2reviews followed accidental aggregate-score exposure."
            ],
            "observations": [
                "SameK retention/math differences show run variation; small development counts are gates, not causal confidence intervals."
            ],
            "hypotheses": [
                "Two frozen fresh execution blocks are necessary for the requested reproducibility claim; neither development nor posthoc review supplies that evidence."
            ],
            "sources": [
                "audit.json",
                "audit-corrections.json",
                "../relational-probe-memory-20261102/blinding-deviation.json",
            ],
        },
    ]
    # The referenced relational preparation deviation does not exist; current preparation error is pruned only.
    categories[3]["sources"][-1] = "../pruned-episode-memory-20261102/preparation-deviation.json"
    priorities = [
        {
            "rank": 1,
            "bottleneck": "Project final delivery and bounded required work",
            "basis": "Recurring original283 empty finals acrossmultiplecohorts; actualpersistedgraph/directstop evidence; affects entire required delivery. Native writes/reads andknowledge can be intervened on, but the root cause is unresolved.",
            "action": "State-linked evidence v1 and replay-pruning v2 both failed strict development; finite native state equivalence did not transfer to final delivery.",
        },
        {
            "rank": 2,
            "bottleneck": "Math guidance/code consistency and false inference from native checks",
            "basis": "Repeated133core failures, including old108mathSP/SF0/9 each. Direct staticcounterexamples; intervention reach limited because generatedPython is not the native parser.",
            "action": "Losslessdictionary/contrastive andcapabilityconsolidation alreadytestednegative; no claim wholemethodspaceinvalid.",
        },
        {
            "rank": 3,
            "bottleneck": "Numerical final summaries on unchanged charts",
            "basis": "Exactinput/spec comparison finds wrongannuals/dips/gaps despite chart success. Directfailurebut235knowledgeunchanged.",
            "action": "Retention guard/control only; cannot claim selectiveknowledgegain or patchunrelatedknowledge to chase this metric.",
        },
    ]
    (E / "failure-matrix.json").write_text(
        json.dumps(
            {
                "categories": categories,
                "priorities": priorities,
                "limits": "Frequency counts are stratified by cohort/task, include correlated methods/repeats, and are descriptive only. Priority also considers evidence strength, final-product impact and legal intervention reach.",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    print(
        json.dumps(
            {
                "candidates": len(maturity),
                "candidate_product_gaps": 0,
                "cohort_task_groups": len(facts),
                "categories": 5,
                "priority_bottlenecks": 3,
            }
        )
    )


if __name__ == "__main__":
    main()

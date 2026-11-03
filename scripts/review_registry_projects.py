"""Historical persisted project review; keep missing fields and judgments explicit."""

import hashlib
import json
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "results/evidence/unified-reaudit-20261102/historical-products"
G = runpy.run_path(
    str(ROOT / "results/evidence/capability-consolidation-20261102/product_graph.py")
)["graph_facts"]
COHORTS = [
    "selective-search-v1.1-development-20261031",
    "selective-search-v2.1-development-20261031",
]
DELIVERY = {
    ("selective-search-v1.1-development-20261031", "task283-late-linked_notes-r0"): (
        "fail",
        "Claims all<=5 in a24task complexity assessment, but3milestone records remain6.24total/20leaves/0flagged>=7 and analyzer4.7 correct. Leafhours174 versus approximately180 acceptable; no dependencies claimed persisted.",
    ),
    ("selective-search-v1.1-development-20261031", "task283-late-feedback_notes-r0"): (
        "pass",
        "37total,6milestones,31leaves,204leafhours match; allleafcomplexities2–4 and6–8h; analyzer3.5 andremainingM6heuristic6 disclosed. Required work preserved under real children.",
    ),
    ("selective-search-v1.1-development-20261031", "task283-middle-feedback_notes-r0"): (
        "pass",
        "37total,5milestones,32leaves; rootestimates24+60+52+64+44=244 match table. Leaves sum248, consistent with approximate244; not claiming exactchildsum. Leaves2–5 and4–10h; analyzer4.4 and4flaggedmilestones disclosed.8dependencies include2claimedcrosslinks.",
    ),
}


def main():
    count = 0
    for co in COHORTS:
        for f in sorted((P / co).glob("task283-*.json")):
            if (f.parent / "reviews" / f.name).exists():
                continue
            d = json.loads(f.read_text())
            props = dict.fromkeys(
                ["coverage", "structure_and_scope", "delivery_truth", "scope_preserved"], "unknown"
            )
            evidence = {}
            facts = None
            mutations = []
            if d["artifacts"]:
                artifact = d["artifacts"][0]
                raw = (
                    ROOT / d["cohort"] / "cells" / d["cell_id"] / "run/workspace" / artifact["path"]
                )
                assert hashlib.sha256(raw.read_bytes()).hexdigest() == artifact["sha256"]
                s = json.loads(raw.read_text())
                facts = G(s)
                parents = {t.get("parentId") for t in s["tasks"]}
                assert all(
                    t["id"] and any(x["id"] == t["projectId"] for x in s["projects"])
                    for t in s["tasks"]
                )
                assert not any(
                    facts[k]
                    for k in [
                        "duplicate_ids",
                        "dangling_parents",
                        "dangling_dependencies",
                        "parent_cycle",
                    ]
                )
                props.update(coverage="pass", structure_and_scope="pass", scope_preserved="pass")
                evidence.update(
                    coverage="Saved tasks cover CSV processing, log analysis and visualization; domain names and concrete work descriptions reviewed.",
                    structure_and_scope="Unique linked records and valid parent graph; substantive executable decomposition distinguished from milestone containers. No arbitrary numeric effort cutoff.",
                    scope_preserved="Required work retained; parent estimates after real child decomposition are not treated as scope hiding.",
                )
                for c in d["calls"]:
                    if c["tool"].startswith(("update_task", "delete_task")):
                        a = json.loads(c["arguments"])
                        a.pop("workingDirectory", None)
                        if set(a) <= {"id", "dependsOn"}:
                            continue
                        entry = {"tool": c["tool"], "args": a, "has_children": a["id"] in parents}
                        created = [
                            x
                            for x in d["calls"]
                            if x["tool"].startswith("create_task")
                            and a["id"] in json.dumps(x["result"])
                        ]
                        if created:
                            entry["initial_arguments"] = json.loads(created[0]["arguments"])
                            entry["initial_arguments"].pop("workingDirectory", None)
                        mutations.append(entry)
                if facts["dependency_field_missing"]:
                    props["structure_and_scope"] = "unknown"
                    evidence["structure_and_scope"] = (
                        "Early persisted leaf records omit dependsOn; do not infer no dependencies or certify complete graph from absent fields. Parent graph is valid and domains decomposed."
                    )
            else:
                evidence["artifact"] = (
                    "No persisted task artifact available after failed execution; required properties unknown."
                )
            if d["answer"]:
                assert (co, f.stem) in DELIVERY
                props["delivery_truth"], evidence["delivery_truth"] = DELIVERY[(co, f.stem)]
            else:
                evidence["delivery_truth"] = (
                    "No final answer; persisted partial work cannot establish completed delivery."
                )
            r = {
                "cell_id": f.stem,
                "task_id": 283,
                "input_sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
                "trace_sha256": d["trace_sha256"],
                "properties": props,
                "core_pass": all(v == "pass" for v in props.values()),
                "evidence": evidence,
                "graph_facts": facts,
                "scope_relevant_mutations": mutations,
                "review_phase": "supplemental_posthoc_scores_exposed",
                "review_source": "scripts/review_registry_projects.py",
                "limitations": [
                    "Same coordinator; prior scores exposed, not independent validation.",
                    "Qualitative scope is not measured implementation effort.",
                    "Analyzer heuristics and stored complexity fields are different quantities.",
                    "Missing dependency fields remain unknown, not zero.",
                ],
            }
            (f.parent / "reviews" / f.name).write_text(
                json.dumps(r, ensure_ascii=False, indent=2) + "\n"
            )
            count += 1
    print(count, "supplemental project reviews")


if __name__ == "__main__":
    main()

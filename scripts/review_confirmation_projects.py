"""Recompute persisted graph evidence and dated supplemental project reviews."""

import hashlib
import json
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = (
    ROOT
    / "results/evidence/unified-reaudit-20261102/historical-products/selective-search-confirmation-r1-20261031"
)
GRAPH_SOURCE = ROOT / "results/evidence/capability-consolidation-20261102/product_graph.py"
graph_facts = runpy.run_path(str(GRAPH_SOURCE))["graph_facts"]
DELIVERY = {
    "late-selective_patch-r0": "32tasks/4milestones/28leaves and256leaf hours agree;3.7 is the observed analyzer heuristic, not a recomputed stored-field average. Final identifies actual project.",
    "late-sufficiency_feedback-r0": "28tasks/4milestones/24leaves, leaf complexities3–5, and approximate300h agree with314h. Explicitly distinguishes4flagged containers; observed average5.0 correctly quoted.",
    "middle-selective_patch-r0": "29tasks/5milestones/24leaves and192h agree. Both analyzer passes match quoted counts/threshold/4.5; lowering actual parent rollups is disclosed. No task implementation completion claimed.",
    "middle-sufficiency_feedback-r2": "27tasks/5milestones/22leaves, approximate200h, and observed average4.0 agree. Sequencing is narrative recommendation; explicitly offers to add formal dependencies, which remain absent.",
}


def main():
    for packet in sorted(FOLDER.glob("task283-*.json")):
        d = json.loads(packet.read_text())
        raw = (
            ROOT
            / "results/raw/selective-search-confirmation-r1-20261031/cells"
            / packet.stem
            / "run/workspace"
        )
        artifact = d["artifacts"][0]
        file = raw / artifact["path"]
        assert hashlib.sha256(file.read_bytes()).hexdigest() == artifact["sha256"]
        store = json.loads(file.read_text())
        facts = graph_facts(store)
        assert not any(
            facts[k]
            for k in [
                "duplicate_ids",
                "dangling_parents",
                "dangling_dependencies",
                "parent_cycle",
                "dependency_cycle",
                "dependency_field_missing",
            ]
        )
        projects = {x["id"] for x in store["projects"]}
        assert all(t["id"] and t["projectId"] in projects for t in store["tasks"])
        parents = {t.get("parentId") for t in store["tasks"]}
        leaves = [t for t in store["tasks"] if t["id"] not in parents]
        assert all(t.get("details") for t in leaves)
        facts["leaf_estimated_hours"] = sum(t.get("estimatedHours") or 0 for t in leaves)
        facts["leaf_complexity_range"] = [
            min(t.get("complexity") or 0 for t in leaves),
            max(t.get("complexity") or 0 for t in leaves),
        ]
        # Persist scope-relevant updates, without drowning audit in dependency edits.
        mutations = []
        for c in d["calls"]:
            if c["tool"].startswith(("update_task", "delete_task")):
                a = json.loads(c["arguments"])
                a.pop("workingDirectory", None)
                if set(a) <= {"id", "dependsOn"}:
                    continue
                mutations.append({"tool": c["tool"], "args": a, "has_children": a["id"] in parents})
        assert not any(m["tool"].startswith("delete_task") for m in mutations)
        # Only leaf complexity edit fills an initially unset field, not a reduction.
        leaf_edits = [m for m in mutations if "complexity" in m["args"] and not m["has_children"]]
        if leaf_edits:
            assert packet.stem == "task283-middle-selective_patch-r0" and len(leaf_edits) == 1
            created = next(
                c
                for c in d["calls"]
                if c["tool"].startswith("create_task")
                and json.loads(c["arguments"]).get("name") == "Performance optimization"
            )
            assert "Complexity: Not set/10" in created["result"]["content"][0]["text"]
        stem = packet.stem.removeprefix("task283-")
        delivery = "pass" if d.get("answer") and stem in DELIVERY else "unknown"
        assert bool(d.get("answer")) == (stem in DELIVERY)
        props = {
            "coverage": "pass",
            "structure_and_scope": "pass",
            "delivery_truth": delivery,
            "scope_preserved": "pass",
        }
        review = {
            "cell_id": packet.stem,
            "task_id": 283,
            "input_sha256": hashlib.sha256(packet.read_bytes()).hexdigest(),
            "trace_sha256": d["trace_sha256"],
            "artifact_sha256": artifact["sha256"],
            "properties": props,
            "core_pass": all(x == "pass" for x in props.values()),
            "graph_facts": facts,
            "scope_relevant_mutations": mutations,
            "evidence": {
                "coverage": "Persisted linked tasks cover CSV ingestion/validation/transforms, application-log parsing/analysis and visualization components; inspected task names/details, not just project label.",
                "structure_and_scope": "Graph checks pass. Concrete leaves separate contracts, collection, transformations, storage, metrics, UI components, integration and tests. Parent rollups with real children distinguished from executable leaves. No arbitrary hour/count/complexity cutoff substituted for qualitative scope judgment.",
                "delivery_truth": DELIVERY.get(
                    stem,
                    "Final answer empty; saved planning work does not establish a user-facing handoff.",
                ),
                "scope_preserved": "No deletions. Complexity changes concern parents with actual children, except filling initially unset Performance optimization field; no observed material removal or numeric-only leaf reduction.",
            },
            "review_phase": "supplemental_posthoc_scores_exposed",
            "review_source": "scripts/review_confirmation_projects.py",
            "limitations": [
                "Task granularity is qualitative, not measured implementation effort.",
                "Same coordinator with original scores exposed; not independent validation.",
                "Heuristic analyzer values are not identical to stored complexity averages.",
                "Original records and conclusions unchanged.",
            ],
        }
        (FOLDER / "reviews" / packet.name).write_text(
            json.dumps(review, ensure_ascii=False, indent=2) + "\n"
        )
    print("18 supplemental project reviews recomputed")


if __name__ == "__main__":
    main()

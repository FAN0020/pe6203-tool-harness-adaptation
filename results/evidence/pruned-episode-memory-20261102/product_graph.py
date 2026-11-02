"""Read native persisted graph fields; no task execution or content rewriting."""
from collections import Counter


def graph_facts(store):
    tasks = store["tasks"]
    by = {t["id"]: t for t in tasks}
    missing = [t["id"] for t in tasks if "dependsOn" not in t]
    parent = {k: [t["parentId"]] if t.get("parentId") else [] for k,t in by.items()}
    deps = {k: t.get("dependsOn", []) for k,t in by.items()}
    def cycle(edges):
        visited, active = set(), set()
        def visit(node):
            if node in active:
                return True
            if node in visited or node not in edges:
                return False
            visited.add(node)
            active.add(node)
            if any(visit(n) for n in edges[node]):
                return True
            active.remove(node)
            return False
        return any(visit(n) for n in edges)
    return {"tasks":len(tasks), "unique_ids":len(by),
            "duplicate_ids":[k for k,v in Counter(t["id"] for t in tasks).items() if v != 1],
            "roots":sum(not t.get("parentId") for t in tasks),
            "leaves":sum(t["id"] not in {x.get("parentId") for x in tasks} for t in tasks),
            "dependency_edges":sum(map(len,deps.values())) if not missing else None,
            "dependency_field_missing":missing,
            "dangling_parents":[[k,v] for k,vs in parent.items() for v in vs if v not in by],
            "dangling_dependencies":[[k,v] for k,vs in deps.items() for v in vs if v not in by],
            "parent_cycle":cycle(parent), "dependency_cycle":cycle(deps) if not missing else None}

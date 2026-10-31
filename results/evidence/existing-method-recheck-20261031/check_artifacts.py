"""Offline artifact facts; not a quality score. Generated code is parsed, never executed."""

import ast
import json
import re
from pathlib import Path

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[2]


def inspect(cell):
    result = {
        "cell_id": cell["cell_id"],
        "block": cell["block"],
        "task_id": cell["task_id"],
        "stage": cell["stage"],
        "strategy": cell["strategy"],
        "evidence": cell["evidence"],
    }
    if cell["task_id"] == 133:
        blocks = re.findall(r"```python\s*\n(.*?)```", cell["answer"] or "", re.S)
        parsed = []
        for i, code in enumerate(blocks):
            try:
                tree = ast.parse(code)
                parsed.append(
                    {
                        "block": i,
                        "parses": True,
                        "unknown_ast_attributes": sorted(
                            {
                                n.attr
                                for n in ast.walk(tree)
                                if isinstance(n, ast.Attribute)
                                and isinstance(n.value, ast.Name)
                                and n.value.id == "ast"
                                and not hasattr(ast, n.attr)
                            }
                        ),
                        "imports": [
                            ast.unparse(n)
                            for n in ast.walk(tree)
                            if isinstance(n, (ast.Import, ast.ImportFrom))
                        ],
                    }
                )
            except SyntaxError as exc:
                parsed.append({"block": i, "parses": False, "error": str(exc)})
        result["code_blocks"] = parsed
        result["limit"] = (
            "Parsing is not execution, safety verification or proof of complete code. An unclosed code fence is not parsed."
        )
    if cell["task_id"] == 235:
        result["chart_calls"] = [
            {"tool": c["tool"], "arguments": c["arguments"], "is_error": c["is_error"]}
            for c in cell["calls"]
        ]
        result["expected_from_question"] = {
            "provincial_total": 53.4,
            "monthly_total": 25.4,
            "q4_total": 9.2,
            "category_total": 28.1,
            "region_totals": [15.8, 12.3],
            "gaps": {"electronics": 1.4, "home_appliances": 0.6, "clothing": 1.5},
        }
        result["limit"] = (
            "Expected values recalculated from frozen task235 question. Successful calls do not establish rendered appearance."
        )
    if cell["task_id"] == 283:
        store = cell.get("task_store")
        if store is None:
            result["store"] = "missing"
            return result
        tasks = store["tasks"]
        ids = {t["id"] for t in tasks}
        parent_ids = {t.get("parentId") for t in tasks if t.get("parentId") in ids}
        leaves = [t for t in tasks if t["id"] not in parent_ids]
        dangling = []
        graph = {}
        for t in tasks:
            deps = t.get("dependsOn") or []
            if not isinstance(deps, list):
                dangling.append({"id": t["id"], "invalid_dependency_type": type(deps).__name__})
                deps = []
            graph[t["id"]] = deps
            dangling += [{"id": t["id"], "dependency": d} for d in deps if d not in ids]

        def cycle(node, active, done):
            if node in active:
                return True
            if node in done:
                return False
            active.add(node)
            if any(cycle(d, active, done) for d in graph.get(node, []) if d in ids):
                return True
            active.remove(node)
            done.add(node)
            return False

        done = set()
        cycles = any(cycle(n, set(), done) for n in ids)
        result.update(
            task_count=len(tasks),
            leaf_count=len(leaves),
            parent_count=len(parent_ids),
            leaf_hours=sum(t.get("estimatedHours", 0) for t in leaves),
            unknown_leaf_hours=sum(t.get("estimatedHours") is None for t in leaves),
            dangling_dependencies=dangling,
            dependency_cycle=cycles,
            dangling_parents=store["dangling_parents"],
            complexity_leaves=store["complexity_leaves"],
        )
        result["parent_rollups"] = [
            {
                "id": t["id"],
                "name": t.get("name"),
                "direct_child_count": sum(x.get("parentId") == t["id"] for x in tasks),
                "direct_leaf_hours": sum(
                    x.get("estimatedHours", 0) for x in leaves if x.get("parentId") == t["id"]
                ),
            }
            for t in tasks
            if t["id"] in parent_ids
        ]
        result["mutations"] = [
            c for c in cell["calls"] if any(s in c["tool"] for s in ("update_task", "delete_task"))
        ]
        result["limit"] = (
            "Declared complexity is not independent task difficulty. Review mutation semantics rather than treating warnings disappearing as success."
        )
    return result


def main():
    selected = json.loads((FOLDER / "trial-facts/facts.json").read_text())["cells"]
    selected = [{**c, "block": "replication"} for c in selected]
    assert len(selected) == 6
    print(
        json.dumps(
            {
                "new_model_calls": 0,
                "generated_code_executed": False,
                "cells": [inspect(c) for c in selected],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

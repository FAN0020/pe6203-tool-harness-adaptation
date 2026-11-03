"""Artifact audit and closed feedback for independent project-persistence episodes.

No questions, text values, answers, reasoning, expected counts or TF/PE are exported.
"""

import json
import re

PROPERTIES = {"records", "fields", "structure", "delivery"}
SCHEDULE = {"P01": 900401, "P02": 900402, "P03": 900402, "P04": 900401}
NATIVE_TOOLS = {
    "create_project",
    "get_project",
    "list_projects",
    "update_project",
    "delete_project",
    "create_task",
    "get_task",
    "list_tasks",
    "update_task",
    "delete_task",
    "get_next_task_recommendation",
    "parse_prd",
    "analyze_task_complexity",
    "review_project_status",
    "review_workspace_health",
    "create_memory",
    "get_memory",
    "list_memories",
    "search_memories",
    "update_memory",
    "delete_memory",
    "create_subtask",
    "get_subtask",
    "list_subtasks",
    "update_subtask",
    "delete_subtask",
    "move_task",
    "migrate_tasks",
    "get_task_hierarchy",
    "sequentialthinking",
    "parallel-thinking",
    "convergent-synthesis",
    "migration_status",
    "migrate_subtasks",
    "generate_research_queries",
    "infer_task_progress",
    "research_task",
}
ARGUMENT_FIELDS = {
    "workingDirectory",
    "name",
    "description",
    "owner",
    "dueDate",
    "tags",
    "id",
    "projectId",
    "parentId",
    "taskId",
    "dependsOn",
    "details",
    "priority",
    "complexity",
    "estimatedHours",
    "actualHours",
    "status",
    "completed",
    "showHierarchy",
    "includeCompleted",
    "includeMemories",
    "maxItems",
    "limit",
    "category",
    "query",
    "content",
    "prdContent",
    "generateSubtasks",
    "defaultPriority",
    "estimateComplexity",
    "complexityThreshold",
    "suggestBreakdown",
    "autoCreateSubtasks",
    "thought",
    "nextThoughtNeeded",
    "thoughtNumber",
    "totalThoughts",
    "isRevision",
    "revisesThought",
    "branchFromThought",
    "branchId",
    "needsMoreThoughts",
    "operation",
    "action",
    "targetParentId",
}
UUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")


def audit_store(oracle, store):
    if store is None:
        return {"records": "fail", "fields": "unknown", "structure": "unknown"}
    tasks = store.get("tasks", [])
    projects = store.get("projects", [])
    nodes = oracle["nodes"]
    names = {n["name"] for n in nodes}
    by_name = {t.get("name"): t for t in tasks}
    ids = [t.get("id") for t in tasks]
    records = (
        len(projects) == 1
        and projects[0].get("name") == oracle["project_name"]
        and isinstance(projects[0].get("id"), str)
        and bool(projects[0]["id"])
        and len(tasks) == len(nodes)
        and len(by_name) == len(tasks)
        and set(by_name) == names
        and all(isinstance(i, str) and i for i in ids)
        and len(set(ids)) == len(ids)
        and not store.get("subtasks")
        and (
            "project_description" not in oracle
            or projects[0].get("description") == oracle["project_description"]
        )
    )
    if not records:
        return {"records": "fail", "fields": "unknown", "structure": "unknown"}
    expected = {n["key"]: n for n in nodes}
    levels = {}
    for n in nodes:
        levels[n["key"]] = 0 if n["parent"] is None else levels[n["parent"]] + 1
    project_id = projects[0].get("id")
    fields = True
    structure = True
    for n in nodes:
        t = by_name[n["name"]]
        fields &= all(
            t.get(k) == n[k]
            for k in ("details", "priority", "complexity", "estimatedHours", "status")
        )
        fields &= sorted(t.get("tags", [])) == sorted(n["tags"]) and t.get("completed") is False
        fields &= all(
            type(t.get(k)) in (int, float) for k in ("priority", "complexity", "estimatedHours")
        )
        structure &= t.get("projectId") == project_id and t.get("level", 0) == levels[n["key"]]
        parent = by_name[expected[n["parent"]]["name"]]["id"] if n["parent"] else None
        structure &= (t.get("parentId") or None) == parent
        deps = [by_name[expected[k]["name"]]["id"] for k in n["dependsOn"]]
        structure &= sorted(t.get("dependsOn", [])) == sorted(deps)
    graph = {
        t["id"]: t.get("dependsOn", []) + ([t["parentId"]] if t.get("parentId") else [])
        for t in tasks
    }
    done = set()
    active = set()

    def visit(k):
        if k not in graph or k in active:
            return False
        if k in done:
            return True
        active.add(k)
        for v in graph[k]:
            if not visit(v):
                return False
        active.remove(k)
        done.add(k)
        return True

    structure &= all(visit(k) for k in graph)
    return {
        "records": "pass",
        "fields": "pass" if fields else "fail",
        "structure": "pass" if structure else "fail",
    }


def project_episode(episode_id, trace, routes, properties):
    if episode_id not in SCHEDULE or trace.get("task_id") != SCHEDULE[episode_id]:
        raise ValueError("Only fixed independent synthetic episodes may enter induction")
    if set(properties) != PROPERTIES or any(
        v not in {"pass", "fail", "unknown"} for v in properties.values()
    ):
        raise ValueError("Closed property labels only; never oracle text")
    status = trace.get("execution_status")
    if status not in {
        "completed",
        "output_truncated",
        "max_rounds",
        "error",
        "timeout",
        "not_started",
    }:
        raise ValueError("Unrecognized execution status")
    symbols = {}
    calls = []
    for event in trace["events"]:
        if event.get("type") != "tool_result":
            continue
        call = event["call"]["function"]
        name = routes.get(call["name"], {}).get("tool_name")
        if name not in NATIVE_TOOLS:
            raise ValueError("Unrecognized native tool")
        try:
            args = json.loads(call["arguments"])
        except (TypeError, ValueError):
            args = {}
        if not isinstance(args, dict):
            args = {}
        refs = []
        for key in ("id", "projectId", "parentId", "taskId"):
            if isinstance(args.get(key), str):
                refs.append(args[key])
        if isinstance(args.get("dependsOn"), list):
            refs += [v for v in args["dependsOn"] if isinstance(v, str)]
        consumed = sorted({symbols[v] for v in refs if v in symbols})
        unknown = any(v not in symbols for v in refs)
        result = event["result"]
        contents = [c.get("text", "") for c in result.get("content", []) if c.get("type") == "text"]
        error = bool(result.get("isError", False)) or any(
            re.match(r"^\s*[Ee]rror\b", s) for s in contents
        )
        produced = []
        if not error:
            for s in contents:
                for identity in UUID.findall(s):
                    if identity not in symbols:
                        symbol = f"entity{len(symbols) + 1}"
                        symbols[identity] = symbol
                        produced.append(symbol)
        safe = {
            k: args[k]
            for k in (
                "showHierarchy",
                "includeCompleted",
                "includeMemories",
                "autoCreateSubtasks",
                "suggestBreakdown",
                "generateSubtasks",
                "estimateComplexity",
            )
            if type(args.get(k)) is bool
        }
        calls.append(
            {
                "event_id": f"{episode_id}-C{len(calls) + 1:02d}",
                "native_tool": name,
                "argument_fields": sorted(set(args) & ARGUMENT_FIELDS),
                "safe_booleans": safe,
                "consumes_ids": consumed,
                "produces_ids": produced,
                "unresolved_id_reference": unknown,
                "observed_error": error,
            }
        )
    return {
        "episode": episode_id,
        "execution_status": status,
        "calls": calls,
        "properties": dict(properties),
    }


def training_gate(rows):
    if len(rows) != 4 or {r["episode"] for r in rows} != set(SCHEDULE):
        raise ValueError("Exactly four fixed episodes required")
    for r in rows:
        if r["task_id"] != SCHEDULE[r["episode"]] or any(
            type(r[k]) is not bool for k in ("normal_completion", "core_pass")
        ):
            raise ValueError("Invalid episode identity or outcome")
    positives = [r for r in rows if r["normal_completion"] and r["core_pass"]]
    return {
        "admit_induction": {r["task_id"] for r in positives} == {900401, 900402},
        "positive_episodes": [r["episode"] for r in positives],
        "failed_episodes": [r["episode"] for r in rows if r not in positives],
        "additional_sampling_allowed": False,
    }

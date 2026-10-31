"""Separate catalog mutation, task relevance, and actual trace contact; offline only."""

import json
from pathlib import Path

from raw_cell_verifier import archive_files

HERE = Path(__file__).resolve().parent


def main():
    files, manifest = archive_files(HERE)
    prefix = manifest["prefix"] + "/"

    def read(path):
        return json.loads(files[prefix + path])

    original = {t["tool_id"]: t for t in read("catalogs/90/early.json")["tools"]}
    summaries = []
    for version in ("middle", "late"):
        target = {t["tool_id"]: t for t in read(f"catalogs/90/{version}.json")["tools"]}
        diff = read(f"diffs/90/{version}.json")
        rows = []
        for kind, entries in (("added", diff["added"]), ("removed", diff["removed"]), ("changed", diff["changed"])):
            for entry in entries:
                identity = entry["tool_id"]
                name = identity.split("::", 1)[1]
                fields = entry.get("changed_fields", [])
                levels = ["Tool"] if kind != "changed" else []
                if "parameters" in fields:
                    levels.append("Parameter")
                if "description" in fields:
                    levels.append("Description")
                if name == "search_cards":
                    relevance = "Requested card lookup; newly added filters are optional."
                elif name in ("get_daily_challenge", "get_problem") and version == "late":
                    relevance = "Daily lookup requirement; current route/selector needed after removal."
                else:
                    relevance = "Optional capability; not required by the stated task."
                before = original.get(identity, {}).get("parameters", {}).get("properties", {})
                after = target.get(identity, {}).get("parameters", {}).get("properties", {})
                param_diff = [k for k in before.keys() | after.keys() if before.get(k) != after.get(k)]
                touches = []
                for cell in read("plan.json")["cells"]:
                    if cell["version"] != version:
                        continue
                    result = read(f"cells/{cell['id']}/run/result.json")
                    trace = read(f"cells/{cell['id']}/run/raw_trace.json")
                    calls = []
                    for event in trace["events"]:
                        if event["type"] != "tool_result":
                            continue
                        fn = event["call"]["function"]
                        route = result["model_tool_routes"].get(fn["name"], {})
                        if f"{route.get('server_id')}::{route.get('tool_name')}" != identity:
                            continue
                        args = json.loads(fn["arguments"])
                        calls.append({
                            "round": event["round"],
                            "arguments": args,
                            "changed_parameter_keys_supplied": sorted(set(args) & set(param_diff)),
                            "structured_error": bool(event["result"].get("isError")),
                        })
                    touches.append({"cell_id": cell["id"], "strategy": cell["strategy"], "calls": calls})
                rows.append({
                    "tool_id": identity, "change": kind, "levels": levels,
                    "environment_change_exists": True,
                    "task_relevance": relevance,
                    "changed_parameter_keys": sorted(param_diff),
                    "actual_contact": touches,
                    "causal_limit": "Calling a tool whose description changed does not isolate a description effect; other contract changes and stochastic planning coexist.",
                })
        summaries.append({"stage": version, "changes": rows})
    print(json.dumps({"new_model_calls": 0, "stages": summaries}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

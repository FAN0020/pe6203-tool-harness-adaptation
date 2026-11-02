"""Descriptive mediator audit after all product reviews; never a promotion substitute."""

import json
import re
import argparse
from pathlib import Path
from raw_cell_verifier import archive_files

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RAW = ROOT / "results/raw/extensions/dependency-factorial-v1"
UUID = re.compile(r"\(ID: ([0-9a-f-]{36})\)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interrupted", action="store_true")
    options = parser.parse_args()
    if options.interrupted:
        assert (HERE / "review-freeze-at-stop.json").exists()
        files, manifest = archive_files(HERE / "interruption-1")
        prefix = manifest["prefix"] + "/"

        def read(name):
            return json.loads(files[prefix + name])

        plan = read("plan.json")
        state = read("experiment.json")
        assert state["stop_reason"] == "spend_guard"
        cells = [c for c in plan["cells"] if c["id"] in state["cells"]]
        assert len(cells) == 7 and cells == plan["cells"][:7]

        def stores_for(base):
            return [
                json.loads(v)
                for k, v in files.items()
                if k.startswith(prefix + base + "workspace/") and k.endswith("/tasks.json")
            ]
    else:
        assert (HERE / "review-freeze.json").exists()

        def read(name):
            return json.loads((RAW / name).read_text())

        plan = read("plan.json")
        cells = plan["cells"]

        def stores_for(base):
            return [
                json.loads(p.read_text()) for p in (RAW / base / "workspace").rglob("tasks.json")
            ]

    rows = []
    for cell in cells:
        base = f"cells/{cell['id']}/run/"
        t = read(base + "raw_trace.json")
        r = read(base + "result.json")
        routes = r["model_tool_routes"]
        creates = {}
        updates = []
        calls = []
        responses = []
        for event in t["events"]:
            if event["type"] == "agent_response":
                response = event["response"]
                choice = response["choices"][0]
                usage = response["usage"]
                responses.append(
                    {
                        "round": event["round"],
                        "finish_reason": choice["finish_reason"],
                        "completion_tokens": usage["completion_tokens"],
                        "prompt_tokens": usage["prompt_tokens"],
                        "reasoning_tokens": usage.get("completion_tokens_details", {}).get(
                            "reasoning_tokens"
                        ),
                    }
                )
                continue
            if event["type"] != "tool_result":
                continue
            f = event["call"]["function"]
            name = routes[f["name"]]["tool_name"]
            args = json.loads(f["arguments"])
            text = "\n".join(
                c.get("text", "")
                for c in event["result"].get("content", [])
                if c.get("type") == "text"
            )
            error = bool(event["result"].get("isError")) or text.lstrip().startswith("Error:")
            calls.append({"round": event["round"], "tool": name, "error": error})
            if name == "create_task" and not error:
                match = UUID.search(text)
                if match:
                    creates[match.group(1)] = {
                        "round": event["round"],
                        "has_parent": bool(args.get("parentId")),
                        "dependencies_at_creation": len(args.get("dependsOn", [])),
                    }
            elif name == "update_task" and "dependsOn" in args and not error:
                updates.append(
                    {
                        "round": event["round"],
                        "id": args.get("id"),
                        "deps": args["dependsOn"],
                        "dependency_only": set(args) <= {"id", "workingDirectory", "dependsOn"},
                        "target_seen": args.get("id") in creates
                        and creates[args["id"]]["round"] < event["round"],
                        "all_refs_seen": all(
                            x in creates and creates[x]["round"] < event["round"]
                            for x in args["dependsOn"]
                        ),
                    }
                )
        stores = stores_for(base)
        assert len(stores) <= 1
        store = stores[0] if stores else {"tasks": []}
        final = {x["id"]: x for x in store["tasks"]}
        deferred = []
        for identity, creation in creates.items():
            if (
                identity in final
                and final[identity].get("dependsOn")
                and creation["dependencies_at_creation"] == 0
                and any(u["id"] == identity and u["deps"] for u in updates)
            ):
                deferred.append(identity)
        rows.append(
            {
                "cell_id": cell["id"],
                "task_id": cell["task_id"],
                "block_index": cell["seed"],
                "strategy": cell["strategy"],
                "stage": cell["version"],
                "execution_status": r["execution_status"],
                "persisted_records": len(final),
                "created_records": len(creates),
                "created_with_dependencies": sum(
                    c["dependencies_at_creation"] > 0 for c in creates.values()
                ),
                "postcreation_dependency_writes": len(updates),
                "dependency_only_writes": sum(u["dependency_only"] for u in updates),
                "deferred_records_final_nonempty": len(deferred),
                "all_update_refs_previously_seen": all(
                    u["target_seen"] and u["all_refs_seen"] for u in updates
                ),
                "calls": calls,
                "responses": responses,
                "reasoning_text_read": False,
            }
        )
    target = (
        "partial-mechanism-projection.json" if options.interrupted else "mechanism-projection.json"
    )
    (HERE / target).write_text(json.dumps(rows, indent=2) + "\n")
    print(
        json.dumps(
            [{k: v for k, v in x.items() if k not in ("calls", "responses")} for x in rows],
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

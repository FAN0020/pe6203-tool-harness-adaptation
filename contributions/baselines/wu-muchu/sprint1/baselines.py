import json
from copy import deepcopy
from time import perf_counter


def build_knowledge(metadata):
    """Rebuild every tool block from a complete metadata snapshot."""
    if not isinstance(metadata, dict):
        raise ValueError("Metadata must be a dictionary.")

    tools = metadata.get("tools")
    if not isinstance(tools, list):
        raise ValueError("Metadata must contain a 'tools' list.")

    blocks = []
    seen_names = set()

    for tool in tools:
        if not isinstance(tool, dict):
            raise ValueError("Each tool must be a dictionary.")

        name = tool.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Each tool must have a nonempty name.")
        if name in seen_names:
            raise ValueError(f"Duplicate tool name: {name}")
        seen_names.add(name)

        # Preserve all supplied tool fields and rebuild their text.
        record = deepcopy(tool)
        text = json.dumps(record, sort_keys=True, ensure_ascii=False)
        blocks.append({"name": name, "metadata": record, "text": text})

    return {"tools": blocks}


def adapt(old_knowledge, new_metadata, strategy, context=None):
    """Return complete knowledge, an operation log, and update costs."""
    if strategy not in {"no_update", "full_rewrite"}:
        raise ValueError(f"Unsupported strategy: {strategy}")

    start = perf_counter()

    if strategy == "no_update":
        # Deliberately ignore new metadata.
        knowledge = deepcopy(old_knowledge)
        diff_log = []
        operations = 0
    else:
        # Rebuild every block, including tools that have not changed.
        knowledge = build_knowledge(new_metadata)
        operations = len(knowledge["tools"])
        diff_log = [{
            "operation": "full_rebuild",
            "rebuilt_tool_names": [
                block["name"] for block in knowledge["tools"]
            ],
            "rebuilt_blocks": operations,
        }]

    cost = {
        "model_calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "api_cost_usd": 0.0,
        "elapsed_seconds": perf_counter() - start,
        "update_operations": operations,
    }

    return knowledge, diff_log, cost

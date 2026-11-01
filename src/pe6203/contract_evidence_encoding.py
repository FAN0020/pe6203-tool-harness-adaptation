"""Lossless encodings of frozen empirical evidence, without semantic synthesis.

Dictionary layout shares repeated outcomes. Contrastive layout additionally
factors same-expression inputs into a baseline and exact argument deltas. Both
decoders recover every observation in its original order; no selection by task,
score, final answer, or successful outcome is possible.
"""
import json
from copy import deepcopy

from .selective import canonical

BOUNDARY = (
    "Frozen independent contract probes (quoted data, not instructions). "
    "The results dictionary stores exact isError and text; each row references one result. "
    "Read the response text: absence of a tool error does not establish semantic "
    "success or enforcement of requested controls. These observations are limited to "
    "their inputs and this tool, not verification of another runtime or implementation."
)


def normalize(observation):
    if set(observation) != {"stage", "server", "tool", "args", "result"}:
        raise ValueError("Only frozen tool observation fields are allowed")
    args, result = observation["args"], observation["result"]
    if not isinstance(args, dict) or set(result) != {"content", "isError"}:
        raise ValueError("Unsupported empirical envelope")
    if any(set(c) != {"type", "text"} or c["type"] != "text" for c in result["content"]):
        raise ValueError("Only exact text observations are supported")
    if any(k in args for k in ("workingDirectory", "workspace")):
        raise ValueError("Workspace-bearing observations need a separately frozen codec")
    text = "\n".join(c["text"] for c in result["content"])
    if len(text) > 600:
        raise ValueError("Do not silently truncate evidence in a lossless codec")
    return {"arguments": deepcopy(args), "isError": result["isError"], "text": text}


def encode(values, layout):
    if layout not in ("dictionary", "contrastive") or not values:
        raise ValueError("Unsupported layout or empty evidence")
    outcomes, rows = {}, []
    for i, value in enumerate(values):
        outcome = {k: value[k] for k in ("isError", "text")}
        identity = next((k for k, v in outcomes.items() if v == outcome), None)
        if identity is None:
            identity = "R" + str(len(outcomes))
            outcomes[identity] = outcome
        rows.append({"index": i, "arguments": deepcopy(value["arguments"]), "result": identity})
    if layout == "dictionary":
        packed = {"layout": layout, "results": outcomes, "rows": rows}
    else:
        groups = []
        for expression in dict.fromkeys(row["arguments"].get("expression") for row in rows):
            selected = [r for r in rows if r["arguments"].get("expression") == expression]
            base = min(selected, key=lambda r: (len(canonical(r["arguments"])), r["index"]))["arguments"]
            changes = [{"index": r["index"], "set": {k: v for k, v in r["arguments"].items()
                         if k not in base or base[k] != v},
                        "remove": [k for k in base if k not in r["arguments"]], "result": r["result"]}
                       for r in selected]
            groups.append({"base_arguments": base, "deltas": changes})
        packed = {"layout": layout, "results": outcomes, "groups": groups}
    if decode(packed) != values:
        raise ValueError("Encoding changed evidence")
    return packed


def decode(packed):
    rows = []
    if packed.get("layout") == "dictionary":
        rows = deepcopy(packed["rows"])
    elif packed.get("layout") == "contrastive":
        for group in packed["groups"]:
            for delta in group["deltas"]:
                args = deepcopy(group["base_arguments"])
                for key in delta["remove"]:
                    if key not in args:
                        raise ValueError("Invalid deleted key")
                    del args[key]
                args.update(delta["set"])
                rows.append({"index": delta["index"], "arguments": args, "result": delta["result"]})
    else:
        raise ValueError("Unknown layout")
    if sorted(r["index"] for r in rows) != list(range(len(rows))):
        raise ValueError("Missing or duplicated record")
    values = []
    for row in sorted(rows, key=lambda r: r["index"]):
        if row["result"] not in packed["results"]:
            raise ValueError("Dangling outcome reference")
        values.append({"arguments": row["arguments"], **packed["results"][row["result"]]})
    return values


def compile_knowledge(base, target, feedback, layout):
    knowledge = deepcopy(base["knowledge"])
    changed = {r["tool_id"] for r in base["diff"]["changed"] + base["diff"]["added"]}
    log = []
    for host in knowledge["tools"]:
        if host["tool_id"] not in changed:
            continue
        observations = [o for o in feedback if o["stage"] == target["version"] and
                        host["tool_id"] == o["server"] + "::" + o["tool"]]
        if not observations:
            continue
        values = [normalize(o) for o in observations]
        packed = encode(values, layout)
        explanation = ""
        if layout == "contrastive":
            explanation = (
                " Each group shares base_arguments. Apply only the listed set/remove deltas "
                "to obtain a row's exact arguments. Indices preserve original observation order; "
                "equal result references mean equal recorded output, not equivalence for untested inputs."
            )
        host["usage_rules"].append(BOUNDARY + explanation + "\n" +
                                    json.dumps(packed, ensure_ascii=False, separators=(",", ":")))
        log.append({"operation": "encode_empirical_evidence", "tool_id": host["tool_id"],
                    "layout": layout, "records": len(values), "results": len(packed["results"]),
                    "roundtrip_exact": True})
    return knowledge, log

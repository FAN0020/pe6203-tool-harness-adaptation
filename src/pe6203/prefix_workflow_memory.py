"""Induce a constrained procedural memory from verified generic native receipts.

AWM-inspired rule-based abstraction, not a reproduction of its online agent.
No benchmark task, scored trace, heldout oracle or new execution hook is used.
"""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from .selective import validate_adaptation

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "experiments/prefix-workflow-memory-v1.json"
FEEDBACK = ROOT / "experiments/prefix-workflow-feedback-v1.json"
TRIGGER = "slidev-mcp::create_bulk_slides"


def digest(value):
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def induce_workflow(trace):
    """Anti-unify instance strings and the consecutive per-page operation run.

    The grammar is deliberately narrow and frozen. The trace supplies actual tool
    names, arguments, layout constants and action order; it is not arbitrary code.
    """
    names = [row["tool"] for row in trace]
    if names != [
        "create_slidev",
        "set_page",
        "add_page",
        "add_page",
        "add_page",
        "apply_theme",
        "get_all_slides",
        "load_slidev",
        "get_all_slides",
    ]:
        raise ValueError("Unsupported training procedure")
    for row in trace:
        if row["case"] != "train" or row["checks"] or row["result"].get("isError"):
            raise ValueError("Unsuccessful training procedure")
        inner = json.loads(row["result"]["content"][0]["text"])
        if inner.get("success") is not True:
            raise ValueError("Unsuccessful training result")
    for i, row in enumerate(trace[1:5]):
        inner = json.loads(row["result"]["content"][0]["text"])
        if inner["output"] != i:
            raise ValueError("Nonsequential training write")
    add_args = [row["arguments"] for row in trace[2:5]]
    stable = [{k: v for k, v in args.items() if k != "content"} for args in add_args]
    if not stable[0] == stable[1] == stable[2] or any(
        set(a) != {"content", "layout"} for a in add_args
    ):
        raise ValueError("Nonuniform training loop")
    steps = []
    for i, row in enumerate(trace):
        if i in (3, 4):
            continue
        args = deepcopy(row["arguments"])
        for key in ("path", "title", "author"):
            if key in args:
                args[key] = "$" + key
        if "content" in args:
            args["content"] = "$first_body" if i == 1 else "$next_body"
        step = {"call": row["tool"], "args": args}
        if i == 2:
            step["repeat"] = "for each subsequent intended slide"
            step["postcondition"] = (
                "Successful output is the next page index; earlier page bodies remain persisted."
            )
        steps.append(step)
    return {
        "intent": "Persist custom slide content as separate page records when template bulk generation is unsuitable.",
        "precondition": "Fresh project with its initial cover. Each body is one slide's Markdown, with no document frontmatter or slide separator.",
        "bindings": "$path/$title/$author identify the project; $first_body is its cover body; $next_body is the next intended page's body.",
        "steps": steps,
        "invariant": "Each set/add call commits one page. The loop does not require a complete document string. Final records must contain all intended page bodies in order; reload verifies persisted state.",
        "scope": "Generic verified procedure; page content and complete task coverage remain the caller's responsibility. Does not clear an already populated project.",
    }


def expand_workflow(program, project, bodies):
    """Offline transfer check only. Never called by the benchmark executor."""
    result = []
    for step in program["steps"]:
        values = bodies[1:] if "repeat" in step else [None]
        for body in values:
            bindings = {"$" + k: v for k, v in project.items()}
            bindings.update({"$first_body": bodies[0], "$next_body": body})
            args = {
                k: bindings.get(v, v) if isinstance(v, str) else v for k, v in step["args"].items()
            }
            result.append({"call": step["call"], "args": args})
    return result


def expected_workflow(base, target, feedback):
    knowledge = deepcopy(base["knowledge"])
    changes = {row["tool_id"]: row for row in base["diff"]["changed"]}
    if target["version"] not in ("middle", "late") or TRIGGER not in changes:
        return knowledge, []
    contract = json.loads(SPEC.read_text())["knowledge_contract"]
    data = FEEDBACK.read_bytes()
    if hashlib.sha256(data).hexdigest() != contract["feedback_sha256"]:
        raise ValueError("Changed frozen training file")
    expected = json.loads(data)["observations"]
    if feedback != expected:
        raise ValueError("Missing or unverified training observations")
    tools = {t["tool_id"]: t for t in knowledge["tools"]}
    for identity, fingerprint in contract["fingerprints"][target["version"]].items():
        if (
            identity not in tools
            or digest({k: tools[identity][k] for k in ("description", "parameters", "routing")})
            != fingerprint
        ):
            raise ValueError("Unverified workflow native contract: " + identity)
    trace = next(row["result"]["trace"] for row in feedback if row["stage"] == target["version"])
    program = induce_workflow(trace)
    before = tools[TRIGGER]["description"]
    tools[TRIGGER]["description"] = (
        before + "\nVerified procedural memory:\n" + json.dumps(program, ensure_ascii=False)
    )
    return knowledge, [
        {
            "operation": "attach_induced_workflow",
            "tool_id": TRIGGER,
            "path": "description",
            "before": before,
            "after": tools[TRIGGER]["description"],
            "basis": [changes[TRIGGER]["change_id"]],
            "training_sha256": digest(trace),
            "program_sha256": digest(program),
        }
    ]


def validate_workflow(candidate, old, target, base, feedback):
    expected, log = expected_workflow(base, target, feedback)
    if candidate != expected:
        return {"errors": ["Candidate differs from frozen workflow delta"], "checks": {}}
    restored = deepcopy(candidate)
    for row in restored["tools"]:
        if row["tool_id"] == TRIGGER and log:
            row["description"] = log[0]["before"]
    result = validate_adaptation(restored, old, target, base["diff"])
    result["checks"]["workflow_records"] = len(log)
    return result

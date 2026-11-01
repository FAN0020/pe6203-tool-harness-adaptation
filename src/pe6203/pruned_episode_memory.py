"""Replay-verified pruning of task-free native creation episodes.

Only finite final-state equivalence is certified, not arbitrary workflow safety.
No benchmark task, score, answer, runtime policy or execution change is an input.
"""

import itertools
import json
from copy import deepcopy

from .relational_probe_memory import PROJECT, ROOT_ID, clean, exported_ids, strings

READS = {"get_project", "get_task", "list_tasks"}
WRITES = {"create_project", "create_task", "update_task"}


def schedules(proposal):
    steps = proposal["steps"]
    if not steps or steps[0]["tool"] != "create_project":
        raise ValueError("Changed producer required")
    if any(s["tool"] not in READS | WRITES for s in steps):
        raise ValueError("Uncertified operation")
    reads = [s["id"] for s in steps if s["tool"] in READS]
    answer = []
    for flags in itertools.product((False, True), repeat=len(reads)):
        keep = {n for n, flag in zip(reads, flags) if flag}
        selected = [s for s in steps if s["tool"] in WRITES or s["id"] in keep]
        known = {"$WORKSPACE"}
        for s in selected:
            if {v for v in strings(s["arguments"]) if v.startswith("$")} - known:
                raise ValueError("Reference depends on an elided step")
            if s["tool"] == "create_project":
                known.add(f"${s['id']}.project_id")
            elif s["tool"] == "create_task":
                known.add(f"${s['id']}.task_id")
        answer.append([s["id"] for s in selected])
    return sorted(answer, key=lambda s: (len(s), s))


def state_signature(rows):
    identities = {}
    for i, row in enumerate(rows):
        if (
            row.get("not_executed")
            or row.get("native_exception")
            or row.get("result", {}).get("isError")
        ):
            raise ValueError("Unsuccessful native replay")
        if i and row["before_state"] != rows[i - 1]["after_state"]:
            raise ValueError("Broken state continuity")
        for collection in ("projects", "tasks", "subtasks"):
            for side in ["before_state", "after_state"]:
                records = row[side].get(collection, [])
                if len({r["id"] for r in records}) != len(records):
                    raise ValueError("Duplicate state identifiers")
            before = {r["id"] for r in row["before_state"].get(collection, [])}
            added = [r for r in row["after_state"].get(collection, []) if r["id"] not in before]
            exports = exported_ids(row["id"], row)
            if added and ({r["id"] for r in added} - set(exports.values())):
                raise ValueError("Created record lacks receipt witness")
            identities.update({value: key for key, value in exports.items()})

    def normalize(value, key=None):
        if isinstance(value, dict):
            return {k: normalize(v, k) for k, v in value.items()}
        if isinstance(value, list):
            return [normalize(v, key) for v in value]
        if key in {"id", "projectId", "parentId", "dependsOn"} and isinstance(value, str):
            return identities.get(value, value)
        return value

    state = normalize(clean(rows[-1]["after_state"]))
    for collection in ("projects", "tasks", "subtasks"):
        if collection in state:
            state[collection] = sorted(state[collection], key=lambda r: r["id"])
    return state


def select_replay(proposal, reference, trials):
    expected = schedules(proposal)
    if [t["steps"] for t in trials] != expected:
        raise ValueError("Every pre-scheduled replay must be retained in fixed order")
    target = state_signature(reference)
    passing = []
    for trial in trials:
        if [r["id"] for r in trial["rows"]] != trial["steps"]:
            raise ValueError("Incomplete scheduled observations")
        if trial["rows"][0]["before_state"] != reference[0]["before_state"]:
            raise ValueError("Different starting fixture")
        try:
            equivalent = state_signature(trial["rows"]) == target
        except ValueError:
            equivalent = False
        if equivalent:
            passing.append(trial)
    if not passing:
        raise ValueError("No equivalent replay")
    return deepcopy(passing[0])


def memory_note(proposal, reference, trials):
    chosen = select_replay(proposal, reference, trials)
    state = state_signature(chosen["rows"])
    records = [
        dict(collection=k, **r)
        for k in ("projects", "tasks", "subtasks")
        for r in state.get(k, [])
        if r["id"].startswith("$P")
    ]
    # Terminal witness contains actual record names and links, no free-form task answer.
    witness = [
        {k: r[k] for k in ["collection", "id", "name", "projectId", "parentId"] if k in r}
        for r in records
    ]
    value = {
        "kind": "replay_verified_finite_creation_episode",
        "steps": [
            {k: s[k] for k in ["id", "tool", "arguments"]}
            for s in proposal["steps"]
            if s["id"] in chosen["steps"]
        ],
        "terminal_record_witness": witness,
        "omitted_read_steps": [
            s["id"] for s in proposal["steps"] if s["id"] not in chosen["steps"]
        ],
        "proof_scope": "All scheduled read-elision replays retained. This shortest replay preserves the complete persisted state of this one synthetic creation episode, including unrelated fixture records; exported IDs also occur in native receipts.",
        "limits": "This is a finite example, not a universal plan or proof that a user task is complete. It proves only these record creations and links. A read may be required for another information need, changed state or operation. No benchmark question, deliverable or answer is encoded.",
    }
    return "Verified minimal native episode: " + json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def compile_knowledge(base, target, feedback):
    result = deepcopy(base["knowledge"])
    changed = {r["tool_id"] for r in base["diff"]["changed"] + base["diff"]["added"]}
    if ROOT_ID not in changed:
        return result, []
    matches = [
        r for r in feedback if r.get("stage") == target["version"] and r.get("server") == PROJECT
    ]
    if len(matches) != 1:
        raise ValueError("Unique stage replay certificate required")
    cert = matches[0]["result"]
    if cert.get("kind") != "pruned_episode_memory_v1" or cert.get("semantic_review") != "accepted":
        raise ValueError("Unreviewed replay certificate")
    if cert["inventory"]["target"]["tools"] != [
        t for t in target["tools"] if t["server_id"] == PROJECT
    ]:
        raise ValueError("Catalog drift")
    note = memory_note(cert["proposal"], cert["reference"], cert["trials"])
    tool = next(t for t in result["tools"] if t["tool_id"] == ROOT_ID)
    before = deepcopy(tool["usage_rules"])
    tool["usage_rules"].append(note)
    return result, [
        dict(
            tool_id=ROOT_ID,
            field="usage_rules",
            before=before,
            after=deepcopy(tool["usage_rules"]),
            reason="finite replay-equivalent pruned episode and native record witness",
        )
    ]

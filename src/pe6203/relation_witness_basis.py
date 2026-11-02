"""Select native evidence by finite predicate coverage, never benchmark utility."""

import json
from copy import deepcopy

from .capability_relations import (
    HOST,
    PREDICATES,
    infer_relations,
)
from .capability_relations import (
    compile_knowledge as compile_full,
)
from .selective import canonical


def select_basis(rows):
    relations = infer_relations(rows)  # reject incomplete/duplicate observations
    grouped = {}
    for row in rows:
        vector = tuple(row[p] for p in PREDICATES)
        grouped.setdefault(vector, []).append(row)
    chosen = [
        min(grouped[k], key=lambda r: (len(canonical(r).encode()), canonical(r)))
        for k in sorted(grouped)
    ]
    assert [r["status"] for r in relations] == [r["status"] for r in infer_relations(chosen)]
    return deepcopy(chosen)


def compile_knowledge(base, target, feedback):
    knowledge, edits = compile_full(base, target, feedback)
    if not edits:
        return knowledge, []
    tool = next(t for t in knowledge["tools"] if t["tool_id"] == HOST)
    note = json.loads(tool["usage_rules"][-1].split(": ", 1)[1])
    full = note["paired_observations"]
    note["kind"] = "finite_relation_witness_basis"
    note["sequence_inputs"] = [r["expression"] for r in full]
    note["paired_observations"] = select_basis(full)
    note["relations"] = infer_relations(note["paired_observations"])
    note["selection"] = {
        "rule": "One exact minimum UTF-8 canonical-JSON-byte representative per complete four-predicate truth vector; canonical lexical tie break.",
        "original_rows": len(full),
        "retained_rows": len(note["paired_observations"]),
        "guarantee": "All observed truth vectors and every finite implication falsification status preserved. Lexical cases are not all retained; this is not a general semantic equivalence proof.",
    }
    note["scope"] += (
        " State receipts describe all ordered sequence_inputs, not only the selected witnesses."
    )
    tool["usage_rules"][-1] = "Cross-operation evidence: " + json.dumps(
        note, ensure_ascii=False, separators=(",", ":")
    )
    edits[0]["after"] = deepcopy(tool["usage_rules"])
    edits[0]["reason"] = (
        "delete redundant cross-input witnesses only under complete finite predicate coverage"
    )
    return knowledge, edits

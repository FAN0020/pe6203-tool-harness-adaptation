"""Coverage graph compilation with an independent missing-claim veto."""

import re
from copy import deepcopy

from .description_factor import compile_factor, inventory


def make_inventory(old, target):
    records = inventory(old, target)
    for r in records:
        lines = r["description_lines"]
        # Keep prose paragraphs, headings and parents of nested examples intact.
        r["eligible_lines"] = [
            n
            for n, line in enumerate(lines)
            if re.match(r"^(?:- |\d+\. )", line)
            and not line.rstrip().endswith(":")
            and not (n + 1 < len(lines) and lines[n + 1].startswith((" ", "\t")))
        ]
    return records


def prepare_checks(records, graph):
    if (
        not isinstance(graph, dict)
        or set(graph) != {"relations"}
        or not isinstance(graph["relations"], list)
    ):
        raise ValueError("Expected relations array only")
    by_id = {r["tool_id"]: r for r in records}
    checks, seen = [], set()
    for n, rel in enumerate(graph["relations"], 1):
        if not isinstance(rel, dict) or set(rel) != {"tool_id", "line", "support"}:
            raise ValueError("Invalid relation fields")
        r = by_id.get(rel["tool_id"])
        line = rel["line"]
        if r is None or type(line) is not int or line not in r["eligible_lines"]:
            raise ValueError("Target is not an eligible changed-tool line")
        key = (rel["tool_id"], line)
        if key in seen:
            raise ValueError("Duplicate target")
        seen.add(key)
        if not isinstance(rel["support"], list) or not rel["support"]:
            raise ValueError("Missing support")
        texts = []
        for support in rel["support"]:
            if not isinstance(support, dict):
                raise ValueError("Invalid support")
            kind = support.get("kind")
            if kind == "description" and set(support) == {"kind", "line"}:
                i = support["line"]
                if type(i) is not int or not 0 <= i < len(r["description_lines"]) or i == line:
                    raise ValueError("Invalid/self description support")
                text = r["description_lines"][i]
            elif kind in ("parameters", "output_schema") and set(support) == {"kind", "path"}:
                path = support["path"]
                if (
                    not isinstance(path, list)
                    or not path
                    or any(not isinstance(p, str) for p in path)
                ):
                    raise ValueError("Invalid schema path")
                text = r[kind]
                try:
                    for part in path:
                        text = text[part]
                except (KeyError, TypeError):
                    raise ValueError("Unknown schema support") from None
            else:
                raise ValueError("Invalid support kind or fields")
            if not isinstance(text, str) or not text.strip():
                raise ValueError("Support must be a nonempty string")
            texts.append(text)
        checks.append({"id": f"E{n:03d}", "claim": r["description_lines"][line], "evidence": texts})
    return checks


def compile_verified(old, target, graph, feedback):
    checks = prepare_checks(make_inventory(old, target), graph)
    if (
        not isinstance(feedback, dict)
        or set(feedback) != {"checks"}
        or not isinstance(feedback["checks"], list)
    ):
        raise ValueError("Expected independent checks array")
    reviewed = {}
    for row in feedback["checks"]:
        if not isinstance(row, dict) or set(row) != {"id", "missing_claims", "uncertain"}:
            raise ValueError("Invalid feedback fields")
        if (
            not isinstance(row["id"], str)
            or row["id"] in reviewed
            or type(row["uncertain"]) is not bool
        ):
            raise ValueError("Invalid/duplicate feedback ID or uncertainty")
        if not isinstance(row["missing_claims"], list) or any(
            not isinstance(s, str) or not s.strip() for s in row["missing_claims"]
        ):
            raise ValueError("Invalid missing claims")
        reviewed[row["id"]] = row
    if set(reviewed) != {c["id"] for c in checks}:
        raise ValueError("Must review exactly every relation")
    accepted = [
        (c, r)
        for c, r in zip(checks, graph["relations"])
        if not reviewed[c["id"]]["missing_claims"] and not reviewed[c["id"]]["uncertain"]
    ]
    # A witness is immutable even when another relation proposes deleting it.
    protected = {
        (r["tool_id"], s["line"])
        for _, r in accepted
        for s in r["support"]
        if s["kind"] == "description"
    }
    rows, selected = [], []
    for c, r in accepted:
        if (r["tool_id"], r["line"]) in protected:
            continue
        citations = []
        for s, quote in zip(r["support"], c["evidence"]):
            citations.append(
                {"kind": "description", "lines": [s["line"]], "quote": quote}
                if s["kind"] == "description"
                else {**deepcopy(s), "quote": quote}
            )
        rows.append(
            {
                "tool_id": r["tool_id"],
                "lines": [r["line"]],
                "coverage": citations,
                "reason": "Independent missing-claim check returned no gap or uncertainty; all cited witnesses are protected.",
            }
        )
        selected.append(c["id"])
    result, log = compile_factor(old, target, {"deletions": rows})
    return result, {
        "checks": checks,
        "feedback": deepcopy(feedback),
        "selected": selected,
        "protected_witnesses": [list(p) for p in sorted(protected)],
        "deletion_log": log,
    }

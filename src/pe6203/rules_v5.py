"""V5 structural admission and program rendering; no free-form guarantee type."""

import json
from copy import deepcopy


def evidence_ids(item, identity, changes, sources):
    basis, ids = item["basis"], item["evidence_ids"]
    if (
        not isinstance(basis, list)
        or not basis
        or any(type(b) is not str or b not in changes for b in basis)
    ):
        raise ValueError("Semantic edit needs actual diff IDs")
    if (
        not isinstance(ids, list)
        or not ids
        or any(type(i) is not str or i not in sources for i in ids)
    ):
        raise ValueError("Unknown or missing evidence ID")
    cited = {sources[i]["tool_id"] for i in ids}
    if identity not in cited or not cited.intersection(changes[b]["tool_id"] for b in basis):
        raise ValueError("Evidence must cover the edited record and a basis change")
    if (
        not isinstance(item["reason"], str)
        or not item["reason"].strip()
        or len(item["reason"]) > 1200
    ):
        raise ValueError("Each edit needs a bounded reason")


def decisions(payload, ids, changes, sources):
    if (
        not isinstance(payload, dict)
        or set(payload) != {"decisions"}
        or not isinstance(payload["decisions"], list)
    ):
        raise ValueError("Expected exactly decisions")
    seen = set()
    for row in payload["decisions"]:
        if not isinstance(row, dict) or set(row) != {
            "tool_id",
            "action",
            "reason",
            "basis",
            "evidence_ids",
        }:
            raise ValueError("Invalid review fields")
        identity = row["tool_id"]
        if type(identity) is not str or identity not in ids or identity in seen:
            raise ValueError("Unknown or duplicate review ID")
        seen.add(identity)
        if row["action"] not in {"keep", "update", "unresolved"}:
            raise ValueError("Invalid review action")
        if (
            not isinstance(row["reason"], str)
            or not row["reason"].strip()
            or len(row["reason"]) > 1200
        ):
            raise ValueError("Invalid review reason")
        if row["action"] != "keep" or row["basis"] or row["evidence_ids"]:
            evidence_ids(row, identity, changes, sources)
        elif row["basis"] != [] or row["evidence_ids"] != []:
            raise ValueError("Empty keep evidence must be arrays")
    if seen != ids:
        raise ValueError("Incomplete full-catalog review")
    return payload["decisions"]


def render_rule(row, sources):
    if not isinstance(row, dict) or set(row) != {"kind", "text", "evidence_ids"}:
        raise ValueError("Rules need kind, text and evidence_ids; no free-form guarantees")
    kind, text, ids = row["kind"], row["text"], row["evidence_ids"]
    if not isinstance(text, str) or len(text) > 1200:
        raise ValueError("Invalid rule explanation")
    if (
        not isinstance(ids, list)
        or not ids
        or any(type(i) is not str or i not in sources for i in ids)
    ):
        raise ValueError("Unknown rule evidence ID")
    refs = [sources[i] for i in ids]
    if kind in {"documentation", "source_observation", "probe_observation"}:
        if len(ids) != 1 or text:
            raise ValueError("Literal rules require one evidence ID and empty model text")
        ref = refs[0]
        if kind == "documentation":
            if ref["kind"] != "catalog" or ref["side"] != "target" or ref["field"] != "description":
                raise ValueError("Documentation requires a current description")
            result = "Tool documentation declares (not runtime verified): " + json.dumps(
                ref["value"], ensure_ascii=False
            )
        elif kind == "source_observation":
            if ref["kind"] != "source":
                raise ValueError("Source observation needs source evidence")
            result = "Source excerpt only; not a runtime guarantee: " + json.dumps(
                ref["content"], ensure_ascii=False
            )
        else:
            if ref["kind"] != "probe":
                raise ValueError(
                    "Behavior observation requires a recorded probe, not a catalog claim"
                )
            exchange = json.loads(ref["content"])
            result = (
                "Finite probe observation; applies only to this exchange, not a general guarantee: "
                + json.dumps(
                    {
                        "arguments": exchange["arguments"],
                        "check": exchange["check"],
                        "observed": ref["observation"],
                        "stage": ref["stage"],
                    },
                    ensure_ascii=False,
                )
            )
    elif kind in {"guidance", "unknown", "conflict"}:
        if not text.strip():
            raise ValueError("Guidance/uncertainty needs an explanation")
        if kind == "guidance" and not any(
            r["kind"] == "catalog" and r["side"] == "target" for r in refs
        ):
            raise ValueError("Guidance needs current catalog evidence")
        prefix = {
            "guidance": "Unverified LLM guidance from declared evidence; not an established behavior: ",
            "unknown": "Unknown behavior; do not rely on an unverified guarantee: ",
            "conflict": "Evidence conflict; do not rely on the disputed behavior: ",
        }[kind]
        result = prefix + json.dumps(text, ensure_ascii=False)
    else:
        raise ValueError("Unsupported rule kind; universal guarantees cannot be admitted")
    result += " [evidence: " + ", ".join(ids) + "]"
    if len(result) > 6000:
        raise ValueError("Rendered rule exceeds evidence budget; no silent truncation")
    return result


def patches(payload, ids, changes, sources, records):
    if (
        not isinstance(payload, dict)
        or set(payload) != {"patches"}
        or not isinstance(payload["patches"], list)
    ):
        raise ValueError("Expected exactly patches")
    result, seen = [], set()
    for row in payload["patches"]:
        fields = {"tool_id", "retain_rule_indices", "rules", "reason", "basis", "evidence_ids"}
        if not isinstance(row, dict) or set(row) != fields:
            raise ValueError("Only scoped local-rule operations are allowed")
        identity = row["tool_id"]
        if type(identity) is not str or identity not in ids or identity in seen:
            raise ValueError("Unknown or duplicate patch ID")
        seen.add(identity)
        evidence_ids(row, identity, changes, sources)
        existing, retained = records[identity].get("usage_rules", []), row["retain_rule_indices"]
        if (
            not isinstance(retained, list)
            or any(type(i) is not int or not 0 <= i < len(existing) for i in retained)
            or len(set(retained)) != len(retained)
            or retained != sorted(retained)
        ):
            raise ValueError("Invalid retained rule indices")
        if not isinstance(row["rules"], list) or len(retained) + len(row["rules"]) > 8:
            raise ValueError("Too many local rules")
        for rule in row["rules"]:
            if not isinstance(rule, dict) or not isinstance(rule.get("evidence_ids"), list):
                raise ValueError("Invalid local rule evidence")
            if any(
                type(key) is not str or key not in row["evidence_ids"]
                for key in rule["evidence_ids"]
            ):
                raise ValueError("Rule evidence must be included in the patch's cited evidence")
        rules = [existing[i] for i in retained] + [render_rule(r, sources) for r in row["rules"]]
        result.append(
            {
                **deepcopy(row),
                "usage_rules": rules,
                "withdrawn_rules": [
                    {"index": i, "text": r, "reason": row["reason"]}
                    for i, r in enumerate(existing)
                    if i not in retained
                ],
            }
        )
    if seen != ids:
        raise ValueError("Missing selected patch")
    return result

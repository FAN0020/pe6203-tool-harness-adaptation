"""Lossless local catalog, compact global index and candidate-only evidence.

No task/question/score input is accepted. JSON pointers are local reads, never
model-selected code, network fetches or probe execution.
"""

import json
import math
from copy import deepcopy

from .benchmark import digest
from .evidence_v5 import load_bundle, registry
from .selective import adapt_result as deterministic_patch
from .selective import build_reference_index


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def measure(messages):
    raw = compact(messages)
    size = len(raw.encode("utf-8"))
    return {
        "request_chars": len(raw),
        "request_utf8_bytes": size,
        "estimated_input_tokens": math.ceil(size / 3) + 32,
        "estimate_method": "utf8_bytes_divided_by_3_plus_32_heuristic_not_model_tokenizer",
        "reservation_input_tokens": size + 256,
    }


def leaves(old, new, pointer=""):
    """Exact changed leaves; missing is distinguished from JSON null."""
    if old == new and type(old) is type(new):
        return []
    if isinstance(old, dict) and isinstance(new, dict):
        result = []
        for key in sorted(old.keys() | new.keys()):
            path = pointer + "/" + key.replace("~", "~0").replace("/", "~1")
            if key not in old or key not in new:
                result.append({"pointer": path, "old_exists": key in old, "new_exists": key in new})
            else:
                result.extend(leaves(old[key], new[key], path))
        return result
    return [{"pointer": pointer, "old_exists": True, "new_exists": True}]


def prepare(old, target, evidence_path=None):
    base = deterministic_patch(old, target)
    if base["knowledge"] is None:
        raise ValueError("Deterministic metadata validation failed")
    bundle = load_bundle(evidence_path, target)
    sources = registry(old, target, bundle)
    changes = {
        c["change_id"]: deepcopy(c)
        for kind in ("changed", "added", "removed")
        for c in base["diff"][kind]
    }
    # A finite failed predeclared check is a credible anomaly, not a behavior
    # guarantee. Source excerpts are new evidence to examine, not trusted facts.
    for key, source in sources.items():
        if source["kind"] == "source" or (
            source["kind"] == "probe" and not source["observation"]["matched"]
        ):
            identity = "obs-" + key[2:]
            changes[identity] = {
                "change_id": identity,
                "tool_id": source["tool_id"],
                "kind": "independent_anomaly" if source["kind"] == "probe" else "source_review",
                "evidence_id": key,
            }
    records = {t["tool_id"]: t for t in base["knowledge"]["tools"]}
    mandatory = {}
    for key, change in changes.items():
        identity = change["tool_id"]
        if identity in records and (records[identity]["usage_rules"] or "evidence_id" in change):
            mandatory.setdefault(identity, set()).add(key)
    # Transitive explicit references; semantic dependencies remain the LLM's job.
    index = build_reference_index(old)
    for key, change in changes.items():
        pending, visited = [change["tool_id"]], set()
        while pending:
            ref = pending.pop()
            if ref in visited:
                continue
            visited.add(ref)
            for host in index.get(ref, []):
                if host in records:
                    mandatory.setdefault(host, set()).add(key)
                    pending.append(host)
    return {
        "base": base,
        "bundle": bundle,
        "sources": sources,
        "changes": changes,
        "mandatory": {k: sorted(v) for k, v in sorted(mandatory.items())},
        "records": records,
    }


def screening_packet(state):
    summaries = []
    for key, change in state["changes"].items():
        row = {"change_id": key, "tool_id": change["tool_id"]}
        if "evidence_id" in change:
            row["event"] = change["kind"]
            row["evidence_available_locally"] = True
        else:
            row["event"] = (
                "changed"
                if "old" in change and "new" in change
                else ("added" if "new" in change else "removed")
            )
            row["fields"] = change.get("changed_fields", [])
            row["changed_paths"] = {
                field: leaves(change.get("old", {}).get(field), change.get("new", {}).get(field))
                for field in change.get("changed_fields", [])
            }
        summaries.append(row)
    return {
        "phase": "v6_global_screen",
        "program_completed": "Metadata synchronized; dangling removed-tool rules removed. Do not redo.",
        "catalog": [
            {"tool_id": key, "purpose": record["description"], "rules": record["usage_rules"]}
            for key, record in sorted(state["records"].items())
        ],
        "changes": summaries,
        "mandatory": state["mandatory"],
    }


def selections(response, state):
    if not isinstance(response, dict) or set(response) != {"covered_tool_ids", "candidates"}:
        raise ValueError("Screen must return coverage and candidates")
    coverage = response["covered_tool_ids"]
    if (
        not isinstance(coverage, list)
        or any(type(i) is not str for i in coverage)
        or len(set(coverage)) != len(coverage)
        or set(coverage) != set(state["records"])
    ):
        raise ValueError("Incomplete or duplicate full-catalog screening coverage")
    if not isinstance(response["candidates"], list):
        raise ValueError("Candidates must be a list")
    chosen = {}
    for row in response["candidates"]:
        if not isinstance(row, dict) or set(row) != {
            "tool_id",
            "category",
            "reason",
            "basis",
            "fields",
        }:
            raise ValueError("Invalid semantic candidate fields")
        identity = row["tool_id"]
        if type(identity) is not str or identity not in state["records"] or identity in chosen:
            raise ValueError("Unknown or duplicate candidate")
        if row["category"] not in {"potential", "uncertain", "program_review"}:
            raise ValueError("Invalid candidate category")
        if not isinstance(row["reason"], str) or not 0 < len(row["reason"]) <= 1200:
            raise ValueError("Candidate needs a bounded reason")
        basis = row["basis"]
        if (
            not isinstance(basis, list)
            or not basis
            or any(type(b) is not str or b not in state["changes"] for b in basis)
        ):
            raise ValueError("Candidate requires actual change/event IDs")
        chosen[identity] = deepcopy(row)
    # Model cannot dismiss a program-required record or its basis.
    for identity, basis in state["mandatory"].items():
        if identity not in chosen:
            chosen[identity] = {
                "tool_id": identity,
                "category": "program_review",
                "basis": basis,
                "reason": "Program-required semantic rule/dependency/anomaly review",
                "fields": [],
            }
        else:
            chosen[identity]["basis"] = sorted(set(chosen[identity]["basis"]) | set(basis))
    return [chosen[k] for k in sorted(chosen)]


def _pointer(value, path):
    if not isinstance(path, str) or (path and not path.startswith("/")):
        raise ValueError("Evidence uses a JSON pointer")
    for key in path.split("/")[1:] if path else []:
        key = key.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            if not key.isdigit():
                raise ValueError("Invalid array pointer")
            value = value[int(key)]
        else:
            value = value[key]
    return value


def detail_packet(state, rows, extra_fields=()):
    """Hydrate only selected records and the changes those records cite.

    Full schemas never enter automatically. A requested schema subtree can be
    read explicitly; unchanged siblings and unrelated tools stay local.
    """
    basis = sorted({b for row in rows for b in row["basis"]})
    scope = {r["tool_id"] for r in rows} | {state["changes"][b]["tool_id"] for b in basis}
    sources, requests = {}, []

    def add(source):
        key = "e-" + digest(source)[:24]
        sources[key] = deepcopy(source)

    for source in state["sources"].values():
        if source["tool_id"] not in scope:
            continue
        # Local purposes and the relevant independent observations suffice by
        # default. Schemas are supplied as exact changed leaves below.
        if source["kind"] != "catalog" or source["field"] == "description":
            add(source)
    for b in basis:
        change = state["changes"][b]
        for field in change.get("changed_fields", []):
            if field in {"parameters", "output_schema"}:
                for leaf in leaves(change["old"].get(field), change["new"].get(field)):
                    for side, label in (("old", "old_exists"), ("target", "new_exists")):
                        if leaf[label]:
                            requests.append(
                                {
                                    "tool_id": change["tool_id"],
                                    "side": side,
                                    "field": field,
                                    "pointer": leaf["pointer"],
                                }
                            )
            elif field != "description":
                requests.extend(
                    {"tool_id": change["tool_id"], "side": side, "field": field, "pointer": ""}
                    for side in ("old", "target")
                )
    for row in rows:
        if not isinstance(row["fields"], list):
            raise ValueError("Requested evidence fields must be a list")
        requests.extend(row["fields"])
    requests.extend(extra_fields)
    for req in requests:
        # A selector with tool/side/field unambiguously names the whole field.
        # Normalizing its missing root pointer is deterministic, not another
        # semantic LLM decision. Never ignore unknown selector keys.
        if isinstance(req, dict) and set(req) == {"tool_id", "side", "field"}:
            req = {**req, "pointer": ""}
        if not isinstance(req, dict) or set(req) != {"tool_id", "side", "field", "pointer"}:
            raise ValueError("Only tool/side/field/pointer evidence reads are allowed")
        if req["tool_id"] not in scope or req["side"] not in {"old", "target"}:
            raise ValueError("Evidence request exceeds candidate/change scope")
        if req["field"] not in {
            "description",
            "parameters",
            "output_schema",
            "routing",
            "name",
            "usage_rules",
        }:
            raise ValueError("Unknown evidence field")
        source = next(
            (
                s
                for s in state["sources"].values()
                if s["kind"] == "catalog"
                and all(s[k] == req[k] for k in ("tool_id", "side", "field"))
            ),
            None,
        )
        if source is None:
            raise ValueError("Requested evidence not available in that catalog side")
        try:
            value = _pointer(source["value"], req["pointer"])
        except (KeyError, IndexError, TypeError):
            raise ValueError("Requested evidence pointer not found") from None
        if req["pointer"]:
            add({**source, "pointer": req["pointer"], "value": deepcopy(value)})
        else:
            add(source)
    # The model sees deduplicated values and short evidence handles. The full
    # provenance stays in this local registry and is restored by the program.
    pool, refs = {}, {}
    for key, source in sources.items():
        value = source.get("value") if source["kind"] == "catalog" else source["content"]
        content_id = "v-" + digest(value)[:20]
        pool[content_id] = value
        refs[key] = {k: source[k] for k in ("tool_id", "side", "field", "kind")}
        refs[key].update(content_id=content_id)
        if "pointer" in source:
            refs[key]["pointer"] = source["pointer"]
    packet = {
        "phase": "v6_local_patch",
        "changes": [{"change_id": b, "tool_id": state["changes"][b]["tool_id"]} for b in basis],
        "selected": [
            {
                "tool_id": r["tool_id"],
                "rules": state["records"][r["tool_id"]]["usage_rules"],
                "review": r["reason"],
                "category": r["category"],
                "basis": r["basis"],
            }
            for r in rows
        ],
        "evidence_registry": refs,
        "content_pool": pool,
        "evidence_scope": "Current stage, catalog/source declarations or finite independent probes; no universal guarantees",
    }
    return packet, sources

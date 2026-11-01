"""QI-V3 conservative capability evidence: literal observations, never inferred guarantees."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from .benchmark import digest, read_json, write_json
from .hybrid_selective import adapt_result as v2_result

VERSION = "hybrid_v3"
LIMIT = (
    "Evidence concerns this tool contract/source or the recorded probe input only. "
    "It does not execute, audit or validate a newly generated Python artifact. "
    "A prompt/template is guidance, not an artifact audit. Source quotations establish "
    "provenance, not entailment or complete behavioral/security guarantees."
)
FIELDS = ("tool_id", "description", "parameters", "output_schema", "routing")


def fingerprint(tool):
    return digest({k: tool.get(k) for k in FIELDS})


def load_evidence(path):
    """Resolve explicit source files before updating; never execute/import them."""
    path = Path(path).resolve()
    bundle = read_json(path)
    if set(bundle) != {"version", "entries"} or bundle["version"] != "capability-evidence-v1":
        raise ValueError("Invalid capability evidence bundle")
    if not isinstance(bundle["entries"], list) or len(bundle["entries"]) > 1000:
        raise ValueError("Invalid capability entries")
    entries = []
    for entry in bundle["entries"]:
        if not isinstance(entry, dict):
            raise ValueError("Invalid capability entry")
        if entry.get("kind") == "catalog":
            entries.append(deepcopy(entry))
            continue
        if set(entry) != {"tool_id", "tool_fingerprint", "kind", "path", "sha256", "quote"}:
            raise ValueError("Only literal source/probe evidence is supported; no semantic claims")
        source = (path.parent / entry["path"]).resolve()
        if not source.is_relative_to(path.parent) or not source.is_file():
            raise ValueError("Evidence files must be inside the independent bundle directory")
        if source.stat().st_size > 200000:
            raise ValueError("Evidence file exceeds limit")
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError("Evidence source hash mismatch")
        entries.append({**entry, "content": data.decode("utf-8")})
    return {"version": bundle["version"], "entries": entries}


def enrich(candidate, old, bundle):
    """Copy only exact evidence; unknown or stale boundaries remain explicitly unresolved."""
    if not isinstance(bundle, dict) or set(bundle) != {"version", "entries"}:
        raise ValueError("Capability evidence is required for hybrid_v3")
    if bundle["version"] != "capability-evidence-v1" or not isinstance(bundle["entries"], list):
        raise ValueError("Invalid capability evidence")
    tools = {t["tool_id"]: t for t in candidate["tools"]}
    previous = {t["tool_id"]: t for t in old["tools"]}
    observations = {identity: [] for identity in tools}
    for row in bundle["entries"]:
        if not isinstance(row, dict):
            raise ValueError("Invalid evidence row")
        kind = row.get("kind")
        keys = {"tool_id", "tool_fingerprint", "kind", "quote"}
        if kind in {"source", "probe"}:
            keys |= {"path", "sha256", "content"}
        elif kind != "catalog":
            raise ValueError("Unsupported evidence kind")
        if set(row) != keys or row["tool_id"] not in tools:
            raise ValueError("Unsupported scope/semantic assertion or unknown tool")
        tool = tools[row["tool_id"]]
        if row["tool_fingerprint"] != fingerprint(tool):
            raise ValueError("Stale evidence: tool contract fingerprint mismatch")
        quote = row["quote"]
        original = tool["description"] if kind == "catalog" else row["content"]
        if not isinstance(quote, str) or not quote.strip() or len(quote) > 4000:
            raise ValueError("Invalid evidence quotation")
        if not isinstance(original, str) or quote not in original:
            raise ValueError("Unsupported conclusion: quotation not in source")
        if kind != "catalog" and digest_bytes(original) != row["sha256"]:
            raise ValueError("Evidence content hash mismatch")
        item = {
            "kind": kind,
            "object": {
                "catalog": "declared_tool_contract",
                "source": "tool_source_excerpt",
                "probe": "recorded_probe_exchange_only",
            }[kind],
            "literal_observation": quote,
            "source_sha256": digest_bytes(original),
        }
        if kind == "probe":
            try:
                exchange = json.loads(original)
            except ValueError:
                raise ValueError(
                    "Probe evidence must contain a structured input/result exchange"
                ) from None
            if (
                not isinstance(exchange, dict)
                or set(exchange) != {"tool_id", "tool_fingerprint", "arguments", "result"}
                or exchange["tool_id"] != row["tool_id"]
                or exchange["tool_fingerprint"] != row["tool_fingerprint"]
                or not isinstance(exchange["arguments"], dict)
            ):
                raise ValueError("Probe evidence subject/input mismatch")
            item["recorded_arguments"] = deepcopy(exchange["arguments"])
            # Recorded result is literal evidence, not an authenticated behavioral claim.
        if kind != "catalog":
            item["source_path"] = row["path"]
        observations[row["tool_id"]].append(item)
    changes = []
    for identity, tool in tools.items():
        # Never trust carried/generated extra fields. Fresh evidence is required each update.
        prior = previous.get(identity, {}).get("capability_boundary")
        boundary = {
            "version": "capability-boundary-v1",
            "tool_fingerprint": fingerprint(tool),
            "status": "literal_evidence_only"
            if observations[identity]
            else "unresolved_no_evidence",
            "observations": observations[identity],
            "limitation": LIMIT,
        }
        tool["capability_boundary"] = boundary
        if boundary != prior:
            changed = identity not in previous or fingerprint(previous[identity]) != fingerprint(
                tool
            )
            changes.append(
                {
                    "operation": "capability_change_propagation"
                    if changed
                    else "initial_evidence_enrichment"
                    if prior is None
                    else "evidence_refresh",
                    "tool_id": identity,
                    "boundary": deepcopy(boundary),
                }
            )
    return changes


def digest_bytes(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def adapt_result(old, target, context=None):
    context = deepcopy(context or {})
    bundle = context.pop("capability_evidence", None)
    if bundle is None:
        raise ValueError("hybrid_v3 requires independently frozen capability_evidence")
    # Strip untrusted extra boundary fields before V2's protected-field checks/model requests.
    clean_old, clean_target = deepcopy(old), deepcopy(target)
    for data in (clean_old, clean_target):
        for tool in data["tools"]:
            tool.pop("capability_boundary", None)
    # Reject stale/invented boundary inputs before spending V2 model budget.
    enrich(deepcopy(clean_target), clean_old, bundle)
    context["selective_mode"] = "hybrid_v2"
    result = v2_result(clean_old, clean_target, context)
    edits = enrich(result["knowledge"], old, bundle)
    result["changes"] += edits
    result["cost"]["method"] = "hybrid_selective_patch_v3"
    result["cost"]["update_operations"] += len(edits)
    result["audit"].update(
        pipeline_version=VERSION,
        capability_changes=edits,
        capability_evidence_sha256=digest(bundle),
    )
    return result


def adapt(old, target, context=None):
    result = adapt_result(old, target, context)
    return result["knowledge"], result["changes"], result["cost"]


def write_adaptation(old_path, metadata_path, output, context=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    artifact = {
        "schema_version": "1.0",
        "strategy": "selective_patch",
        "pipeline_version": VERSION,
        "status": "failed",
        "validation": {"errors": []},
    }
    result = None
    try:
        result = adapt_result(
            read_json(old_path),
            read_json(metadata_path),
            {**(context or {}), "audit_path": str(output / "v2-audit.json")},
        )
        write_json(output / "knowledge.json", result["knowledge"])
        write_json(output / "updater-audit.json", result["audit"])
        artifact.update(
            status="validated",
            benchmark_commit=result["knowledge"]["benchmark_commit"],
            target_stage=result["knowledge"]["version"],
            input={
                "old_file_sha256": hashlib.sha256(Path(old_path).read_bytes()).hexdigest(),
                "target_file_sha256": hashlib.sha256(Path(metadata_path).read_bytes()).hexdigest(),
            },
            output={
                "knowledge_path": "knowledge.json",
                "knowledge_file_sha256": hashlib.sha256(
                    (output / "knowledge.json").read_bytes()
                ).hexdigest(),
            },
            patch=result["changes"],
            cost=result["cost"],
            capability_evidence_sha256=result["audit"]["capability_evidence_sha256"],
        )
    except Exception as exc:
        audit = getattr(exc, "audit", None)
        if audit is not None:
            artifact.update(cost=audit["cost"], updater_audit_path="v2-audit.json")
        elif result is not None:
            artifact["cost"] = result["cost"]
        (output / "knowledge.json").unlink(missing_ok=True)
        artifact["validation"]["errors"].append(
            type(exc).__name__ + ": " + str(exc)
            if isinstance(exc, ValueError)
            else type(exc).__name__
        )
        raise
    finally:
        write_json(output / "adaptation.json", artifact)
    return artifact

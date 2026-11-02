"""Task-independent V5 evidence registry and bounded, declarative MCP probes.

IDs identify bytes and subjects, not semantic truth. Source excerpts stay source
observations; probe conclusions stay scoped to the recorded exchange. No model
code, benchmark question, answer, judge feedback or arbitrary shell is executed.
"""

import asyncio
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from time import perf_counter

from jsonschema import Draft202012Validator

from .benchmark import digest, read_json, source, write_json

VERSION = "selective-evidence-v5"
FIELDS = ("name", "server_id", "tool_id", "description", "parameters", "output_schema", "routing")


def fingerprint(tool):
    return digest({key: tool.get(key) for key in FIELDS})


def check_result(result, check):
    """Evaluate a finite observation, not an arbitrary natural-language claim."""
    if not isinstance(check, dict) or set(check) != {"pointer", "operator", "expected"}:
        raise ValueError("Probe checks require pointer, operator and expected")
    pointer, op = check["pointer"], check["operator"]
    if not isinstance(pointer, str) or (pointer and not pointer.startswith("/")):
        raise ValueError("Invalid JSON pointer")
    if op not in {"equals", "contains"}:
        raise ValueError("Unsupported probe check operator")
    value, found = result, True
    try:
        for key in pointer.split("/")[1:] if pointer else []:
            key = key.replace("~1", "/").replace("~0", "~")
            if isinstance(value, list):
                if not key.isdigit():
                    raise KeyError(key)
                value = value[int(key)]
            else:
                value = value[key]
    except (KeyError, IndexError, TypeError):
        value, found = None, False
    expected = check["expected"]
    if op == "contains" and not isinstance(expected, str):
        raise ValueError("Contains checks require a string")
    matched = found and (
        type(value) is type(expected) and value == expected
        if op == "equals"
        else isinstance(value, str) and expected in value
    )
    return {"found": found, "value": deepcopy(value), "matched": bool(matched)}


def load_bundle(path, target):
    """Freeze explicitly supplied files; never import, fetch or execute sources."""
    if path is None:
        return {"version": VERSION, "entries": []}
    path = Path(path).resolve()
    bundle = read_json(path)
    if not isinstance(bundle, dict) or set(bundle) != {"version", "entries"}:
        raise ValueError("Invalid V5 evidence bundle")
    if bundle["version"] != VERSION or not isinstance(bundle["entries"], list):
        raise ValueError("Invalid V5 evidence version/entries")
    if len(bundle["entries"]) > 128:
        raise ValueError("Too many independent evidence entries")
    tools = {t["tool_id"]: t for t in target["tools"]}
    entries = []
    for entry in bundle["entries"]:
        fields = {
            "tool_id",
            "tool_fingerprint",
            "stage",
            "benchmark_commit",
            "kind",
            "path",
            "sha256",
        }
        if not isinstance(entry, dict) or set(entry) != fields:
            raise ValueError("Only scoped source/probe entries are accepted")
        tool = tools.get(entry["tool_id"])
        if (
            tool is None
            or entry["tool_fingerprint"] != fingerprint(tool)
            or entry["stage"] != target["version"]
            or entry["benchmark_commit"] != target["benchmark_commit"]
            or entry["kind"] not in {"source", "probe"}
        ):
            raise ValueError("Stale or unknown evidence subject/environment")
        if not isinstance(entry["path"], str) or Path(entry["path"]).is_absolute():
            raise ValueError("Evidence requires a relative path")
        source = (path.parent / entry["path"]).resolve()
        if not source.is_relative_to(path.parent) or not source.is_file():
            raise ValueError("Evidence must stay inside its frozen bundle directory")
        if source.stat().st_size > 24000:
            raise ValueError("Evidence exceeds the bounded excerpt/exchange limit")
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError("Evidence file hash mismatch")
        content = data.decode("utf-8")
        observation = None
        if entry["kind"] == "probe":
            exchange = json.loads(content)
            required = {
                "tool_id",
                "tool_fingerprint",
                "stage",
                "benchmark_commit",
                "arguments",
                "result",
                "check",
            }
            if not isinstance(exchange, dict) or set(exchange) != required:
                raise ValueError("Probe must be an exact scoped input/result/check exchange")
            if any(exchange[key] != entry[key] for key in required & fields):
                raise ValueError("Probe subject/environment mismatch")
            if not isinstance(exchange["arguments"], dict):
                raise ValueError("Invalid probe arguments")
            if not Draft202012Validator(tool["parameters"]).is_valid(exchange["arguments"]):
                raise ValueError("Probe arguments do not match the frozen schema")
            observation = check_result(exchange["result"], exchange["check"])
        elif not content.strip():
            raise ValueError("Source excerpts must be nonempty")
        entries.append({**deepcopy(entry), "content": content, "observation": observation})
    return {"version": VERSION, "entries": entries}


def registry(old, target, bundle):
    """Program-generated IDs restore the exact source; models never copy quotes."""
    result = {}

    def add(row):
        identity = "e-" + digest(row)[:24]
        if identity in result and result[identity] != row:
            raise ValueError("Evidence ID collision")
        result[identity] = row

    for side, catalog in (("old", old), ("target", target)):
        for tool in catalog["tools"]:
            for field in (*FIELDS, "usage_rules"):
                if field not in tool:
                    continue
                value = tool[field]
                add(
                    {
                        "kind": "catalog",
                        "side": side,
                        "tool_id": tool["tool_id"],
                        "field": field,
                        "value": deepcopy(value),
                        "tool_fingerprint": fingerprint(tool),
                        "stage": catalog["version"],
                        "benchmark_commit": catalog["benchmark_commit"],
                    }
                )
    for entry in bundle["entries"]:
        add({**deepcopy(entry), "side": "target", "field": "content"})
    return result


async def collect_probes(root, plan_path, output):
    """Run only a predeclared, explicitly reviewed probe plan in a fresh workspace.

    This opt-in command starts archived MCP services. The caller reviews the
    finite actions and freezes the plan before scored generation; no agent or
    updater LLM chooses new arguments or interprets successes as general proofs.
    """
    from .baselines import build_knowledge
    from .transport import check_arguments, sessions, snapshot

    plan_path, output = Path(plan_path).resolve(), Path(output).resolve()
    raw = plan_path.read_bytes()
    plan = json.loads(raw)
    if not isinstance(plan, dict) or set(plan) != {
        "version",
        "reviewed",
        "catalog",
        "timeout_seconds",
        "probes",
    }:
        raise ValueError("Invalid V5 probe plan; task/answer/score inputs are forbidden")
    if plan["version"] != "selective-probes-v5" or plan["reviewed"] is not True:
        raise ValueError("Probe actions must be explicitly reviewed before execution")
    if type(plan["timeout_seconds"]) is not int or not 1 <= plan["timeout_seconds"] <= 30:
        raise ValueError("Invalid probe timeout")
    probes = plan["probes"]
    if not isinstance(probes, list) or not 1 <= len(probes) <= 16:
        raise ValueError("Probe plan must have 1..16 fixed exchanges")
    catalog = build_knowledge(read_json(plan_path.parent / plan["catalog"]))
    lock, _ = source(root)
    if catalog["benchmark_commit"] != lock["commit"] or catalog["version"] not in lock["stages"]:
        raise ValueError("Probe catalog does not match the pinned benchmark environment")
    tools = {t["tool_id"]: t for t in catalog["tools"]}
    for row in probes:
        if not isinstance(row, dict) or set(row) != {"tool_id", "arguments", "check"}:
            raise ValueError("Invalid fixed probe")
        if row["tool_id"] not in tools or not isinstance(row["arguments"], dict):
            raise ValueError("Unknown probe tool/arguments")
        check_result({}, row["check"])
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "frozen-plan.json", plan)
    write_json(output / "frozen-catalog.json", catalog)
    workspace = output / "workspace"
    workspace.mkdir()
    started = perf_counter()
    audit = {
        "status": "started",
        "plan_sha256": hashlib.sha256(raw).hexdigest(),
        "catalog_sha256": digest(catalog),
        "calls": [],
        "actual_mcp_execution": False,
    }
    entries = []
    try:
        servers = sorted({tools[p["tool_id"]]["server_id"] for p in probes})
        async with sessions(
            root,
            catalog["version"],
            servers,
            workspace,
            output / "mcp.stderr.log",
            plan["timeout_seconds"],
        ) as clients:
            live = await snapshot(clients, catalog["version"], catalog["benchmark_commit"])
            live_tools = {t["tool_id"]: t for t in live["tools"]}
            for index, row in enumerate(probes):
                tool = tools[row["tool_id"]]
                if row["tool_id"] not in live_tools or fingerprint(
                    live_tools[row["tool_id"]]
                ) != fingerprint(tool):
                    raise ValueError("Live MCP contract differs from the frozen probe catalog")
                arguments = deepcopy(row["arguments"])
                # The sole substitution is an isolated, pre-generation workspace.
                for field in ("workingDirectory", "workspace"):
                    if arguments.get(field) == "{workspace}":
                        arguments[field] = str(workspace)
                check_arguments(arguments, workspace)
                Draft202012Validator(tool["parameters"]).validate(arguments)
                attempt = {"tool_id": row["tool_id"], "arguments": arguments, "status": "started"}
                audit["calls"].append(attempt)
                write_json(output / "probe-audit.json", audit)
                response = await asyncio.wait_for(
                    clients[tool["server_id"]].call_tool(tool["name"], arguments),
                    plan["timeout_seconds"],
                )
                result = response.model_dump(mode="json", exclude_none=True)
                audit["actual_mcp_execution"] = True
                exchange = {
                    "tool_id": row["tool_id"],
                    "tool_fingerprint": fingerprint(tool),
                    "stage": catalog["version"],
                    "benchmark_commit": catalog["benchmark_commit"],
                    "arguments": arguments,
                    "result": result,
                    "check": row["check"],
                }
                if len(json.dumps(exchange).encode()) > 23000:
                    raise ValueError("Probe response exceeds evidence budget; no silent truncation")
                file = output / f"probe-{index}.json"
                write_json(file, exchange)
                entries.append(
                    {
                        key: exchange[key]
                        for key in ("tool_id", "tool_fingerprint", "stage", "benchmark_commit")
                    }
                )
                entries[-1].update(
                    kind="probe",
                    path=file.name,
                    sha256=hashlib.sha256(file.read_bytes()).hexdigest(),
                )
                attempt.update(status="recorded", observation=check_result(result, row["check"]))
        write_json(output / "evidence.json", {"version": VERSION, "entries": entries})
        audit["status"] = "recorded"
    except BaseException as exc:
        audit.update(status="failed", error_type=type(exc).__name__)
        raise
    finally:
        audit["seconds"] = perf_counter() - started
        write_json(output / "probe-audit.json", audit)
    return audit

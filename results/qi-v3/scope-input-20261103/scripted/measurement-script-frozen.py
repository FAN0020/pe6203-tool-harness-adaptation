"""Frozen V3 before/after updater input diagnostic; no benchmark actor or judge.

Default uses scripted responses and measures exact input characters/UTF-8 bytes.
--live uses the fixed real model/provider and provider-reported token/cost usage.
No trajectory, answer, or score enters the updater. Every attempt is retained.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import subprocess
from decimal import Decimal
from pathlib import Path
from types import ModuleType

from openai import OpenAI

from integration import baselines as provider
from pe6203 import capability
from pe6203.benchmark import digest, write_json
from pe6203.costs import provider_usd

BASELINE = "b94d51226324e3eac70e5fe873a5be51e9cd8df1"
MODEL = "deepseek/deepseek-v4.1-flash-1017"
ROUTING = {
    "provider": {"only": ["DigitalOcean"], "allow_fallbacks": False, "require_parameters": True},
    "reasoning": {"enabled": False},
}
RULE = "Pass the balance service result directly as amount without conversion."
NEW_RULE = "Convert the supplied amount from cents to dollars by dividing by 100 before display."


def catalogs(n, program_only=False):
    def tool(name, description, rules=()):
        return {
            "tool_id": "server::" + name,
            "server_id": "server",
            "version": "early",
            "name": name,
            "description": description,
            "usage_rules": list(rules),
            "output_schema": None,
            "routing": {"server_id": "server", "tool_name": name},
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number"},
                    **{
                        f"option_{i}": {
                            "type": "string",
                            "description": "An unrelated optional string selector. Preserve its literal value; no implicit transformation.",
                        }
                        for i in range(8)
                    },
                },
                "required": ["amount"],
                "additionalProperties": False,
            },
        }

    records = [
        tool("fetch_balance", "Returns the account balance for the display panel in dollars.")
    ]
    if not program_only:
        records.append(
            tool(
                "display",
                "Displays the account balance supplied by the balance service. The amount input is in dollars.",
                [RULE],
            )
        )
    records += [
        tool(
            f"store_{i:03}",
            "Stores an unrelated numeric measurement. It does not consume balances or financial amounts.",
            ["Preserve the original measurement. Labels do not change its value."],
        )
        for i in range(n - len(records))
    ]
    old = {
        "schema_version": "1.0",
        "benchmark_commit": "synthetic-fixture",
        "version": "early",
        "tools": records,
    }
    target = copy.deepcopy(old)
    target["version"] = "late"
    for t in target["tools"]:
        t["version"] = "late"
        t["usage_rules"] = []
    if program_only:
        t = target["tools"][0]
        t["parameters"]["properties"]["strict"] = {"type": "boolean"}
        t["parameters"]["required"].append("strict")
    else:
        target["tools"][0]["description"] = (
            "Returns the account balance for the display panel in cents."
        )
    bundle = {
        "version": "capability-evidence-v1",
        "entries": [
            {
                "tool_id": t["tool_id"],
                "tool_fingerprint": capability.fingerprint(t),
                "kind": "catalog",
                "quote": t["description"],
            }
            for t in target["tools"]
        ],
    }
    return old, target, bundle


def evidence():
    return [
        {
            "tool_id": "server::fetch_balance",
            "side": "target",
            "field": "description",
            "quote": "Returns the account balance for the display panel in cents.",
        },
        {"tool_id": "server::display", "side": "old", "field": "usage_rules", "quote": RULE},
    ]


def scripted(payload):
    if payload.get("phase") == "scope_screen":
        ids = [r["tool_id"] for r in payload["directory"]]
        return {
            "screened_tool_ids": ids,
            "candidates": [
                {
                    "tool_id": "server::display",
                    "classification": "potential_impact",
                    "basis": ["c1"],
                    "reason": "Implicit balance-unit dependency.",
                }
            ]
            if "server::display" in ids
            else [],
        }
    if payload.get("phase") == "local_semantic_review":
        return {
            "decisions": [
                {
                    "tool_id": r["tool_id"],
                    "action": "update",
                    "reason": "Replace stale unit rule.",
                    "basis": ["c1"],
                    "evidence": evidence(),
                    "usage_rules": [NEW_RULE],
                }
                for r in payload["records"]
            ]
        }
    if "candidates" in payload:
        return {
            "decisions": [
                {
                    "tool_id": r["tool_id"],
                    "action": "update" if r["tool_id"] == "server::display" else "keep",
                    "reason": "Unit impact."
                    if r["tool_id"] == "server::display"
                    else "No local edit needed.",
                    "basis": ["c1"] if r["tool_id"] == "server::display" else [],
                    "evidence": evidence() if r["tool_id"] == "server::display" else [],
                }
                for r in payload["candidates"]
            ]
        }
    return {
        "patches": [
            {
                "tool_id": r["patched_record"]["tool_id"],
                "usage_rules": [NEW_RULE],
                "reason": "Update units.",
                "basis": ["c1"],
                "evidence": evidence(),
                "unresolved": False,
            }
            for r in payload["selected"]
        ]
    }


def checks(result, old, target, program_only):
    knowledge = result["knowledge"]
    orig = {t["tool_id"]: t for t in old["tools"]}
    actual = {t["tool_id"]: t for t in knowledge["tools"]}
    validations = {
        "program_validation": not result["audit"]["validation"]["errors"],
        "capability_boundary_all_records": all(
            t["capability_boundary"]["status"] == "literal_evidence_only"
            for t in knowledge["tools"]
        ),
    }
    for t in knowledge["tools"]:
        authoritative = next(x for x in target["tools"] if x["tool_id"] == t["tool_id"])
        for field in ("name", "description", "parameters", "routing", "output_schema"):
            validations[f"{t['tool_id']}:{field}_protected"] = t[field] == authoritative[field]
        if t["tool_id"] not in ("server::display",):
            validations[f"{t['tool_id']}:rules_preserved"] = (
                t["usage_rules"] == orig[t["tool_id"]]["usage_rules"]
            )
    if not program_only:
        rules = actual["server::display"]["usage_rules"]
        validations["obsolete_rule_withdrawn"] = RULE not in rules
        validations["updated_unit_rule"] = any(
            "100" in r and "cent" in r.lower() and "dollar" in r.lower() for r in rules
        )
    return validations


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    source = subprocess.check_output(
        ["git", "show", f"{BASELINE}:src/pe6203/capability.py"], text=True
    )
    (out / "baseline-capability.py").write_text(source)
    oldmodule = ModuleType("pe6203._before_v3_scope")
    oldmodule.__file__ = str(out / "baseline-capability.py")
    exec(compile(source, oldmodule.__file__, "exec"), oldmodule.__dict__)
    settings = {
        "model": MODEL,
        "temperature": 0.0,
        "max_tokens": 16384,
        "timeout": 120,
        "api_key_env": "AGENT_API_KEY",
        "base_url_env": "AGENT_BASE_URL",
        "allow_metadata_api": True,
        "request_retry": {"max_retries": 0},
    }
    if args.live:
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise ValueError("OPENROUTER_API_KEY missing")
        os.environ["AGENT_API_KEY"] = key
        os.environ["AGENT_BASE_URL"] = "https://openrouter.ai/api/v1"
    cases = [
        ("program_only", 1, True),
        ("implicit_3", 3, False),
        ("implicit_12", 12, False),
        ("implicit_42", 42, False),
    ]
    # Freeze all cases, source identities, model/provider and criteria before requests.
    inputs = {name: catalogs(n, program) for name, n, program in cases}
    for name, data in inputs.items():
        for field, value in zip(("old", "target", "capability-evidence"), data, strict=True):
            write_json(out / name / (field + ".json"), value)
    files = [
        "src/pe6203/capability.py",
        "src/pe6203/hybrid_selective.py",
        "src/pe6203/scope_v3.py",
        "src/pe6203/scoped_selective_v3.py",
        "scripts/measure_v3_scope.py",
    ]
    write_json(
        out / "freeze.json",
        {
            "baseline_commit": BASELINE,
            "new_source_sha256": {
                p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in files
            },
            "inputs_sha256": {name: digest(value) for name, value in inputs.items()},
            "settings": settings,
            "routing": ROUTING,
            "criteria": [
                "metadata exact",
                "obsolete rule removed",
                "updated units",
                "unrelated rules preserved",
                "literal capability boundaries retained",
            ],
            "mode": "real_updater_only" if args.live else "scripted_exact_characters_only",
            "budget_usd": 0.5,
            "implicit_live_sizes": [3, 42],
            "retries": 0,
            "actor_judge_runs": 0,
        },
    )
    receipts = []
    spent = Decimal("0")
    stopped = False
    summaries = []
    try:
        for name, n, program_only in cases:
            if args.live and n == 12:
                continue
            old, target, bundle = inputs[name]
            pair = {}
            results = {}
            for label, engine in [("before", oldmodule), ("after", capability)]:
                directory = out / name / label
                directory.mkdir()
                requests = []

                def request(messages, config):
                    nonlocal spent, stopped
                    if stopped or spent >= Decimal(".5"):
                        raise RuntimeError("Receipt/budget guard stopped requests")
                    index = len(requests) + 1
                    requests.append(copy.deepcopy(messages))
                    write_json(directory / f"request-{index:02}.json", messages)
                    if args.live:
                        try:
                            with OpenAI(
                                api_key=os.environ["AGENT_API_KEY"],
                                base_url=os.environ["AGENT_BASE_URL"],
                                timeout=config["timeout"],
                                max_retries=0,
                            ) as client:
                                packed = client.chat.completions.create(
                                    model=MODEL,
                                    messages=messages,
                                    temperature=0,
                                    max_tokens=config["max_tokens"],
                                    response_format={"type": "json_object"},
                                    extra_body=ROUTING,
                                ).model_dump(mode="json")
                        except BaseException:
                            stopped = True
                            receipts.append(
                                {
                                    "case": name,
                                    "engine": label,
                                    "call": index,
                                    "usd": None,
                                    "error": "request_failed_usage_unknown",
                                }
                            )
                            raise
                        charge = provider_usd(packed.get("usage") or {})
                        receipt = {
                            "case": name,
                            "engine": label,
                            "call": index,
                            "id": packed.get("id"),
                            "model": packed.get("model"),
                            "provider": packed.get("provider"),
                            "usage": packed.get("usage"),
                            "usd": charge,
                        }
                        receipts.append(receipt)
                        if (
                            charge is None
                            or receipt["provider"] != "DigitalOcean"
                            or receipt["model"] != MODEL
                        ):
                            stopped = True
                        if charge is not None:
                            spent += Decimal(str(charge))
                    else:
                        packed = {
                            "choices": [
                                {
                                    "finish_reason": "stop",
                                    "message": {
                                        "content": json.dumps(
                                            scripted(json.loads(messages[-1]["content"]))
                                        )
                                    },
                                }
                            ],
                            "usage": {},
                        }
                    write_json(directory / f"response-{index:02}.json", packed)
                    write_json(
                        out / "live-receipts.json",
                        {
                            "receipts": receipts,
                            "known_usd": str(spent),
                            "unknown_charges": sum(r["usd"] is None for r in receipts),
                        },
                    )
                    return packed

                provider._request_completion = request
                context = {
                    "updater": settings,
                    "capability_evidence": bundle,
                    "audit_path": str(directory / "engine-audit.json"),
                }
                try:
                    result = engine.adapt_result(old, target, context)
                    results[label] = result
                    validation = checks(result, old, target, program_only)
                    write_json(directory / "knowledge.json", result["knowledge"])
                    write_json(directory / "updater-audit.json", result["audit"])
                    pair[label] = {
                        "status": "validated",
                        "calls": len(requests),
                        "input_characters": sum(len(m["content"]) for req in requests for m in req),
                        "input_utf8_bytes": sum(
                            len(m["content"].encode()) for req in requests for m in req
                        ),
                        "provider_input_tokens": result["cost"]["prompt_tokens"]
                        if args.live
                        else None,
                        "provider_output_tokens": result["cost"]["completion_tokens"]
                        if args.live
                        else None,
                        "provider_usd": result["cost"]["usd"] if args.live else None,
                        "checks": validation,
                        "all_checks": all(validation.values()),
                    }
                except Exception as exc:
                    audit = getattr(exc, "audit", {})
                    write_json(
                        directory / "failure.json",
                        {"error_type": type(exc).__name__, "error": str(exc), "audit": audit},
                    )
                    pair[label] = {
                        "status": "failed",
                        "calls": len(requests),
                        "input_characters": sum(len(m["content"]) for req in requests for m in req),
                        "provider_input_tokens": audit.get("cost", {}).get("prompt_tokens"),
                        "all_checks": False,
                    }
                if stopped:
                    break
            complete = len(pair) == 2 and all(
                v["status"] == "validated" and v["all_checks"] for v in pair.values()
            )
            summary = {
                "case": name,
                "records": n,
                "pair": pair,
                "complete_pair": complete,
                "scripted_knowledge_identical": digest(results["before"]["knowledge"])
                == digest(results["after"]["knowledge"])
                if complete and not args.live
                else None,
                "input_characters_reduction": 1
                - pair["after"]["input_characters"] / pair["before"]["input_characters"]
                if complete and pair["before"]["input_characters"]
                else None,
                "actual_input_tokens_reduction": 1
                - pair["after"]["provider_input_tokens"] / pair["before"]["provider_input_tokens"]
                if complete and args.live and pair["before"]["provider_input_tokens"]
                else None,
            }
            summaries.append(summary)
            write_json(
                out / "summary.json",
                {
                    "mode": "real_updater_only" if args.live else "scripted_input_characters_only",
                    "cases": summaries,
                    "known_usd": str(spent),
                    "benchmark_runs": 0,
                },
            )
            print(json.dumps({k: v for k, v in summary.items() if k != "pair"}), flush=True)
            if stopped:
                break
    finally:
        write_json(
            out / "live-receipts.json",
            {
                "receipts": receipts,
                "known_usd": str(spent),
                "unknown_charges": sum(r["usd"] is None for r in receipts),
            },
        )
    return 0 if all(s["complete_pair"] for s in summaries) and not stopped else 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Frozen, task-free before/after V5 input measurements.

Default: scripted semantic fixtures plus an explicitly labelled o200k tokenizer
proxy, not DeepSeek usage. --live uses the real same model/provider, no retries,
and stops on unknown billing/transport failure. No actor or benchmark is run.
"""

import argparse
import copy
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

from integration import baselines as provider
from pe6203 import selective_v5
from pe6203.benchmark import digest, write_json

BASELINE = "a97a599790f076b6a48c2e023a7d538e196322f3"


def tool(name, description, rules=()):
    return {
        "tool_id": "server::" + name,
        "server_id": "server",
        "name": name,
        "version": "early",
        "description": description,
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {"type": "number", "description": "A finite numeric amount."},
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
        "output_schema": None,
        "usage_rules": list(rules),
        "routing": {"server_id": "server", "tool_name": name},
    }


def catalogs(n, *, explicit=False, program_only=False):
    records = [
        tool("fetch_balance", "Returns the account balance for the display panel in dollars.")
    ]
    if not program_only:
        records.append(
            tool(
                "display",
                "Displays the account balance supplied by the balance service. The input amount is in dollars.",
                [
                    "Pass fetch_balance output directly as amount without conversion."
                    if explicit
                    else "Pass the balance service result directly as amount without conversion."
                ],
            )
        )
    records += [
        tool(
            f"store_{i:03}",
            "Stores an unrelated numeric measurement with an optional label. It does not consume balances or financial amounts.",
            ["Preserve the original measurement. Optional labels do not change its value."],
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
        t["version"], t["usage_rules"] = "late", []
    if program_only:
        target["tools"][0]["parameters"]["properties"]["strict"] = {"type": "boolean"}
        target["tools"][0]["parameters"]["required"].append("strict")
    else:
        target["tools"][0]["description"] = (
            "Returns the account balance for the display panel in cents."
        )
    return old, target


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
                    "reason": "The balance consumer has implicit unit dependence.",
                }
            ]
            if "server::display" in ids
            else [],
        }
    sources = payload["evidence_registry"]
    refs = [
        k
        for k, v in sources.items()
        if v["kind"] == "catalog"
        and v["side"] == "target"
        and v["field"] == "description"
        and v["tool_id"] in {"server::fetch_balance", "server::display"}
    ]

    def decision(identity):
        affected = identity == "server::display"
        row = {
            "tool_id": identity,
            "action": "update" if affected else "keep",
            "reason": "Correct unit conversion." if affected else "No semantic rule change.",
            "basis": ["c1"] if affected else [],
            "evidence_ids": refs if affected else [],
        }
        return row

    def edit(identity):
        return {
            "tool_id": identity,
            "retain_rule_indices": [],
            "basis": ["c1"],
            "evidence_ids": refs,
            "reason": "Correct unit conversion.",
            "rules": [
                {
                    "kind": "guidance",
                    "text": "Convert cents to dollars before display.",
                    "evidence_ids": refs,
                }
            ],
        }

    if "candidates" in payload:
        return {"decisions": [decision(r["tool_id"]) for r in payload["candidates"]]}
    if "selected" in payload:
        return {"patches": [edit(r["patched_record"]["tool_id"]) for r in payload["selected"]]}
    return {
        "decisions": [
            {
                **decision(r["tool_id"]),
                **(edit(r["tool_id"]) if r["tool_id"] == "server::display" else {}),
            }
            for r in payload["records"]
        ]
    }


def original(root):
    raw = subprocess.check_output(
        ["git", "show", BASELINE + ":src/pe6203/selective_v5.py"], cwd=root
    )
    module = ModuleType("pe6203._frozen_v5_before_scope")
    module.__package__ = "pe6203"
    exec(compile(raw, "frozen-v5-before-scope", "exec"), module.__dict__)
    return module, hashlib.sha256(raw).hexdigest()


def semantic_checks(result, old, target):
    actual = {t["tool_id"]: t for t in result["knowledge"]["tools"]}
    old_tools = {t["tool_id"]: t for t in old["tools"]}
    metadata = all(
        all(
            actual[t["tool_id"]][k] == t[k]
            for k in ("description", "parameters", "routing", "name", "output_schema")
        )
        for t in target["tools"]
    )
    display = actual.get("server::display")
    return {
        "authoritative_metadata_exact": metadata,
        "known_implicit_consumer_selected": display is None
        or "server::display" in result["audit"]["semantic_impacted"],
        # Inspect retained rule entries, not a substring: a valid conflict can
        # quote the obsolete phrase specifically to warn against following it.
        "obsolete_direct_rule_withdrawn": display is None
        or not any(
            r in display["usage_rules"] for r in old_tools["server::display"]["usage_rules"]
        ),
        "unrelated_rules_preserved": all(
            t["usage_rules"] == old_tools[k]["usage_rules"]
            for k, t in actual.items()
            if k.startswith("server::store_")
        ),
        "no_duplicate_detailed_review": len(result["audit"].get("reviewed_tool_ids", []))
        == len(set(result["audit"].get("reviewed_tool_ids", []))),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--arm", choices=("both", "before", "after"), default="both")
    parser.add_argument(
        "--cases", nargs="+", help="Explicit task-free cases; recorded before calls"
    )
    parser.add_argument(
        "--continuation-of",
        type=Path,
        help="Prior frozen run directory; verify identical selected inputs, never rerun failed arm",
    )
    parser.add_argument(
        "--env", type=Path, help="Existing credential file; values never written to evidence"
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    args.output.mkdir(parents=True, exist_ok=False)
    before, source_hash = original(root)
    cases = {
        "program_only_1": catalogs(1, program_only=True),
        "implicit_3": catalogs(3),
        "implicit_12": catalogs(12),
        "implicit_42": catalogs(42),
        "explicit_42": catalogs(42, explicit=True),
    }
    if args.cases:
        cases = {k: cases[k] for k in args.cases}
    elif args.live:
        cases = {k: cases[k] for k in ("program_only_1", "implicit_42")}
    continuation = None
    if args.continuation_of:
        previous = json.loads((args.continuation_of / "frozen-cases.json").read_text())
        if any(digest(previous.get(k)) != digest(value) for k, value in cases.items()):
            raise ValueError("Continuation inputs differ from the predeclared frozen cases")
        if args.arm != "after":
            raise ValueError(
                "Continuation only completes the unrun after arm; failed before arm is immutable"
            )
        continuation = {
            "path": str(args.continuation_of),
            "freeze_sha256": hashlib.sha256(
                (args.continuation_of / "freeze.json").read_bytes()
            ).hexdigest(),
        }
    arms = [("before", before), ("after", selective_v5)]
    if args.arm != "both":
        arms = [(name, module) for name, module in arms if name == args.arm]
    write_json(args.output / "frozen-cases.json", cases)
    manifest = {
        "baseline_commit": BASELINE,
        "baseline_source_sha256": source_hash,
        "new_source_sha256": {
            str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (root / "src/pe6203/selective_v5.py", root / "src/pe6203/scope_v5.py")
        },
        "cases_sha256": digest(cases),
        "case_order": list(cases),
        "arm_order": [name for name, _ in arms],
        "continuation_of": continuation,
        "expected": "same metadata, implicit consumer updated, unrelated rules preserved; no task or benchmark answers",
        "live": args.live,
        "model": "deepseek/deepseek-v4.1-flash-1017" if args.live else "SCRIPTED",
        "provider": "DigitalOcean only, no fallback" if args.live else "local fixture",
        "transport_retries": 0,
        "max_calls_per_arm": 16,
        "token_measurement": "provider-reported prompt_tokens"
        if args.live
        else "tiktoken o200k_base proxy; NOT DeepSeek tokenization",
    }
    write_json(args.output / "freeze.json", manifest)
    encoder = None
    if not args.live:
        import tiktoken

        encoder = tiktoken.get_encoding("o200k_base")
        manifest["tiktoken_version"] = importlib.metadata.version("tiktoken")
        write_json(args.output / "freeze.json", manifest)
    if args.live:
        from dotenv import dotenv_values
        from openai import OpenAI

        data = dotenv_values(args.env) if args.env else {}
        key = os.environ.get("OPENROUTER_API_KEY") or data.get("OPENROUTER_API_KEY")
        if not key:
            raise RuntimeError("No configured OpenRouter key; no request made")
        client = OpenAI(
            api_key=key, base_url="https://openrouter.ai/api/v1", timeout=120, max_retries=0
        )
    else:
        client = None
    old_provider = provider._request_completion
    results = []
    try:
        for name, (old, target) in cases.items():
            pair = {}
            for arm, module in arms:
                output = args.output / name / arm
                output.mkdir(parents=True)
                requests = []

                def complete(messages, settings):
                    requests.append(copy.deepcopy(messages))
                    if client is not None:
                        wire = client.chat.completions.create(
                            model=manifest["model"],
                            messages=messages,
                            temperature=0,
                            max_tokens=4096,
                            response_format={"type": "json_object"},
                            extra_body={
                                "reasoning": {"enabled": False},
                                "provider": {
                                    "order": ["DigitalOcean"],
                                    "allow_fallbacks": False,
                                    "require_parameters": True,
                                },
                            },
                        ).model_dump(mode="json")
                        # Persist the response/usage BEFORE validating charge or model output.
                        write_json(output / f"response-{len(requests):02}.json", wire)
                        usage = wire.get("usage") or {}
                        if usage.get("cost") is None or wire.get("provider") != "DigitalOcean":
                            raise RuntimeError(
                                "Unknown charge/provider mismatch; stop without retries"
                            )
                        print(
                            json.dumps(
                                {
                                    "case": name,
                                    "arm": arm,
                                    "request": len(requests),
                                    "prompt_tokens": usage.get("prompt_tokens"),
                                    "usd": usage.get("cost"),
                                }
                            ),
                            flush=True,
                        )
                        return wire
                    return {
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
                        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "cost": 0.0},
                    }

                provider._request_completion = complete
                try:
                    result = module.adapt_result(
                        old,
                        target,
                        {
                            "selective_mode": "hybrid_v5",
                            "audit_path": str(output / "audit.json"),
                            "updater": {
                                "allow_metadata_api": True,
                                "model": manifest["model"],
                                "timeout": 120,
                            },
                        },
                    )
                    checks = semantic_checks(result, old, target)
                    write_json(output / "knowledge.json", result["knowledge"])
                    proxy = (
                        None
                        if encoder is None
                        else sum(len(encoder.encode(m["content"])) for req in requests for m in req)
                    )
                    measure = {
                        "calls": len(requests),
                        "input_characters": sum(len(m["content"]) for req in requests for m in req),
                        "input_utf8_bytes": sum(
                            len(m["content"].encode()) for req in requests for m in req
                        ),
                        "input_tokens": result["cost"]["prompt_tokens"] if args.live else proxy,
                        "reported_model_usd": result["cost"]["usd"] if args.live else None,
                        "checks": checks,
                        "knowledge_sha256": digest(result["knowledge"]),
                    }
                    pair[arm] = measure
                    write_json(output / "measure.json", measure)
                    if not all(checks.values()):
                        raise RuntimeError(
                            "Known semantic/protection check failed; retain evidence, no resampling"
                        )
                except Exception as exc:
                    write_json(
                        output / "failure.json",
                        {
                            "status": "failed",
                            "error_type": type(exc).__name__,
                            "error": exc.audit.get("error")
                            if hasattr(exc, "audit")
                            else "Retained failure; no retry",
                            "cost": exc.audit.get("cost") if hasattr(exc, "audit") else None,
                        },
                    )
                    raise
                finally:
                    write_json(output / "requests.json", requests)
            pair["case"] = name
            if args.arm == "both":
                b, a = pair["before"]["input_tokens"], pair["after"]["input_tokens"]
                pair["input_token_reduction_fraction"] = None if b == 0 else 1 - a / b
            results.append(pair)
            write_json(args.output / "results.json", results)
    finally:
        provider._request_completion = old_provider
        if client is not None:
            client.close()
    summary = {
        "live": args.live,
        "measurement": manifest["token_measurement"],
        "cases": results,
        "benchmark_runs": 0,
        "actor_calls": 0,
        "semantic_recall_proven": False,
        "all_known_checks_passed": True,
    }
    write_json(args.output / "summary.json", summary)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

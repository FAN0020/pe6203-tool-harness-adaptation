"""Freeze task-independent evidence and an explicit shared artifact protocol.

No benchmark answers, trajectories or judge feedback are read. Original questions
are hashed for fidelity; only execution sees them. All probes precede scored runs.
"""

import asyncio
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from pe6203.benchmark import digest, load_task, read_json, source, write_json
from pe6203.evidence_v5 import collect_probes

HERE = Path(__file__).resolve().parent
ROOT = Path("/Users/q/Desktop/tool-selective_patch/V5")
V3 = Path("/Users/q/Desktop/tool-selective_patch/V3")
INSTALLED = Path(
    "/Users/q/.codex/.chatgpt-projects/g-p-6a731461688481918939646b5d12604b/outputs/mcpevol-install-20261103/catalogs"
)
IMAGE = "python@sha256:e697c81897302a4c4333bade000d98038fbb21eb064f8ee1fd42d02ebcd9d337"
STAGES = ["early", "middle", "late"]
TASKS = [133, 235, 283]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def v3_fingerprint(tool):
    return digest(
        {
            k: tool.get(k)
            for k in ("tool_id", "description", "parameters", "output_schema", "routing")
        }
    )


async def main():
    inputs = HERE / "inputs"
    inputs.mkdir(exist_ok=False)
    lock, upstream = source(ROOT)
    for task in TASKS:
        dest = inputs / "catalogs" / str(task)
        dest.mkdir(parents=True)
        for stage in STAGES:
            shutil.copy2(INSTALLED / f"task{task}-{stage}.json", dest / f"{stage}.json")
    for stage in STAGES:
        for task in [133, 283]:
            catalog_path = inputs / "catalogs" / str(task) / f"{stage}.json"
            catalog = read_json(catalog_path)
            tools = {t["name"]: t for t in catalog["tools"]}
            calls = []
            if task == 133:
                props = tools["validate_syntax"]["parameters"]["properties"]
                args = {"expression": "(8 + 4) / 3"}
                if "allow_variables" in props:
                    args["allow_variables"] = False
                calls.append(
                    {
                        "tool_id": tools["validate_syntax"]["tool_id"],
                        "arguments": args,
                        "check": {
                            "pointer": "/content/0/text",
                            "operator": "contains",
                            "expected": "valid",
                        },
                    }
                )
                calls.append(
                    {
                        "tool_id": tools["evaluate"]["tool_id"],
                        "arguments": {"expression": "(8 + 4) / 3"},
                        "check": {"pointer": "/isError", "operator": "equals", "expected": False},
                    }
                )
                if "max_depth" in props:
                    calls.append(
                        {
                            "tool_id": tools["validate_syntax"]["tool_id"],
                            "arguments": {
                                "expression": "(((3)))",
                                "allow_variables": False,
                                "max_depth": 1,
                            },
                            "check": {
                                "pointer": "/content/0/text",
                                "operator": "contains",
                                "expected": "invalid",
                            },
                        }
                    )
            else:
                calls.append(
                    {
                        "tool_id": tools["create_project"]["tool_id"],
                        "arguments": {
                            "workingDirectory": "{workspace}",
                            "name": "Independent contract probe",
                            "description": "Predeclared generic tool capability observation, not a scored task.",
                        },
                        "check": {"pointer": "/isError", "operator": "equals", "expected": False},
                    }
                )
            plan_path = inputs / f"probe-plan-{task}-{stage}.json"
            write_json(
                plan_path,
                {
                    "version": "selective-probes-v5",
                    "reviewed": True,
                    "catalog": f"catalogs/{task}/{stage}.json",
                    "timeout_seconds": 15,
                    "probes": calls,
                },
            )
            await collect_probes(ROOT, plan_path, inputs / "probes" / str(task) / stage)
            print(
                json.dumps({"probe_plan_completed": f"{task}-{stage}", "calls": len(calls)}),
                flush=True,
            )
    # Convert the same literal exchanges into V3's documented four-field format.
    for task in TASKS:
        for stage in STAGES:
            catalog = read_json(inputs / "catalogs" / str(task) / f"{stage}.json")
            tools = {t["tool_id"]: t for t in catalog["tools"]}
            dest = inputs / "v3-evidence" / str(task) / stage
            dest.mkdir(parents=True)
            entries = []
            for tool in tools.values():
                if tool["description"].strip():
                    entries.append(
                        {
                            "tool_id": tool["tool_id"],
                            "tool_fingerprint": v3_fingerprint(tool),
                            "kind": "catalog",
                            "quote": tool["description"][:1000],
                        }
                    )
            v5_bundle = inputs / "probes" / str(task) / stage / "evidence.json"
            if v5_bundle.exists():
                for i, entry in enumerate(read_json(v5_bundle)["entries"]):
                    original_path = v5_bundle.parent / entry["path"]
                    original = read_json(original_path)
                    exchange = {
                        "tool_id": original["tool_id"],
                        "tool_fingerprint": v3_fingerprint(tools[original["tool_id"]]),
                        "arguments": original["arguments"],
                        "result": original["result"],
                    }
                    p = dest / f"probe-{i}.json"
                    write_json(p, exchange)
                    assert len(p.read_text()) <= 4000
                    entries.append(
                        {
                            "tool_id": exchange["tool_id"],
                            "tool_fingerprint": exchange["tool_fingerprint"],
                            "kind": "probe",
                            "path": p.name,
                            "sha256": sha(p),
                            "quote": p.read_text(),
                        }
                    )
            write_json(
                dest / "evidence.json", {"version": "capability-evidence-v1", "entries": entries}
            )
    tests = [
        {
            "id": "numeric-precedence",
            "kind": "benign",
            "source": "from artifact import safe_eval\nassert abs(safe_eval('2 + 6 * 3') - 20) < 1e-9\nassert abs(safe_eval('((9 - 3) / 2)') - 3) < 1e-9",
        },
        {
            "id": "unary-and-decimals",
            "kind": "benign",
            "source": "from artifact import safe_eval\nassert abs(safe_eval('-4 + 1.5') + 2.5) < 1e-9",
        },
        {
            "id": "reject-code-and-attributes",
            "kind": "negative",
            "source": "from artifact import safe_eval\nfor expression in [\"__import__('os').getpid()\", '().__class__.__mro__', 'untrusted_name', '1;2']:\n try:\n  safe_eval(expression)\n except (ValueError, TypeError, SyntaxError, NameError):\n  pass\n else:\n  raise AssertionError('unsupported expression was accepted')",
        },
        {
            "id": "empty-and-wrong-type",
            "kind": "negative",
            "source": "from artifact import safe_eval\nfor expression in ['', None, 17]:\n try:\n  safe_eval(expression)\n except (ValueError, TypeError, SyntaxError):\n  pass\n else:\n  raise AssertionError('invalid input accepted')",
        },
        {
            "id": "bounded-input",
            "kind": "negative",
            "source": "from artifact import safe_eval\ntry:\n safe_eval('1+' * 600 + '1')\nexcept (ValueError, TypeError, SyntaxError):\n pass\nelse:\n raise AssertionError('input beyond the declared length limit accepted')",
        },
    ]
    write_json(
        inputs / "python-protocol.json",
        {
            "version": "artifact-v1",
            "image": IMAGE,
            "max_repairs": 1,
            "timeout_seconds": 3,
            "max_repair_tokens": 4096,
            "tests": tests,
        },
    )
    context = (
        "Additional common artifact-evaluation interface for this run: provide the final Python "
        "implementation with a public safe_eval(expression) function. It accepts strings of at most 1000 "
        "characters, supports numeric literals, parentheses, unary +/- and arithmetic +, -, *, /. "
        "Return a numeric result, and raise ValueError/TypeError/SyntaxError for unsupported or invalid "
        "inputs. Arbitrary identifiers, imports, attributes, strings and function calls are outside "
        "this evaluator contract. Put the security recommendations in the summary. "
        "This is an added deliverable/interface convention for finite artifact checking; it does not "
        "change the original benchmark question or assert complete security."
    )
    (inputs / "python-task-context.txt").write_text(context + "\n")
    for name in ["local-v5-execution.json", "local-v5-updater.json"]:
        shutil.copy2(ROOT / "configs" / name, inputs / name)
    plan = {
        "version": "v5-v3-controlled-evol-1",
        "order": ["V5", "V3", "no_update", "full_rewrite"],
        "tasks": TASKS,
        "stages": STAGES,
        "repeats": 1,
        "judge_slots": 5,
        "benchmark_commit": lock["commit"],
        "dataset_revision": lock["dataset_revision"],
        "question_hashes": {
            str(t): hashlib.sha256(load_task(upstream, t)["question"].encode()).hexdigest()
            for t in TASKS
        },
        "model": "deepseek/deepseek-v4.1-flash-1017",
        "provider": {"only": ["relace/fp4"], "allow_fallbacks": False, "require_parameters": True},
        "method_commits": {
            "V5": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "V3": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=V3, text=True).strip(),
        },
        "patch_budget": {"max_calls": 32, "max_request_chars": 200000},
        "shared_baselines_unmodified": True,
        "baselines_reused_across_selective_versions": True,
        "python_validation_only_for_selective": True,
        "comparison_scope": "full_system_not_pure_updater_effect",
        "artifact_protocol_is_task_extension": True,
        "probes_independent_of_answers_and_trajectories": True,
        "retry_policy": "No trajectory, semantic admission, low score or code-test failure reruns; native bounded transport/judge retries only; one artifact repair.",
        "spend_guard_usd": 5,
        "maximum_forwarded_requests": 1000,
        "limit_notes": [
            "Historical baselines are not pooled.",
            "Fixed order may affect caches; record cache tokens and normalized uncached API cost separately.",
            "One execution per cell; five judge slots are not five independent actor repeats.",
            "Finite artifact tests do not establish universal security; native server bugs remain.",
            "Baseline actor protocol has no new artifact contract/test/repair, as requested.",
        ],
        "files": {
            str(p.relative_to(HERE)): sha(p)
            for p in sorted(inputs.rglob("*"))
            if p.is_file() and "workspace" not in p.parts
        },
    }
    for label, root in [("V5", ROOT), ("V3", V3)]:
        plan.setdefault("source_files", {})[label] = {
            str(p.relative_to(root)): sha(p)
            for base in ["src/pe6203", "integration"]
            for p in sorted((root / base).rglob("*.py"))
        }
    write_json(HERE / "frozen-plan.json", plan)
    print(
        json.dumps(
            {
                "status": "inputs_frozen",
                "planned_executions": 36,
                "real_model_calls_in_preparation": 0,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    asyncio.run(main())

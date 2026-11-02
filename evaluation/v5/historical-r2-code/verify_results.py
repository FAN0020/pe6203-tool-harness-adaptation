"""Independent recomputation from receipts and saved native result artifacts."""

import hashlib
import json
from pathlib import Path

from dotenv import dotenv_values

from pe6203.benchmark import digest, load_task, source
from pe6203.judge import ecs

HERE = Path(__file__).resolve().parent
ROOT = Path("/Users/q/Desktop/tool-selective_patch/V5")


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    plan, summary = read(HERE / "frozen-plan.json"), read(HERE / "costs-and-results.json")
    records = [read(p) for p in sorted((HERE / "transport").glob("request-*.json"))]
    problems, reconciliations, artifact_checks, question_checks, environment_checks = (
        [],
        [],
        [],
        [],
        [],
    )
    for relative, expected in plan["files"].items():
        if sha(HERE / relative) != expected:
            problems.append("frozen input changed: " + relative)
    for label, directory in [
        ("V5", ROOT),
        ("V3", Path("/Users/q/Desktop/tool-selective_patch/V3")),
    ]:
        for relative, expected in plan["source_files"][label].items():
            if sha(directory / relative) != expected:
                problems.append("method source changed: " + label + "/" + relative)
    for request in records:
        body, response = request["request"], request.get("response") or {}
        if (
            body["provider"] != plan["provider"]
            or body["model"] != plan["model"]
            or body.get("reasoning") != {"enabled": False}
        ):
            problems.append("request protocol mismatch: " + str(request["index"]))
        if request.get("http_status") == 200 and response.get("provider") != "Relace":
            problems.append("provider mismatch: " + str(request["index"]))
        reasoned = (response.get("usage", {}).get("completion_tokens_details") or {}).get(
            "reasoning_tokens"
        )
        if reasoned not in (None, 0):
            problems.append("reasoning unexpectedly billed: " + str(request["index"]))
    _, upstream = source(ROOT)
    for arm in plan["order"]:
        for stage in plan["stages"]:
            for task in plan["tasks"]:
                cell = HERE / "cells" / arm / f"task{task}-{stage}-r0"
                name = f"{arm}/task{task}-{stage}-r0"
                if not (cell / "cell.json").exists():
                    continue
                state = read(cell / "cell.json")
                if state["status"] == "started":
                    continue
                own = [r for r in records if r["cell"] == name]
                adaptation = read(cell / "adaptation/adaptation.json")
                updater = [r for r in own if r["phase"] == "updater"]
                usds = [r.get("response", {}).get("usage", {}).get("cost") for r in updater]
                native = adaptation.get("cost", {}).get("usd")
                if all(type(x) in (int, float) for x in usds) and native is not None:
                    same = abs(sum(usds) - native) < 1e-9
                    reconciliations.append({"cell": name, "role": "updater", "passed": same})
                    if not same:
                        problems.append("native updater cost mismatch: " + name)
                if not (cell / "run/result.json").exists():
                    continue
                result = read(cell / "run/result.json")
                trace = read(cell / "run/raw_trace.json")
                question = load_task(upstream, task)["question"]
                ok = (
                    trace.get("question") == question
                    and hashlib.sha256(question.encode()).hexdigest()
                    == plan["question_hashes"][str(task)]
                )
                question_checks.append({"cell": name, "passed": ok})
                if not ok:
                    problems.append("question changed: " + name)
                for role, phases in [("agent", ["agent", "repair"]), ("judge", ["judge"])]:
                    usds = [
                        r.get("response", {}).get("usage", {}).get("cost")
                        for r in own
                        if r["phase"] in phases
                    ]
                    native = result.get("cost", {}).get(role, {}).get("usd")
                    if all(type(x) in (int, float) for x in usds) and native is not None:
                        same = abs(sum(usds) - native) < 1e-9
                        reconciliations.append({"cell": name, "role": role, "passed": same})
                        if not same:
                            problems.append("native role cost mismatch: " + name + "/" + role)
                expected = read(HERE / "inputs/catalogs" / str(task) / f"{stage}.json")
                actual = read(cell / "run/environment-metadata.json")
                ok = digest(expected) == digest(actual)
                environment_checks.append({"cell": name, "passed": ok})
                if not ok:
                    problems.append("environment metadata changed: " + name)
                audit = cell / "run/artifact-validation/audit.json"
                if audit.exists():
                    a = read(audit)
                    if a.get("accepted_artifact"):
                        accepted = a["accepted_artifact"]
                        ok = sha(audit.parent / accepted["path"]) == accepted["sha256"]
                        ok = ok and all(
                            x.get("isolated_execution") is True
                            for x in a["attempts"]
                            if x["status"] == "passed_finite_tests"
                        )
                        artifact_checks.append(
                            {
                                "cell": name,
                                "passed": ok,
                                "accepted_source_sha256": accepted["sha256"],
                            }
                        )
                        if not ok:
                            problems.append("accepted code hash/isolation mismatch: " + name)
    triplets = {}
    for arm, a in summary["arms"].items():
        triplets[arm] = {}
        for task in plan["tasks"]:
            cells = {r["stage"]: r["TF"] for r in a["cells"] if r["task_id"] == task}
            triplets[arm][str(task)] = (
                ecs(cells)
                if all(cells.get(s) is not None for s in plan["stages"])
                else {"status": "incomplete_triplet", "TF": cells}
            )
    # Never publish a key; test only the in-memory exact value against deliverables.
    key = dotenv_values(ROOT / ".env.v5")["V5_API_KEY"]
    for path in HERE.rglob("*"):
        if (
            path.is_file()
            and path.suffix in {".json", ".py", ".csv", ".md", ".txt"}
            and key in path.read_text(errors="replace")
        ):
            problems.append("credential found in deliverable: " + str(path.relative_to(HERE)))
    match_sets = [
        {
            (r["task_id"], r["stage"])
            for r in a["cells"]
            if r["TF"] is not None and r["PE"] is not None
        }
        for a in summary["arms"].values()
    ]
    matched = sorted(set.intersection(*match_sets))
    result = {
        "status": "passed" if not problems else "failed",
        "problems": problems,
        "terminal_cells": sum(a["terminal_cells"] for a in summary["arms"].values()),
        "planned": 36,
        "provider_requests_checked": len(records),
        "native_cost_reconciliations": reconciliations,
        "question_checks": question_checks,
        "environment_checks": environment_checks,
        "accepted_artifact_hash_and_isolation_checks": artifact_checks,
        "ecs_by_complete_task_triplet": triplets,
        "fully_matched_four_arm_conditions": matched,
        "credential_scan": "exact secret absent from all deliverables"
        if not any("credential found" in x for x in problems)
        else "failed",
    }
    (HERE / "verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                "verification": result["status"],
                "problems": problems,
                "terminal_cells": result["terminal_cells"],
                "provider_requests_checked": len(records),
                "cost_checks": len(reconciliations),
                "fully_matched_conditions": len(matched),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

"""Offline delivery audit: run from a clean clone with Python 3.12+ only.

Reconstructs the frozen corpus from committed archives into a temporary directory.
No provider calls, score writes, bootstrap, experiment restart or deployment.
"""

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import runpy
import socket
import sys
import tarfile
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
S = ROOT / "submission"
D = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text())


def canonical(tool):
    return {k: v for k, v in tool.items() if k != "version"}


def audit_main():
    spec = importlib.util.spec_from_file_location("arithmetic", S / "reproduce/recalculate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    archive = ROOT / "results/evidence/course-v1.3-20261031/raw-trial.tar.gz"
    metrics = module.audit(archive)
    assert metrics == read(S / "evidence/recomputed/metrics.json")
    prefix = module.PREFIX
    baseline, coverage = [], []
    with tarfile.open(archive) as tar:

        def get(name):
            return json.load(tar.extractfile(prefix + name))

        def catalog(task, stage):
            return {t["tool_id"]: t for t in get(f"catalogs/{task}/{stage}.json")["tools"]}

        for task in module.TASKS:
            early = catalog(task, "early")
            for stage in module.STAGES:
                target = catalog(task, stage)
                base = f"cells/task{task}-{stage}-full_rewrite-r0/"
                knowledge = get(base + "adaptation/knowledge.json")
                rewritten = {t["tool_id"]: t for t in knowledge["tools"]}
                assert set(target) == set(rewritten)
                if stage == "early":
                    assert rewritten == early
                    assert get(base + "adaptation/adaptation.json")["cost"]["calls"] == 0
                    continue
                audit = get(base + "adaptation/updater-audit.json")
                payload = json.loads(audit["request"][-1]["content"])
                generated = json.loads(audit["response"]["choices"][0]["message"]["content"])
                output = {t["name"]: t for t in generated["tools"]}
                assert len(output) == len(generated["tools"]) == len(target)
                assert set(output) == set(target)
                assert set(payload) == {"tools", "rewrite_checks"}
                for tool_id, record in target.items():
                    assert rewritten[tool_id]["description"] == output[tool_id]["description"]
                    assert output[tool_id]["usage_rules"] == record["usage_rules"]
                    assert {k: v for k, v in rewritten[tool_id].items() if k != "description"} == {
                        k: v for k, v in record.items() if k != "description"
                    }
                baseline.append(
                    {
                        "task": task,
                        "stage": stage,
                        "target_tools": len(target),
                        "generated_descriptions": len(output),
                        "descriptions_textually_changed": sum(
                            rewritten[k]["description"] != target[k]["description"] for k in target
                        ),
                        "all_other_fields_equal_target": True,
                        "settings": audit["settings"],
                        "evidence": prefix + base + "adaptation/updater-audit.json",
                    }
                )
                calls, observations = {}, {}
                for method in module.METHODS:
                    trace = get(f"cells/task{task}-{stage}-{method}-r0/run/raw_trace.json")
                    knowledge = get(f"cells/task{task}-{stage}-{method}-r0/run/knowledge.json")
                    names = {
                        re.sub(r"[^a-zA-Z0-9_-]", "_", tool["name"])[:50]
                        + "__"
                        + sha(tool["tool_id"].encode())[:12]: tool["tool_id"]
                        for tool in knowledge["tools"]
                    }
                    assert set(names) == {t["function"]["name"] for t in trace["involved_tools"]}
                    called = Counter(
                        names[e["call"]["function"]["name"]]
                        for e in trace["events"]
                        if e["type"] == "tool_result"
                    )
                    calls[method] = called
                    observations[method] = defaultdict(list)
                    for event in trace["events"]:
                        if event["type"] == "tool_result":
                            observations[method][names[event["call"]["function"]["name"]]].append(
                                {
                                    "round": event["round"],
                                    "arguments_raw": event["call"]["function"]["arguments"],
                                    "observation": event["result"],
                                }
                            )
                for tool_id in sorted(set(early) | set(target)):
                    old, new = early.get(tool_id), target.get(tool_id)
                    if old is None:
                        types, fields = ["TOOL"], ["tool_added"]
                    elif new is None:
                        types, fields = ["TOOL"], ["tool_removed"]
                    else:
                        fields = [
                            k
                            for k in sorted(set(old) | set(new))
                            if k != "version" and old.get(k) != new.get(k)
                        ]
                        types = []
                        if "parameters" in fields:
                            types.append("PARAM")
                        if "description" in fields:
                            types.append("DESC")
                    if not fields:
                        continue
                    coverage.append(
                        {
                            "task": task,
                            "transition": "early_to_" + stage,
                            "tool_id": tool_id,
                            "types": types,
                            "changed_fields": fields,
                            "calls_by_method": {m: calls[m][tool_id] for m in module.METHODS},
                            "observed_calls": {m: observations[m][tool_id] for m in module.METHODS},
                            "before": canonical(old) if old else None,
                            "after": canonical(new) if new else None,
                        }
                    )
            assert all(
                catalog(235, s).keys() == catalog(235, "early").keys() for s in module.STAGES
            )
        for stage in module.STAGES:
            assert {k: canonical(v) for k, v in catalog(235, stage).items()} == {
                k: canonical(v) for k, v in catalog(235, "early").items()
            }
    return {
        "metrics_identical": True,
        "selective_PE": metrics["selective_PE"],
        "full_rewrite": baseline,
        "coverage": coverage,
        "retention_metadata_unchanged": True,
    }


def restore_corpus(destination):
    manifest = read(S / "evidence/corpus-manifest.json")
    pending = defaultdict(list)
    for item in manifest:
        path = ROOT / item["path"]
        if path.is_file() and sha(path.read_bytes()) == item["sha256"]:
            output = destination / item["path"]
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(path.read_bytes())
        else:
            pending[item["sha256"]].append(item)
    archives = (
        read(S / "evidence/history-manifest.json") + read(D / "extra-manifest.json")["archives"]
    )
    for record in archives:
        archive = ROOT / record["path"]
        assert sha(archive.read_bytes()) == record["sha256"], record["path"]
        with tarfile.open(archive) as tar:
            for member in tar:
                if not member.isfile():
                    continue
                data = tar.extractfile(member).read()
                for item in pending.pop(sha(data), []):
                    output = destination / item["path"]
                    output.parent.mkdir(parents=True, exist_ok=True)
                    output.write_bytes(data)
    assert not pending, (
        f"Missing original files: {[item['path'] for items in pending.values() for item in items]}"
    )
    for item in manifest:
        assert sha((destination / item["path"]).read_bytes()) == item["sha256"]
    return len(manifest)


def run_script(path, arguments):
    saved = sys.argv
    sys.argv = [str(path), *arguments]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            runpy.run_path(str(path), run_name="__main__")
    finally:
        sys.argv = saved


def audit_history(directory):
    corpus, out = directory / "corpus", directory / "history-recomputed"
    count = restore_corpus(corpus)
    os.environ["PE6203_EVIDENCE_ROOT"] = str(corpus)
    os.environ["PE6203_AUDIT_OUTPUT"] = str(out)
    sys.path.insert(0, str(S / "reproduce"))
    run_script(S / "reproduce/screen_trajectories.py", [])
    run_script(S / "reproduce/audit_cases.py", [])
    actual, expected = read(out / "failure-cases.json"), read(S / "evidence/failure-cases.json")
    for key in ["candidate_count", "candidate_classification_counts", "case_studies"]:
        assert actual[key] == expected[key], key
    assert read(out / "diagnostic-review.json") == read(S / "evidence/diagnostic-review.json")
    return {
        "corpus_files": count,
        "candidate_count": actual["candidate_count"],
        "candidate_classifications": actual["candidate_classification_counts"],
        "deep_case_studies": len(actual["case_studies"]),
        "six_negative_diagnostics_preserved": True,
    }


def audit_diagnostics(directory):
    folder = S / "diagnostics-20261031"
    archive = S / "evidence/targeted-diagnostics-20261031.tar.gz"
    expected_archive = next(
        x for x in read(folder / "SHA256SUMS.json") if x["path"] == "raw.tar.gz"
    )
    assert sha(archive.read_bytes()) == expected_archive["sha256"]
    raw = directory / "diagnostics"
    with tarfile.open(archive) as tar:
        tar.extractall(raw, filter="data")
    for item in read(folder / "raw-manifest.json"):
        assert sha((raw / item["path"]).read_bytes()) == item["sha256"]
    out = directory / "diagnostics-recomputed"
    run_script(
        folder / "audit.py",
        ["--raw", str(raw / "raw"), "--output", str(out), "--skip-prior-evidence"],
    )
    actual, expected = read(out / "audit.json"), read(folder / "audit.json")
    assert expected.pop("prior_evidence_members_unchanged") == 10959
    assert actual.pop("prior_evidence_members_unchanged") is None
    assert actual == expected
    return {"trajectories": 4, "ratings": 20, "recalculation_identical": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    def blocked(*a, **kw):
        raise RuntimeError("Network disabled during offline delivery audit")

    socket.socket = blocked
    socket.create_connection = blocked
    socket.getaddrinfo = blocked
    for key in list(os.environ):
        if any(token in key for token in ("API_KEY", "AUTH_TOKEN", "ACCESS_TOKEN")):
            os.environ.pop(key, None)
    with tempfile.TemporaryDirectory(prefix="pe6203-delivery-audit-") as temporary:
        directory = Path(temporary)
        result = {
            "main": audit_main(),
            "history": audit_history(directory),
            "diagnostics": audit_diagnostics(directory),
            "network": "disabled",
            "new_model_calls": 0,
            "historical_scores_modified": False,
        }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": "passed",
                "main_cells": 27,
                "main_ratings": 135,
                "corpus_files": result["history"]["corpus_files"],
                "diagnostic_trajectories": 4,
                "network": "disabled",
                "model_calls": 0,
            }
        )
    )


if __name__ == "__main__":
    main()

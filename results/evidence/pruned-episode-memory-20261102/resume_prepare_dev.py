"""Freeze exact admitted state-linked knowledge and all original paired cases."""

import hashlib
import json
import random
import shutil
import tarfile
from pathlib import Path

from pe6203.benchmark import read_json, write_json
from pe6203.experiment import freeze_files, sha
from pe6203.pruned_episode_memory import compile_knowledge
from pe6203.runner import prepare_tools
from pe6203.selective import adapt_result
from pe6203.strategy_search import build, check_knowledge, review

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / "results/raw/pruned-episode-memory-pilot-20261102"


def main():
    assert read_json(HERE / "semantic-review.json")["accepted"]
    assert OUT.exists() and not list(OUT.glob("cells/*/run/raw_trace.json"))
    plan = read_json(OUT / "plan.json")
    expected_endpoints = read_json(ROOT / "results/raw/relational-probe-memory-pilot-20261102/plan.json")["endpoints"]
    assert all(v is None for v in plan["endpoints"].values())
    plan["endpoints"] = expected_endpoints
    plan["files"] = freeze_files(ROOT, [ROOT/n for n in plan["files"]])
    assert plan["cells"] == read_json(HERE / "execution-schedule.json")["development"]
    suite = read_json(ROOT / "experiments/benchmark-v1.3.json")
    for task in plan["tasks"]:
        expected = next(t for t in suite["tasks"] if t["task_id"] == task["idx"])
        assert hashlib.sha256(task["question"].encode()).hexdigest() == expected["question_sha256"]
    for name, value in suite["catalog_sha256"].items():
        assert sha(OUT / name) == value
    extra = [p for p in HERE.glob("*") if p.is_file() and p.suffix in {".py", ".json"}]
    extra += [
        ROOT / "tests/test_pruned_episode_memory.py",
        ROOT / "experiments/benchmark-v1.3.json",
    ]
    extra += [
        ROOT / p
        for p in read_json(HERE / "native-freeze.json")["files"]
        if p.startswith(".cache/")
    ]
    plan["files"].update(freeze_files(ROOT, extra))
    write_json(OUT / "plan.json", plan)
    (OUT / "plan.sha256").write_text(sha(OUT / "plan.json") + "\n")
    build(ROOT, OUT)
    feedback = read_json(OUT / "feedback.json")["observations"]
    audit = []
    for task, stage in [
        (133, "middle"),
        (133, "late"),
        (283, "middle"),
        (283, "late"),
        (235, "late"),
    ]:
        old = read_json(OUT / f"catalogs/{task}/early.json")
        target = read_json(OUT / f"catalogs/{task}/{stage}.json")
        base = adapt_result(old, target)
        bp = OUT / f"adaptations/{task}-{stage}-selective_patch/knowledge.json"
        cp = OUT / f"adaptations/{task}-{stage}-pruned_episode_memory/knowledge.json"
        baseline, candidate = read_json(bp), read_json(cp)
        assert baseline == base["knowledge"]
        expected, edits = compile_knowledge(base, target, feedback)
        assert candidate == expected
        if task == 283:
            assert len(edits) == 1
        else:
            assert not edits and candidate == baseline
        bt, br = prepare_tools(baseline["tools"], "selective_patch", "namespaced")
        ct, cr = prepare_tools(candidate["tools"], "pruned_episode_memory", "namespaced")
        assert br == cr and len(bt) == len(ct)
        for a, b in zip(baseline["tools"], candidate["tools"], strict=True):
            b = dict(b)
            b["usage_rules"] = a["usage_rules"]
            assert a == b
        audit.append(
            {
                "task_id": task,
                "stage": stage,
                "edits": edits,
                "SP_sha256": sha(bp),
                "candidate_sha256": sha(cp),
                "SP_model_tool_chars": len(json.dumps(bt, ensure_ascii=False)),
                "candidate_model_tool_chars": len(json.dumps(ct, ensure_ascii=False)),
            }
        )
    write_json(HERE / "knowledge-audit.json", audit)
    review(
        OUT,
        "All6pre-registerednativecounterfactuals passed full-state equivalence;17nativecalls,0newupdatercalls. Both originaltask-freeLLMsequences reduce to2writecalls;terminalnames/IDs/links witnessed. Only changedcreate_project usage_rules;133/235exactSP, native/runtime/schema/orderprotected. Finite example not user-task completion proof.",
    )
    check_knowledge(OUT)
    order = [c["id"] for c in plan["cells"]]
    random.Random(20261107).shuffle(order)
    write_json(HERE / "blind-map.json", {f"R{i:02d}": c for i, c in enumerate(order, 1)})
    dest = HERE / "preexecution"
    dest.mkdir()
    for name in ["plan.json", "plan.sha256", "knowledge-lock.json", "knowledge-review.json"]:
        shutil.copyfile(OUT / name, dest / name)
    shutil.copytree(OUT / "adaptations", dest / "adaptations")
    archive = HERE / "source-prefreeze.tar.gz"
    with tarfile.open(archive, "w:gz") as t:
        for name in plan["files"]:
            t.add(ROOT / name, arcname=name, recursive=False)
    write_json(
        HERE / "prefreeze-manifest.json",
        {
            "archive": archive.name,
            "archive_sha256": sha(archive),
            "files": plan["files"],
            "model_calls": 0,
        },
    )
    print(
        json.dumps(
            {
                "cells": 10,
                "source_files": len(plan["files"]),
                "model_calls": 0,
                "knowledge_hash": sha(OUT / "knowledge-lock.json"),
            }
        )
    )


if __name__ == "__main__":
    main()

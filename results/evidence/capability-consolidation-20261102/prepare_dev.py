"""Freeze original full-subset paired development; zero updater requests."""
import hashlib
import json
import random
import shutil
from pathlib import Path

from pe6203.benchmark import read_json, write_json
from pe6203.capability_consolidation import compile_knowledge
from pe6203.experiment import freeze_files, sha
from pe6203.runner import prepare_tools
from pe6203.selective import adapt_result
from pe6203.strategy_search import build, check_knowledge, prepare_search, review

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / "results/raw/capability-consolidation-pilot-20261102"


def main():
    # Resume only this pre-model preparation after a missing credential check.
    # Existing generated knowledge or an experiment state makes this ineligible.
    if OUT.exists():
        assert not (OUT / "adaptations").exists()
        assert not (OUT / "experiment.json").exists()
        assert not (OUT / "knowledge-lock.json").exists()
        plan = read_json(OUT / "plan.json")
    else:
        plan = prepare_search(ROOT, OUT, "experiments/capability-consolidation-v1.json", "development")
    assert plan["cells"] == read_json(HERE / "execution-schedule.json")["development"]
    suite = read_json(ROOT / "experiments/benchmark-v1.3.json")
    for task in plan["tasks"]:
        expected = next(t for t in suite["tasks"] if t["task_id"] == task["idx"])
        assert hashlib.sha256(task["question"].encode()).hexdigest() == expected["question_sha256"]
    for name, value in suite["catalog_sha256"].items():
        assert sha(OUT / name) == value
    extra = [HERE / n for n in ["research-decision.json", "execution-schedule.json", "prepare_dev.py",
                               "run_model_trial.py", "collect_blind.py", "raw_cell_verifier.py", "credential-readiness.json"]]
    extra += [ROOT / n for n in ["tests/test_capability_consolidation.py", "experiments/benchmark-v1.3.json",
                                "results/evidence/capability-consolidation-20261102/native-plan.json", "results/evidence/capability-consolidation-20261102/native-result.json"]]
    extra += [ROOT / n for n in read_json(HERE / "native-plan.json")["files"]]
    plan["files"].update(freeze_files(ROOT, extra))
    write_json(OUT / "plan.json", plan)
    (OUT / "plan.sha256").write_text(sha(OUT / "plan.json") + "\n")
    build(ROOT, OUT)
    feedback = read_json(OUT / "feedback.json")["observations"]
    audit = []
    for task, stage in [(133,"middle"),(133,"late"),(283,"middle"),(283,"late"),(235,"late")]:
        old = read_json(OUT / f"catalogs/{task}/early.json")
        target = read_json(OUT / f"catalogs/{task}/{stage}.json")
        base = adapt_result(old, target)
        bp = OUT / f"adaptations/{task}-{stage}-selective_patch/knowledge.json"
        cp = OUT / f"adaptations/{task}-{stage}-capability_consolidation/knowledge.json"
        baseline, candidate = read_json(bp), read_json(cp)
        assert baseline == base["knowledge"]
        expected, edits = compile_knowledge(base, target, feedback)
        assert candidate == expected
        if task == 133:
            assert len(edits) == 2 and len(candidate["tools"]) == len(baseline["tools"]) - 1
        else:
            assert not edits and candidate == baseline
        bt, br = prepare_tools(baseline["tools"], "selective_patch", "namespaced")
        ct, cr = prepare_tools(candidate["tools"], "capability_consolidation", "namespaced")
        assert all(key in br and value == br[key] for key,value in cr.items())
        assert len(br) - len(cr) == (1 if task == 133 else 0)
        audit.append({"task_id":task,"stage":stage,"edits":edits,
                      "SP_sha256":sha(bp),"candidate_sha256":sha(cp),
                      "SP_model_tool_chars":len(json.dumps(bt,ensure_ascii=False)),
                      "candidate_model_tool_chars":len(json.dumps(ct,ensure_ascii=False))})
    write_json(HERE / "knowledge-audit.json", audit)
    review(OUT, "Source/nativecertifiedvalid-domainsubstitution:22matchedchecks,44calls. Onlychangedvalidate_syntax removed; existingevaluate usage_rules annotated;retainedschemas/routesandallotherfieldsprotected.283/235exactSP. Originalquestions/cataloghashesverified;newledger;90focusedtests passed. No efficacyclaim.")
    check_knowledge(OUT)
    order = [c["id"] for c in plan["cells"]]
    random.Random(20261104).shuffle(order)
    write_json(HERE / "blind-map.json", {f"R{i:02d}":c for i,c in enumerate(order,1)})
    dest = HERE / "preexecution"
    dest.mkdir()
    for name in ("plan.json","plan.sha256","knowledge-lock.json","knowledge-review.json"):
        shutil.copyfile(OUT/name,dest/name)
    shutil.copytree(OUT/"adaptations",dest/"adaptations")
    print(json.dumps({"model_calls":0,"cells":10,"source_files":len(plan["files"]),
                      "knowledge_lock_sha256":sha(OUT/"knowledge-lock.json"),"audit":audit}))


if __name__ == "__main__":
    main()

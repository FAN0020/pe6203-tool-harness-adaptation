"""Freeze original full-subset paired development; zero updater requests."""
import hashlib
import json
import random
import shutil
from pathlib import Path

from pe6203.benchmark import read_json, write_json
from pe6203.contract_evidence_encoding import compile_knowledge
from pe6203.experiment import freeze_files, sha
from pe6203.patch_variants import adapt_result as variant
from pe6203.runner import prepare_tools
from pe6203.selective import adapt_result
from pe6203.strategy_search import build, check_knowledge, prepare_search, review

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / "results/raw/evidence-contrastive-pilot-ready-20261102"


def main():
    # Resume only this pre-model preparation after a missing credential check.
    # Existing generated knowledge or an experiment state makes this ineligible.
    if OUT.exists():
        assert not (OUT / "adaptations").exists()
        assert not (OUT / "experiment.json").exists()
        assert not (OUT / "knowledge-lock.json").exists()
        plan = read_json(OUT / "plan.json")
    else:
        plan = prepare_search(ROOT, OUT, "experiments/evidence-contrastive-v1.json", "development")
    assert plan["cells"] == read_json(HERE / "execution-schedule.json")["development"]
    suite = read_json(ROOT / "experiments/benchmark-v1.3.json")
    for task in plan["tasks"]:
        expected = next(t for t in suite["tasks"] if t["task_id"] == task["idx"])
        assert hashlib.sha256(task["question"].encode()).hexdigest() == expected["question_sha256"]
    for name, value in suite["catalog_sha256"].items():
        assert sha(OUT / name) == value
    extra = [HERE / n for n in ["research-decision.json", "execution-schedule.json", "prepare_dev.py",
                               "run_model_trial.py", "collect_blind.py", "raw_cell_verifier.py", "credential-readiness.json"]]
    extra += [ROOT / n for n in ["tests/test_contract_evidence_encoding.py", "experiments/benchmark-v1.3.json",
                                "results/evidence/observed-contract-probes-20261031/mechanism-review.json"]]
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
        cp = OUT / f"adaptations/{task}-{stage}-observed_contrastive/knowledge.json"
        baseline, candidate = read_json(bp), read_json(cp)
        assert baseline == base["knowledge"]
        expected, edits = compile_knowledge(base, target, feedback, "contrastive")
        assert candidate == expected
        if task == 133:
            assert len(edits) == 1 and edits[0]["records"] == {"middle":7,"late":9}[stage]
        else:
            assert not edits and candidate == baseline
        historical = variant(old, target, "observed_contract", {"feedback": feedback})["knowledge"]
        bt, br = prepare_tools(baseline["tools"], "selective_patch", "namespaced")
        ct, cr = prepare_tools(candidate["tools"], "observed_contrastive", "namespaced")
        ht, hr = prepare_tools(historical["tools"], "observed_contract", "namespaced")
        assert br == cr == hr
        audit.append({"task_id":task,"stage":stage,"edits":edits,
                      "SP_sha256":sha(bp),"candidate_sha256":sha(cp),
                      "SP_model_tool_chars":len(json.dumps(bt,ensure_ascii=False)),
                      "candidate_model_tool_chars":len(json.dumps(ct,ensure_ascii=False)),
                      "historical_observed_contract_model_tool_chars":len(json.dumps(ht,ensure_ascii=False))})
    write_json(HERE / "knowledge-audit.json", audit)
    review(OUT, "Exact roundtrip of all frozen16 observations; same-expression argument deltas/shared outcomes, no semantic inference. Only133changedvalidate_syntaxusage_rules;283/235exactSP. Allschema/name/routes/otherrecords untouched. Originalquestions/catalogshashes verified; newledger. Focusedtests passed; native/model efficacy remains unproven.")
    check_knowledge(OUT)
    order = [c["id"] for c in plan["cells"]]
    random.Random(20261103).shuffle(order)
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

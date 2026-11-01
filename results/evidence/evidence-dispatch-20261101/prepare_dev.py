"""Freeze the whole evidence-dispatch candidate and ten original cells."""
import hashlib
import json
import os
import random
import shutil
from copy import deepcopy
from pathlib import Path
from pe6203.benchmark import read_json,write_json
from pe6203.experiment import freeze_files,sha
from pe6203.strategy_search import prepare_search,build,review,check_knowledge
from pe6203.semantic_contract_maintenance import frozen_patch
from pe6203.reviewed_coverage import compile_knowledge as compact
from pe6203.selective import adapt_result
from pe6203.runner import prepare_tools

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUT=ROOT/'results/raw/evidence-dispatch-pilot-20261101'

def main():
    assert not OUT.exists()
    assert all(os.environ.get(k) for k in ('AGENT_BASE_URL','JUDGE_BASE_URL','OPENROUTER_API_KEY_BACKUP'))
    plan=prepare_search(ROOT,OUT,'experiments/evidence-dispatch-v1.json','development')
    assert len(plan['cells'])==10 and all(plan['endpoints'].values())
    suite=read_json(ROOT/'experiments/benchmark-v1.3.json')
    for task in plan['tasks']:
        expected=next(x for x in suite['tasks'] if x['task_id']==task['idx'])
        assert hashlib.sha256(task['question'].encode()).hexdigest()==expected['question_sha256']
    for name,digest in suite['catalog_sha256'].items():assert sha(OUT/name)==digest
    extra=[HERE/name for name in ['research-decision.json','credential-readiness.json','prepare_dev.py','run_model_trial.py','collect_blind.py','archive.py','verify_development.py','raw_cell_verifier.py']]
    extra += [ROOT/p for p in [
        'experiments/benchmark-v1.3.json','tests/test_evidence_dispatch.py','tests/test_reviewed_coverage.py','tests/test_semantic_contract_maintenance.py',
        'tests/fixtures/dependency-cut-catalogs.json','tests/fixtures/semantic-maintenance-catalogs.json','tests/fixtures/prefix-workflow-catalogs.json',
        'experiments/semantic-claim-repair-feedback-v2.json','experiments/reviewed-coverage-feedback-v1.json',
        'results/evidence/semantic-claim-repair-20261101/semantic-review.json','results/evidence/semantic-claim-repair-20261101/updater-inputs.json',
        'results/evidence/semantic-claim-repair-20261101/middle-proposal.json','results/evidence/semantic-claim-repair-20261101/late-proposal.json',
        'results/evidence/semantic-contract-maintenance-20261101/review-decision.json',
        'results/evidence/reviewed-coverage-20261101/source-review.json','results/evidence/reviewed-coverage-20261101/research-decision.json',
        'results/evidence/method-learning-20261101/sources/amem/memory_layer.py','results/evidence/method-learning-20261101/sources/expel/agent/expel.py']]
    extra += [p for p in (ROOT/'results/evidence/description-factor-20261101/sources').rglob('*') if p.is_file()]
    extra += [ROOT/f'configs/evidence-dispatch-validation-{i}-v1.json' for i in (1,2)]
    for stage in ('iter3','iter5'):
        extra += list((ROOT/f'.cache/mcpevol/{stage}/node_modules/@pimzino/agentic-tools-mcp/dist').rglob('*.js'))
    plan['files'].update(freeze_files(ROOT,extra));write_json(OUT/'plan.json',plan)
    (OUT/'plan.sha256').write_text(sha(OUT/'plan.json')+'\n')
    build(ROOT,OUT)
    feedback=read_json(OUT/'feedback.json')['observations'];audit=[]
    for task,stage in [(133,'middle'),(133,'late'),(283,'middle'),(283,'late'),(235,'late')]:
        baseline=read_json(OUT/f'adaptations/{task}-{stage}-selective_patch/knowledge.json')
        candidate=read_json(OUT/f'adaptations/{task}-{stage}-evidence_dispatch/knowledge.json')
        old=read_json(OUT/f'catalogs/{task}/early.json');target=read_json(OUT/f'catalogs/{task}/{stage}.json')
        base=adapt_result(old,target);assert baseline==base['knowledge']
        before={t['tool_id']:t for t in baseline['tools']};after={t['tool_id']:t for t in candidate['tools']}
        changes=[k for k in before if before[k]!=after[k]];assert list(before)==list(after)
        if task==133:
            expected,edits=frozen_patch(old,target,feedback,False);assert candidate==expected
            assert len(edits)=={'middle':2,'late':8}[stage]
            restored=deepcopy(candidate)
            for e in edits:
                node=next(t for t in restored['tools'] if t['tool_id']==e['tool_id'])
                for k in e['path'].split('.')[:-1]:node=node[k]
                node[e['path'].split('.')[-1]]=e['before']
            assert restored==baseline
        elif task==283:
            expected,edits=compact(base,target,feedback);assert candidate==expected
            removed=sum(len(before[t['tool_id']]['description'])-len(t['description']) for t in candidate['tools'])
            assert removed=={'middle':546,'late':976}[stage] and removed>=500
        else:assert baseline==candidate and not changes
        bt,br=prepare_tools(baseline['tools'],'selective_patch','namespaced');ct,cr=prepare_tools(candidate['tools'],'evidence_dispatch','namespaced');assert br==cr
        audit.append(dict(task_id=task,stage=stage,changed_records=changes,SP_sha256=sha(OUT/f'adaptations/{task}-{stage}-selective_patch/knowledge.json'),candidate_sha256=sha(OUT/f'adaptations/{task}-{stage}-evidence_dispatch/knowledge.json'),SP_model_tool_json_characters=len(json.dumps(bt,ensure_ascii=False)),candidate_model_tool_json_characters=len(json.dumps(ct,ensure_ascii=False))))
    write_json(HERE/'knowledge-audit.json',audit)
    review(OUT,'Accepted exact reviewed source/probe claim-repair plus surviving-source coverage certificates.101 focused tests, including mixed catalog, protection and no task routing.133 uses unchanged2/8 prior claim edits;283 unchanged9/15 covered deletions;235 exactSP. No benchmark inputs/answers/scored traces enter compiler. Zero new updater calls; prior LLM generation USD0.0032346 separately disclosed. No actor runtime change; backup billing key uniformly selected before study.')
    check_knowledge(OUT)
    order=[c['id'] for c in plan['cells']];random.Random(80620).shuffle(order)
    write_json(HERE/'blind-map.json',{f'R{i:02d}':c for i,c in enumerate(order,1)})
    write_json(HERE/'review-protocol.json',dict(review_ids=[f'R{i:02d}' for i in range(1,11)],rubrics='experiments/evidence-dispatch-v1.json#quality_cases',all_reviews_before_scores_and_mapping=True,same_coordinator=True,independent_human=False,stdout_redirect=True))
    dest=HERE/'preexecution';dest.mkdir(exist_ok=False)
    for name in ('plan.json','plan.sha256','knowledge-lock.json','knowledge-review.json'):shutil.copyfile(OUT/name,dest/name)
    shutil.copytree(OUT/'adaptations',dest/'adaptations')
    print(json.dumps(dict(model_calls=0,cells=10,source_files=len(plan['files']),knowledge_lock_sha256=sha(OUT/'knowledge-lock.json'))))

if __name__=='__main__':main()

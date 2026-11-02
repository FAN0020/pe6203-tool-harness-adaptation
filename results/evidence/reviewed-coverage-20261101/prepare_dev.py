"""Prepare exactly ten original cases; lock knowledge before any model call."""
import hashlib
import json
import os
import random
import shutil
from pathlib import Path
from pe6203.benchmark import read_json,write_json
from pe6203.experiment import freeze_files,sha
from pe6203.strategy_search import prepare_search,build,review,check_knowledge

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUT=ROOT/'results/raw/reviewed-coverage-pilot-20261101'

def main():
    assert all(os.environ.get(k) for k in ('AGENT_BASE_URL','JUDGE_BASE_URL','AGENT_API_KEY','JUDGE_API_KEY')), 'Run with uv run --env-file .env'
    if OUT.exists():
        # Recover only the observed unstarted preparation, preserving its bytes.
        assert not (OUT/'adaptations').exists() and not (OUT/'cells').exists()
        plan=read_json(OUT/'plan.json')
        assert all(v is None for v in plan['endpoints'].values())
        previous=HERE/'initial-preparation-without-env';previous.mkdir(exist_ok=False)
        for name in ('plan.json','plan.sha256'):shutil.copyfile(OUT/name,previous/name)
        roles={'agent':plan['config']['agent'],'judge':plan['config']['judge'],'updater':plan['updater']}
        plan['endpoints']={role:os.environ.get(cfg['base_url_env']) for role,cfg in roles.items()}
    else:
        plan=prepare_search(ROOT,OUT,'experiments/reviewed-coverage-v1.json','development')
    assert len(plan['cells'])==10 and all(plan['endpoints'].values())
    suite=read_json(ROOT/'experiments/benchmark-v1.3.json')
    for task in plan['tasks']:
        expected=next(x for x in suite['tasks'] if x['task_id']==task['idx'])
        assert hashlib.sha256(task['question'].encode()).hexdigest()==expected['question_sha256']
    for name,digest in suite['catalog_sha256'].items(): assert sha(OUT/name)==digest
    extra=[HERE/name for name in ['research-decision.json','source-review.json','policy-hashes.json','prepare_candidate.py','prepare_dev.py','collect_blind.py','archive.py','verify_development.py','raw_cell_verifier.py']]
    extra += [ROOT/p for p in ['src/pe6203/reviewed_coverage.py','experiments/benchmark-v1.3.json','tests/test_reviewed_coverage.py','tests/fixtures/dependency-cut-catalogs.json']]
    extra += [p for p in (ROOT/'results/evidence/description-factor-20261101/sources').rglob('*') if p.is_file()]
    extra += [ROOT/f'configs/reviewed-coverage-validation-{i}-v1.json' for i in (1,2)]
    for stage in ('iter3','iter5'):
        extra += list((ROOT/f'.cache/mcpevol/{stage}/node_modules/@pimzino/agentic-tools-mcp/dist').rglob('*.js'))
    plan['files'].update(freeze_files(ROOT,extra));write_json(OUT/'plan.json',plan)
    (OUT/'plan.sha256').write_text(sha(OUT/'plan.json')+'\n')
    build(ROOT,OUT)
    audit=[]
    for task,stage in [(133,'middle'),(133,'late'),(283,'middle'),(283,'late'),(235,'late')]:
        baseline=read_json(OUT/f'adaptations/{task}-{stage}-selective_patch/knowledge.json')
        candidate=read_json(OUT/f'adaptations/{task}-{stage}-reviewed_coverage/knowledge.json')
        before={t['tool_id']:t for t in baseline['tools']};after={t['tool_id']:t for t in candidate['tools']}
        changes=[k for k in before if before[k]!=after[k]]
        assert list(before)==list(after)
        if task==283:
            from copy import deepcopy
            restored=deepcopy(candidate)
            removed=sum(len(before[t['tool_id']]['description'])-len(t['description']) for t in candidate['tools'])
            assert removed=={'middle':546,'late':976}[stage] and removed>=500
            assert len(json.dumps(candidate,ensure_ascii=False))<len(json.dumps(baseline,ensure_ascii=False))
            for t in restored['tools']:t['description']=before[t['tool_id']]['description']
            assert restored==baseline
            assert all(k.startswith('@modelcontextprotocol/server-sequential-thinking::') for k in changes)
        else: assert baseline==candidate and not changes
        audit.append(dict(task_id=task,stage=stage,changed_records=changes,
            SP_sha256=sha(OUT/f'adaptations/{task}-{stage}-selective_patch/knowledge.json'),
            candidate_sha256=sha(OUT/f'adaptations/{task}-{stage}-reviewed_coverage/knowledge.json')))
    write_json(HERE/'knowledge-audit.json',audit)
    review(OUT,'Accepted source-reviewed coverage certificates: 9/15 deletions, 546/976 characters; 114 focused tests passed. All schemas and source witnesses retained; only thinking descriptions in 283 differ; 133/235 exact SP. Researcher-authored known-contract policy, not an automated general semantic proof. No benchmark question, answer or scored trace enters updater. No actor runtime change. Zero updater API calls.')
    check_knowledge(OUT)
    order=[c['id'] for c in plan['cells']];random.Random(80619).shuffle(order)
    write_json(HERE/'blind-map.json',{f'R{i:02d}':c for i,c in enumerate(order,1)})
    write_json(HERE/'review-protocol.json',dict(review_ids=[f'R{i:02d}' for i in range(1,11)],rubrics='experiments/reviewed-coverage-v1.json#quality_cases',all_reviews_before_scores_and_mapping=True,same_coordinator=True,independent_human=False,stdout_redirect=True))
    dest=HERE/'preexecution';dest.mkdir(exist_ok=False)
    for name in ('plan.json','plan.sha256','knowledge-lock.json','knowledge-review.json'): shutil.copyfile(OUT/name,dest/name)
    shutil.copytree(OUT/'adaptations',dest/'adaptations')
    print(json.dumps(dict(model_calls=0,cells=10,source_files=len(plan['files']),knowledge_lock_sha256=sha(OUT/'knowledge-lock.json'))))

if __name__=='__main__': main()

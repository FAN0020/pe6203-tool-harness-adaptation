"""Freeze exact one-hop references and all ten original development cells."""
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
from pe6203.shared_contract_refs import compile_knowledge,expand_references
from pe6203.selective import adapt_result
from pe6203.runner import prepare_tools

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUT=ROOT/'results/raw/shared-contract-refs-pilot-20261101'


def main():
    assert not OUT.exists()
    assert all(os.environ.get(k) for k in ('AGENT_BASE_URL','JUDGE_BASE_URL','OPENROUTER_API_KEY_BACKUP'))
    plan=prepare_search(ROOT,OUT,'experiments/shared-contract-refs-v1.json','development')
    assert len(plan['cells'])==10 and all(plan['endpoints'].values())
    assert plan['cells']==read_json(HERE/'execution-schedule.json')['development']
    suite=read_json(ROOT/'experiments/benchmark-v1.3.json')
    for task in plan['tasks']:
        expected=next(x for x in suite['tasks'] if x['task_id']==task['idx'])
        assert hashlib.sha256(task['question'].encode()).hexdigest()==expected['question_sha256']
    for name,digest in suite['catalog_sha256'].items():assert sha(OUT/name)==digest
    extra=[HERE/n for n in ['research-decision.json','credential-readiness.json','execution-schedule.json','prepare_dev.py','run_model_trial.py','collect_blind.py','archive.py','verify_development.py','raw_cell_verifier.py','metadata-inventory.json']]
    extra += [ROOT/p for p in ['experiments/benchmark-v1.3.json','tests/test_shared_contract_refs.py','tests/test_active_contract_probing.py','tests/test_reviewed_coverage.py','tests/test_instruction_scope.py','tests/fixtures/dependency-cut-catalogs.json','tests/fixtures/semantic-maintenance-catalogs.json','tests/fixtures/prefix-workflow-catalogs.json','results/evidence/semantic-contract-maintenance-20261101/review-decision.json']]
    extra += list((HERE/'sources').iterdir())
    extra += [ROOT/f'configs/shared-contract-refs-validation-{i}-v1.json' for i in (1,2)]
    for iteration in ('iter3','iter5'):
        for package in ('@pimzino/agentic-tools-mcp','@modelcontextprotocol/server-sequential-thinking','math-mcp'):
            extra+=list((ROOT/f'.cache/mcpevol/{iteration}/node_modules/{package}/dist').rglob('*.js'))
    plan['files'].update(freeze_files(ROOT,extra));write_json(OUT/'plan.json',plan)
    (OUT/'plan.sha256').write_text(sha(OUT/'plan.json')+'\n')
    build(ROOT,OUT);audit=[]
    for task,stage in [(133,'middle'),(133,'late'),(283,'middle'),(283,'late'),(235,'late')]:
        baseline=read_json(OUT/f'adaptations/{task}-{stage}-selective_patch/knowledge.json')
        candidate=read_json(OUT/f'adaptations/{task}-{stage}-shared_contract_refs/knowledge.json')
        old=read_json(OUT/f'catalogs/{task}/early.json');target=read_json(OUT/f'catalogs/{task}/{stage}.json')
        assert baseline==adapt_result(old,target)['knowledge']
        expected,edits=compile_knowledge(old,target);assert candidate==expected
        assert expand_references(candidate,edits)==baseline
        if task==283:assert len(edits)=={'middle':1,'late':8}[stage]
        else:assert not edits and candidate==baseline
        bt,br=prepare_tools(baseline['tools'],'selective_patch','namespaced')
        ct,cr=prepare_tools(candidate['tools'],'shared_contract_refs','namespaced');assert br==cr
        byname={t['function']['name']:t['function'] for t in ct}
        for e in edits:assert byname[e['anchor_function']]['parameters']['properties'][e['parameter']]['description']==e['before']
        audit.append({'task_id':task,'stage':stage,'edits':edits,'SP_sha256':sha(OUT/f'adaptations/{task}-{stage}-selective_patch/knowledge.json'),'candidate_sha256':sha(OUT/f'adaptations/{task}-{stage}-shared_contract_refs/knowledge.json'),'SP_model_tool_json_characters':len(json.dumps(bt,ensure_ascii=False)),'candidate_model_tool_json_characters':len(json.dumps(ct,ensure_ascii=False))})
    write_json(HERE/'knowledge-audit.json',audit)
    review(OUT,'43 focused tests passed. Exact same-host/full-property/presence grouping; protected one-hop anchors; expansion recovers complete SP structure. Only changed parameter descriptions edited (283Middle1,Late8);133/235 exactSP. All model function names/routes/native constraints preserved. No benchmark question/answer/score input to compiler;0updater/nativebehaviorprobes. LLM reference resolution remains empirical, not proven by lossless expansion.')
    check_knowledge(OUT)
    order=[c['id'] for c in plan['cells']];random.Random(88913).shuffle(order)
    write_json(HERE/'blind-map.json',{f'R{i:02d}':c for i,c in enumerate(order,1)})
    write_json(HERE/'review-protocol.json',{'review_ids':[f'R{i:02d}' for i in range(1,11)],'rubrics':'experiments/shared-contract-refs-v1.json#quality_cases','all_reviews_before_scores_and_mapping':True,'same_coordinator':True,'independent_human':False,'stdout_redirect':True})
    dest=HERE/'preexecution';dest.mkdir(exist_ok=False)
    for name in ('plan.json','plan.sha256','knowledge-lock.json','knowledge-review.json'):shutil.copyfile(OUT/name,dest/name)
    shutil.copytree(OUT/'adaptations',dest/'adaptations')
    print(json.dumps({'model_calls':0,'cells':10,'source_files':len(plan['files']),'knowledge_lock_sha256':sha(OUT/'knowledge-lock.json')}))


if __name__=='__main__':main()

"""Prepare and lock exactly ten original benchmark cells; deterministic knowledge only."""
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
OUT=ROOT/'results/raw/observation-coverage-pilot-20261101'


def main():
    assert read_json(HERE/'native-decision.json')['admitted']
    if (OUT/'plan.json').exists():
        assert not (OUT/'experiment.json').exists() and not (OUT/'knowledge-lock.json').exists()
        assert not (OUT/'adaptations').exists()
        plan=read_json(OUT/'plan.json')
        assert all(v is None for v in plan['endpoints'].values())
        archive=HERE/'preparation-without-env';archive.mkdir(exist_ok=False)
        for name in ('plan.json','plan.sha256'):
            shutil.copyfile(OUT/name,archive/name)
        shutil.copyfile(HERE/'prepare.log',archive/'prepare.log')
        settings={'agent':plan['config']['agent'],'judge':plan['config']['judge'],'updater':plan['updater']}
        plan['endpoints']={role:os.environ[cfg['base_url_env']] for role,cfg in settings.items()}
        assert all(plan['endpoints'].values())
        write_json(archive/'correction.json',{'model_calls':0,'cause':'Initial local preparation omitted --env-file.env; build stopped at credentials check before any adaptation/modelcall.','correction':'Preserve original plan and failure; bind actual endpoint environment before final model freeze. Reuse unchanged catalogs,questions,config,schedule. No source or outcome resampling.'})
    else:
        plan=prepare_search(ROOT,OUT,'experiments/observation-coverage-v1.json','development')
    assert len(plan['cells'])==10
    suite=read_json(ROOT/'experiments/benchmark-v1.3.json')
    for task in plan['tasks']:
        expected=next(x for x in suite['tasks'] if x['task_id']==task['idx'])
        assert hashlib.sha256(task['question'].encode()).hexdigest()==expected['question_sha256']
    for name,digest in suite['catalog_sha256'].items():assert sha(OUT/name)==digest
    extra=[HERE/'research-decision.json',HERE/'native-decision.json',HERE/'run_native.py',HERE/'prepare_dev.py',HERE/'collect_blind.py',HERE/'archive.py',HERE/'verify_development.py',HERE/'raw_cell_verifier.py',ROOT/'experiments/observation-coverage-native-v1.json',ROOT/'experiments/benchmark-v1.3.json',ROOT/'tests/test_observation_coverage.py',ROOT/'tests/fixtures/dependency-cut-catalogs.json']
    extra += [p for p in (HERE/'sources').rglob('*') if p.is_file()]
    extra += [ROOT/f'configs/observation-coverage-validation-{i}-v1.json' for i in (1,2)]
    for stage in ('iter3','iter5'):
        extra += list((ROOT/f'.cache/mcpevol/{stage}/node_modules/@pimzino/agentic-tools-mcp/dist').rglob('*.js'))
    plan['files'].update(freeze_files(ROOT,extra));write_json(OUT/'plan.json',plan);(OUT/'plan.sha256').write_text(sha(OUT/'plan.json')+'\n')
    build(ROOT,OUT)
    audit=[]
    for task,stage in [(133,'middle'),(133,'late'),(283,'middle'),(283,'late'),(235,'late')]:
        baseline=read_json(OUT/f'adaptations/{task}-{stage}-selective_patch/knowledge.json')
        candidate=read_json(OUT/f'adaptations/{task}-{stage}-observation_coverage/knowledge.json')
        before={t['tool_id']:t for t in baseline['tools']};after={t['tool_id']:t for t in candidate['tools']}
        changes=[k for k in before if before[k]!=after[k]]
        assert list(before)==list(after)
        if task==283:
            assert changes==['@pimzino/agentic-tools-mcp::create_project']
            identity=changes[0];restored=dict(after[identity]);restored['description']=before[identity]['description'];assert restored==before[identity]
        else:assert baseline==candidate and not changes
        audit.append({'task_id':task,'stage':stage,'changed_records':changes,'SP_sha256':sha(OUT/f'adaptations/{task}-{stage}-selective_patch/knowledge.json'),'candidate_sha256':sha(OUT/f'adaptations/{task}-{stage}-observation_coverage/knowledge.json')})
    write_json(HERE/'knowledge-audit.json',audit)
    review(OUT,'Accepted source/native observation coverage certificate and exactfield conditions, bothstages. Onlyactualchangedproducerdescription differs;133/235exactSP. All30nativecallsandnegativecontrols retained. No benchmarkquestion,answer,scoredtrace or trainingepisode enters knowledge. No actor runtime change or fullPDDLplanner claim.')
    check_knowledge(OUT)
    order=[c['id'] for c in plan['cells']];random.Random(80617).shuffle(order)
    write_json(HERE/'blind-map.json',{f'O{i:02d}':c for i,c in enumerate(order,1)})
    write_json(HERE/'review-protocol.json',{'review_ids':[f'O{i:02d}' for i in range(1,11)],'rubrics':'experiments/observation-coverage-v1.json#quality_cases','all_reviews_before_scores_and_mapping':True,'same_coordinator':True,'independent_human':False,'stdout_redirect':True})
    dest=HERE/'preexecution';dest.mkdir(exist_ok=False)
    for name in ('plan.json','plan.sha256','knowledge-lock.json','knowledge-review.json'):shutil.copyfile(OUT/name,dest/name)
    shutil.copytree(OUT/'adaptations',dest/'adaptations')
    print(json.dumps({'model_calls':0,'cells':10,'source_files':len(plan['files']),'knowledge_lock_sha256':sha(OUT/'knowledge-lock.json')}))

if __name__=='__main__':main()

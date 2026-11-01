"""Prepare and lock exactly ten original benchmark cells; deterministic knowledge only."""
import hashlib
import json
import random
import shutil
from pathlib import Path
from pe6203.benchmark import read_json,write_json
from pe6203.experiment import freeze_files,sha
from pe6203.strategy_search import prepare_search,build,review,check_knowledge

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUT=ROOT/'results/raw/dependency-cut-pilot-20261101'


def main():
    assert read_json(HERE/'native-v2/native-decision.json')['admitted']
    plan=prepare_search(ROOT,OUT,'experiments/dependency-cut-v1.json','development')
    assert len(plan['cells'])==10
    suite=read_json(ROOT/'experiments/benchmark-v1.3.json')
    for task in plan['tasks']:
        expected=next(x for x in suite['tasks'] if x['task_id']==task['idx'])
        assert hashlib.sha256(task['question'].encode()).hexdigest()==expected['question_sha256']
    for name,digest in suite['catalog_sha256'].items():assert sha(OUT/name)==digest
    extra=[HERE/'research-decision.json',HERE/'native-v2/native-decision.json',HERE/'run_native.py',HERE/'run_native_v2.py',HERE/'prepare_dev.py',HERE/'collect_blind.py',ROOT/'experiments/dependency-cut-native-v1.json',ROOT/'experiments/dependency-cut-native-v2.json',ROOT/'experiments/benchmark-v1.3.json',ROOT/'tests/test_dependency_cut.py',ROOT/'tests/fixtures/dependency-cut-catalogs.json']
    extra += list((HERE/'sources').rglob('*.py'))+list((HERE/'sources').rglob('*.json'))
    extra += [ROOT/f'configs/dependency-cut-validation-{i}-v1.json' for i in (1,2)]
    for stage in ('iter3','iter5'):
        extra += list((ROOT/f'.cache/mcpevol/{stage}/node_modules/@pimzino/agentic-tools-mcp/dist').rglob('*.js'))
    plan['files'].update(freeze_files(ROOT,extra));write_json(OUT/'plan.json',plan);(OUT/'plan.sha256').write_text(sha(OUT/'plan.json')+'\n')
    build(ROOT,OUT)
    audit=[]
    for task,stage in [(133,'middle'),(133,'late'),(283,'middle'),(283,'late'),(235,'late')]:
        baseline=read_json(OUT/f'adaptations/{task}-{stage}-selective_patch/knowledge.json')
        candidate=read_json(OUT/f'adaptations/{task}-{stage}-dependency_cut/knowledge.json')
        before={t['tool_id']:t for t in baseline['tools']};after={t['tool_id']:t for t in candidate['tools']}
        changes=[k for k in before if before[k]!=after[k]]
        assert list(before)==list(after)
        if task==283:
            assert changes==['@pimzino/agentic-tools-mcp::create_project']
            identity=changes[0];restored=dict(after[identity]);restored['description']=before[identity]['description'];assert restored==before[identity]
        else:assert baseline==candidate and not changes
        audit.append({'task_id':task,'stage':stage,'changed_records':changes,'SP_sha256':sha(OUT/f'adaptations/{task}-{stage}-selective_patch/knowledge.json'),'candidate_sha256':sha(OUT/f'adaptations/{task}-{stage}-dependency_cut/knowledge.json')})
    write_json(HERE/'knowledge-audit.json',audit)
    review(OUT,'Accepted source/native certified dependency-cut graph, both stages. Only actualchangedproducer description differs;133/235exactSP. All nativev1 failures retained;v2correctiveinputfreeze independentlyverified. No benchmark question, answer, scored trace, synthetictraininganswer or updater supplied knowledge content.')
    check_knowledge(OUT)
    order=[c['id'] for c in plan['cells']];random.Random(80517).shuffle(order)
    write_json(HERE/'blind-map.json',{f'D{i:02d}':c for i,c in enumerate(order,1)})
    write_json(HERE/'review-protocol.json',{'review_ids':[f'D{i:02d}' for i in range(1,11)],'rubrics':'experiments/dependency-cut-v1.json#quality_cases','all_reviews_before_scores_and_mapping':True,'same_coordinator':True,'independent_human':False,'stdout_redirect':True})
    dest=HERE/'preexecution';dest.mkdir(exist_ok=False)
    for name in ('plan.json','plan.sha256','knowledge-lock.json','knowledge-review.json'):shutil.copyfile(OUT/name,dest/name)
    shutil.copytree(OUT/'adaptations',dest/'adaptations')
    print(json.dumps({'model_calls':0,'cells':10,'source_files':len(plan['files']),'knowledge_lock_sha256':sha(OUT/'knowledge-lock.json')}))

if __name__=='__main__':main()

"""Freeze all fifteen original development cells and both static knowledge views."""
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
from pe6203.instruction_scope import compile_knowledge
from pe6203.selective import adapt_result
from pe6203.runner import prepare_tools

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUT=ROOT/'results/raw/instruction-scope-pilot-20261101'


def main():
    assert not OUT.exists()
    assert all(os.environ.get(k) for k in ('AGENT_BASE_URL','JUDGE_BASE_URL','OPENROUTER_API_KEY_BACKUP'))
    plan=prepare_search(ROOT,OUT,'experiments/instruction-scope-v1.json','development')
    assert len(plan['cells'])==15 and all(plan['endpoints'].values())
    suite=read_json(ROOT/'experiments/benchmark-v1.3.json')
    for task in plan['tasks']:
        expected=next(x for x in suite['tasks'] if x['task_id']==task['idx'])
        assert hashlib.sha256(task['question'].encode()).hexdigest()==expected['question_sha256']
    for name,digest in suite['catalog_sha256'].items():assert sha(OUT/name)==digest
    extra=[HERE/name for name in ['research-decision.json','credential-readiness.json','prepare_policy.py','prepare_dev.py','run_model_trial.py','collect_blind.py','archive.py','verify_development.py','raw_cell_verifier.py']]
    extra += [ROOT/p for p in ['experiments/benchmark-v1.3.json','tests/test_instruction_scope.py','tests/test_reviewed_coverage.py','tests/test_evidence_dispatch.py','tests/fixtures/dependency-cut-catalogs.json','tests/fixtures/semantic-maintenance-catalogs.json','tests/fixtures/prefix-workflow-catalogs.json','experiments/thinking-contract-feedback-v1.json','results/evidence/semantic-contract-maintenance-20261101/review-decision.json','results/evidence/dead-argument-projection-20261101/native-evidence.tar.gz','results/evidence/dead-argument-projection-20261101/native-manifest.json','results/evidence/dead-argument-projection-20261101/reproduction.json']]
    extra += list((HERE/'sources').iterdir())
    extra += [ROOT/f'configs/instruction-scope-validation-{i}-v1.json' for i in (1,2)]
    for folder in ['iter3','iter5']:
        for package in ['@pimzino/agentic-tools-mcp','@modelcontextprotocol/server-sequential-thinking']:
            extra += list((ROOT/f'.cache/mcpevol/{folder}/node_modules/{package}/dist').rglob('*.js'))
    for row in read_json(ROOT/'experiments/instruction-scope-feedback-v1.json')['observations']:
        assert all(sha(ROOT/p)==v for p,v in row['result']['native_sources'].items())
    plan['files'].update(freeze_files(ROOT,extra));write_json(OUT/'plan.json',plan)
    (OUT/'plan.sha256').write_text(sha(OUT/'plan.json')+'\n')
    build(ROOT,OUT)
    feedback=read_json(OUT/'feedback.json')['observations'];audit=[]
    for task,stage in [(133,'middle'),(133,'late'),(283,'middle'),(283,'late'),(235,'late')]:
        baseline=read_json(OUT/f'adaptations/{task}-{stage}-selective_patch/knowledge.json')
        old=read_json(OUT/f'catalogs/{task}/early.json');target=read_json(OUT/f'catalogs/{task}/{stage}.json')
        base=adapt_result(old,target);assert baseline==base['knowledge']
        before={t['tool_id']:t for t in baseline['tools']}
        bt,br=prepare_tools(baseline['tools'],'selective_patch','namespaced')
        for arm in ['instruction_scope','instruction_scope_quote']:
            candidate=read_json(OUT/f'adaptations/{task}-{stage}-{arm}/knowledge.json')
            expected,edits=compile_knowledge(base,target,feedback,arm.endswith('_quote'));assert candidate==expected
            if task!=283:assert candidate==baseline and not edits
            else:assert len(edits)=={'middle':2,'late':3}[stage]
            restored=deepcopy(candidate)
            for t in restored['tools']:t['description']=before[t['tool_id']]['description']
            assert restored==baseline
            ct,cr=prepare_tools(candidate['tools'],arm,'namespaced');assert br==cr
            audit.append(dict(task_id=task,stage=stage,arm=arm,changed_records=[e['tool_id'] for e in edits],SP_sha256=sha(OUT/f'adaptations/{task}-{stage}-selective_patch/knowledge.json'),candidate_sha256=sha(OUT/f'adaptations/{task}-{stage}-{arm}/knowledge.json'),SP_model_tool_json_characters=len(json.dumps(bt,ensure_ascii=False)),candidate_model_tool_json_characters=len(json.dumps(ct,ensure_ascii=False))))
    write_json(HERE/'knowledge-audit.json',audit)
    review(OUT,'Source-reviewed operation facts plus verbatimparameter explanations; changedthinkingdescriptions only. Quotedcontrolpreservesallremovednarrative asquoteddata andisnoteligibleforpromotion.30focusedtests;133/235exactSP;schema/toolset/routing/order protected; noLLMornewnativecalls. Fixedactor/runtime/provider/judge/budgets. No benchmarkQ/A/scoredtraces incompiler.')
    check_knowledge(OUT)
    order=[c['id'] for c in plan['cells']];random.Random(73621).shuffle(order)
    write_json(HERE/'blind-map.json',{f'R{i:02d}':c for i,c in enumerate(order,1)})
    write_json(HERE/'review-protocol.json',dict(review_ids=[f'R{i:02d}' for i in range(1,16)],rubrics='experiments/instruction-scope-v1.json#quality_cases',all_reviews_before_scores_and_mapping=True,same_coordinator=True,independent_human=False,stdout_redirect=True))
    dest=HERE/'preexecution';dest.mkdir(exist_ok=False)
    for name in ('plan.json','plan.sha256','knowledge-lock.json','knowledge-review.json'):shutil.copyfile(OUT/name,dest/name)
    shutil.copytree(OUT/'adaptations',dest/'adaptations')
    print(json.dumps(dict(model_calls=0,cells=15,source_files=len(plan['files']),knowledge_lock_sha256=sha(OUT/'knowledge-lock.json'))))


if __name__=='__main__':main()

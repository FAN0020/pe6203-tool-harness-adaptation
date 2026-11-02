"""One authorized, separate official-rubric judge batch; never runs an actor."""
import argparse
import asyncio
import copy
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from pe6203.benchmark import read_json, write_json
from pe6203.evaluation import judge_scores
from pe6203.judge import save_once
from pe6203.runner import finish_judging

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check():
    plan = read_json(HERE/'freeze.json')
    assert sha(HERE/'freeze.json') == (HERE/'freeze.sha256').read_text().strip()
    for path, digest in plan['files'].items():
        assert sha(ROOT/path) == digest, f'Frozen input changed: {path}'
    checkpoint = read_json(ROOT/plan['source_run']/'execution-checkpoint.json')
    original = checkpoint['result']['config']
    for key in ('judge','judge_recovery','request_retry','request_timeout_seconds'):
        assert plan['config'][key] == original[key], key
    guard = copy.deepcopy(original['spend_guard'])
    guard['ledger'] = plan['config']['spend_guard']['ledger']
    assert guard == plan['config']['spend_guard'] and guard['limit_usd'] is None
    assert plan['source_cell'] == {'id':'cell-009','task_id':283,'version':'middle','strategy':'selective_patch','seed':0}
    assert len(checkpoint['prompts']) == 5
    for i, prompt in enumerate(checkpoint['prompts'], 1):
        assert prompt == (ROOT/plan['source_run']/f'judge-prompt-{i}.txt').read_text()
    assert not (ROOT/plan['output']).exists(), 'Supplement already attempted; no resampling'
    assert not Path(guard['ledger']).exists(), 'Supplement ledger already exists; do not reset it'
    authorization = read_json(HERE/'authorization.json')
    assert authorization['scope']=='only_missing_cell009_supplemental_five_slot_judge'
    assert authorization['user_answer']=='只补评缺失的 1 条'
    return plan, checkpoint


async def run(plan, checkpoint):
    key = os.environ.get('OPENROUTER_API_KEY_BACKUP')
    if not key:
        raise ValueError('OPENROUTER_API_KEY_BACKUP is required; no credential printed')
    os.environ['JUDGE_API_KEY'] = key
    os.environ['JUDGE_BASE_URL'] = plan['endpoint']
    output = ROOT/plan['output']
    output.mkdir(parents=True, exist_ok=False)
    cp = copy.deepcopy(checkpoint)
    cp['result']['config'].update(copy.deepcopy(plan['config']))
    cp['result']['supplemental_evaluation'] = {
        'source_run':plan['source_run'], 'source_cell':plan['source_cell'],
        'primary_experiment_unchanged':True, 'new_actor_calls':0,
        'inherited_actor_update_cost_is_not_new_spending':True,
        'independent_validation':False,
    }
    save_once(output/'execution-checkpoint.json',cp)
    save_once(output/'start.json',{'started_at':datetime.now(UTC).isoformat(),'freeze_sha256':sha(HERE/'freeze.json')})
    def emit(event):
        # Official visible judge output is preserved in immutable response files;
        # progress output contains no prompt, answer, credentials or model reasoning.
        with (output/'events.jsonl').open('a') as f:
            f.write(json.dumps({k:v for k,v in event.items() if k in ('type','run','attempt','failure_category')})+'\n')
        if event['type']=='judge_response_saved':
            print(json.dumps({'judge_slot':event['run'],'attempt':event['attempt'],'response_saved':True}),flush=True)
    result = await finish_judging(output,cp,emit)
    write_json(output/'result.json',result)
    ledger = read_json(ROOT/plan['config']['spend_guard']['ledger'])
    scores, problem = judge_scores(read_json(output/'EVAL/283.json'))
    original_unchanged=all(sha(ROOT/p)==h for p,h in plan['files'].items())
    assert original_unchanged
    providers_ok=all(r.get('actual_provider')=='DigitalOcean' and r.get('actual_model')==plan['config']['judge']['model'] for r in ledger['requests'] if r['status']=='settled')
    summary={
        'scope':'separate supplemental official-rubric evaluation of existing cell009',
        'source_cell':plan['source_cell'],'source_execution_status':checkpoint['result']['execution_status'],
        'status':result['judge_status'],'scores':scores,'score_issue':problem,
        'valid_slots':read_json(output/'EVAL/283.json')['eval_result']['aggregate']['successful_runs'],
        'requests':len(ledger['requests']),'known_usd':ledger['known_usd'],
        'unknown_requests':sum(r['status']=='unknown_charge' for r in ledger['requests']),
        'actual_provider_model_match':providers_ok,'original_files_unchanged':original_unchanged,
        'old_unknown_cost_preserved':True,'new_actor_calls':0,'new_updater_calls':0,
        'cell010_executed':False,'primary_scores_replaced':False,
        'independent_validation':False,'goal_complete':False,
        'historical_actor_and_updater_costs_not_recharged':True,
        'finished_at':datetime.now(UTC).isoformat(),
    }
    write_json(HERE/'result.json',summary)
    print(json.dumps(summary,ensure_ascii=False),flush=True)
    return 0 if not problem and providers_ok and not ledger['blocked'] else 2


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run',action='store_true')
    args=parser.parse_args()
    os.chdir(ROOT)
    plan,cp=check()
    if not args.run:
        print(json.dumps({'ready':True,'model_calls':0,'judge_slots':5,'original_input_files_verified':len(plan['files']),'new_actor_calls':0}))
        return 0
    return asyncio.run(run(plan,cp))


if __name__=='__main__':
    raise SystemExit(main())

"""Offline verification of the separate five-slot EvolBench supplement."""
import hashlib
import json
import re
import statistics
import tarfile
from decimal import Decimal
from pathlib import Path

HERE=Path(__file__).resolve().parent

def sha(b):
    return hashlib.sha256(b).hexdigest()

def read(p):
    return json.loads(p.read_text())

def unpack(name):
    m=read(HERE/(name+'-manifest.json'))
    a=HERE/m['archive']
    assert sha(a.read_bytes())==m['archive_sha256']
    with tarfile.open(a) as t:
        files={p.name:t.extractfile(p).read() for p in t if p.isfile()}
    assert {n:sha(v) for n,v in files.items()}==m['files']
    return files

def main():
    plan=read(HERE/'freeze.json')
    assert sha((HERE/'freeze.json').read_bytes())==(HERE/'freeze.sha256').read_text().strip()
    inputs=unpack('frozen-inputs')
    raw=unpack('supplement-raw')
    assert {n:sha(v) for n,v in inputs.items()}==plan['files']
    source=plan['source_run']+'/'
    output=plan['output']+'/'
    oldcp=json.loads(inputs[source+'execution-checkpoint.json'])
    newcp=json.loads(raw[output+'execution-checkpoint.json'])
    assert oldcp['trace']==newcp['trace'] and oldcp['prompts']==newcp['prompts']
    assert oldcp['result']['execution_status']=='max_rounds'
    assert newcp['result']['supplemental_evaluation']['new_actor_calls']==0
    cfg=newcp['result']['config']
    for k,v in plan['config'].items():assert cfg[k]==v
    manifest=json.loads(raw[output+'judge-plan.json'])
    assert manifest['prompts']==oldcp['prompts']
    assert manifest['judge']==plan['config']['judge']
    eval_=json.loads(raw[output+'EVAL/283.json'])['eval_result']
    assert eval_['protocol']=='durable-slots-v1'
    assert len(eval_['attempts'])==len(eval_['runs'])==5
    assert all(x['attempt']==1 for x in eval_['runs'])
    rows=[];ids=[];cost=Decimal(0)
    ledger=json.loads(raw[plan['config']['spend_guard']['ledger']])
    assert len(ledger['requests'])==5 and not ledger['blocked'] and Decimal(ledger['unknown_reserved_usd'])==0
    for i,selected in enumerate(eval_['runs'],1):
        base=output+f'judge-attempts/slot-{i}-attempt-1/'
        request=json.loads(raw[base+'request.json'])
        response=json.loads(raw[base+'response.json'])
        outcome=json.loads(raw[base+'outcome.json'])
        assert selected==outcome==eval_['attempts'][i-1]
        assert outcome['response']==response and selected['slot']==i
        assert request['prompt_sha256']==sha(json.dumps(oldcp['prompts'][i-1],sort_keys=True).encode())
        assert response['provider']=='DigitalOcean' and response['model']==cfg['judge']['model']
        assert response['choices'][0]['finish_reason']=='stop'
        parsed=json.loads(re.sub(r'^```(?:json)?\s*|\s*```$','',response['choices'][0]['message']['content'].strip()))
        assert parsed==outcome['result']
        for k in ('task_fulfillment','planning_and_efficiency','grounding'):
            assert type(parsed[k]) is int and 1<=parsed[k]<=10
        row=ledger['requests'][i-1]
        assert row['status']=='settled' and row['response_id']==response['id']
        assert row['actual_model']==response['model'] and row['actual_provider']==response['provider']
        settings={k:cfg['judge'][k] for k in ('model','temperature','max_completion_tokens','extra_body')}
        assert settings==request['settings']
        kwargs={'messages':[{'role':'user','content':oldcp['prompts'][i-1]}],**settings}
        assert row['request_sha256']==sha(json.dumps(kwargs,sort_keys=True).encode())
        amount=Decimal(str(response['usage']['cost']))
        assert amount==Decimal(row['actual_usd'])
        cost+=amount;ids.append(response['id'])
        rows.append({'slot':i,'TF':parsed['task_fulfillment'],'PE':parsed['planning_and_efficiency'],'grounding':parsed['grounding'],'usd':str(amount),'response_id':response['id']})
    assert len(set(ids))==5 and cost==Decimal(ledger['known_usd'])
    metrics={k:statistics.mean(r[k] for r in rows) for k in ('TF','PE','grounding')}
    for k,v in [('TF','task_fulfillment'),('PE','planning_and_efficiency'),('grounding','grounding')]:
        assert metrics[k]==eval_['aggregate'][v+'_mean']
    oldresult=json.loads(inputs[source+'result.json'])
    oldledger=json.loads(inputs['results/raw/relation-witness-basis-dev-costs-20261102/spend-ledger.json'])
    assert oldresult['TF'] is None and oldresult['PE'] is None and not oldresult['judge_recovery']['resumable']
    assert oldledger['blocked'] and oldledger['requests'][104]['status']=='unknown_charge'
    assert oldledger['requests'][104]['actual_usd'] is None and len(oldledger['requests'])==105
    saved=read(HERE/'result.json')
    assert metrics=={k:saved['scores'][k] for k in metrics} and saved['known_usd']==str(cost)
    out={'verified':True,'official_slots':5,'metrics':metrics,'known_usd':str(cost),'new_unknown_requests':0,
         'original_failure_and_unknown_preserved':True,'new_actor_calls':0,'cell010_run':False,
         'primary_score_replaced':False,'independent_validation':False,'goal_complete':False,
         'frozen_files_verified':len(inputs),'raw_files_verified':len(raw),'slots':rows}
    print(json.dumps(out,ensure_ascii=False,indent=2))

if __name__=='__main__':main()

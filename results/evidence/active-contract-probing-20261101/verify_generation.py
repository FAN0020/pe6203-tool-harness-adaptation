"""Offline arithmetic/provenance reproduction; no API/native/model calls or .cache needed."""
import hashlib
import json
from decimal import Decimal
from pathlib import Path
import tarfile
from pe6203.active_contract_probing import validate_probes,compile_decisions

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PREFIX=str(HERE.relative_to(ROOT))


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    blobs={};counts={}
    for manifest_path in [HERE/'pre-model-freeze.json',HERE/'generation-raw-manifest.json',HERE/'recovery/pre-model-freeze.json',HERE/'recovery-raw-manifest.json']:
        manifest=json.loads(manifest_path.read_text());archive=manifest_path.parent/manifest['archive']
        assert sha(archive.read_bytes())==manifest['archive_sha256']
        with tarfile.open(archive,'r:gz') as tf:
            members=[m for m in tf.getmembers() if m.isfile()]
            for member in members:
                data=tf.extractfile(member).read()
                assert sha(data)==manifest['files'][member.name],member.name
                if member.name in blobs:assert blobs[member.name]==data
                else:blobs[member.name]=data
            counts[str(archive.relative_to(HERE))]=len(members)
        assert all(name in blobs and sha(blobs[name])==digest for name,digest in manifest['files'].items())
    def get(name):return json.loads(blobs[name])
    original=get(PREFIX+'/generation-decision.json')
    final=get(PREFIX+'/recovery/decision.json')
    review=get(PREFIX+'/recovery/semantic-review.json')
    inputs=get(PREFIX+'/updater-inputs.json')
    plans=get(PREFIX+'/recovery/decoded-first-plans.json')
    total=Decimal(0);allids=set();request_count=0;tokens={'prompt':0,'completion':0}
    for name,folder,expected in [('active-contract-probing-generation-20261101',PREFIX,9),('active-contract-probing-recovery-20261101',PREFIX+'/recovery',4)]:
        ledger=get('results/raw/'+name+'/spend-ledger.json')
        responses=[]
        for path in blobs:
            if str(Path(path).parent)==folder and path.endswith('-audit.json'):
                responses.extend(a['response'] for a in get(path)['attempts'])
        assert len(responses)==expected==len(ledger['requests'])
        byid={r['id']:r for r in responses}
        assert len(byid)==expected and set(byid)=={r['response_id'] for r in ledger['requests']}
        assert not set(byid)&allids;allids.update(byid)
        subtotal=Decimal(0)
        for row in ledger['requests']:
            assert row['status']=='settled' and row['actual_provider']=='DigitalOcean'
            assert row['actual_model']=='deepseek/deepseek-v4.1-flash-1017'
            response=byid[row['response_id']];cost=Decimal(str(response['usage']['cost']))
            assert cost==Decimal(row['actual_usd']);subtotal+=cost
            tokens['prompt']+=response['usage']['prompt_tokens'];tokens['completion']+=response['usage']['completion_tokens']
        assert subtotal==Decimal(ledger['known_usd']) and Decimal(ledger['unknown_reserved_usd'])==0
        total+=subtotal;request_count+=expected
    assert request_count==13 and total==Decimal(final['total_cost_usd']) and tokens==final['tokens']
    native=0;edits=0
    bindings={**inputs['bindings'],'$WORKSPACE':'$WORKSPACE'}
    def bind(value):
        if isinstance(value,str):return bindings.get(value,value)
        if isinstance(value,list):return [bind(v) for v in value]
        if isinstance(value,dict):return {k:bind(v) for k,v in value.items()}
        return value
    for job in inputs['jobs']:
        data=job['data'];plan=plans[job['id']]
        first=get(PREFIX+'/'+job['id']+'-plan-audit.json')['attempts'][0]['response']
        first_plan=json.loads(first['choices'][0]['message']['content'])
        assert len(first_plan['probes'])==len(plan['probes'])
        for a,b in zip(first_plan['probes'],plan['probes'],strict=True):
            assert {k:v for k,v in a.items() if k!='basis'}=={k:v for k,v in b.items() if k!='basis'}
        validate_probes(data,plan)
        observations=get(PREFIX+'/recovery/'+job['id']+'-observations.json')
        assert len(observations)==len(plan['probes'])
        for proposal,receipt in zip(plan['probes'],observations,strict=True):
            assert receipt['id']==proposal['id'] and receipt['tool_id']==proposal['tool_id']
            assert receipt['arguments']==bind(proposal['arguments']) and receipt['attempts']==1
            path=PREFIX+'/recovery/native/'+job['id']+'/'+proposal['id']
            native_raw=get(path+'/observation.json')
            assert native_raw['before_state']==inputs['fixture']
            get(path+'/catalog.json')
        payload=get(PREFIX+'/recovery/'+job['id']+'-decisions.json')
        knowledge,changes=compile_decisions(data['old'],data['target'],data,payload,{p['id'] for p in observations})
        saved=get(PREFIX+'/recovery/'+job['id']+'-candidate.json')
        assert knowledge==saved['knowledge'] and changes==saved['edits']
        native+=len(observations);edits+=len(changes)
    assert native==14 and edits==9 and len(review['rows'])==9 and not review['admitted']
    failed=[r for r in review['rows'] if r['generation_rule_review']!='no_disqualifying_issue_identified']
    assert [(r['job'],r['claim_id']) for r in failed]==[('math-late','C007')]
    bad=next(e for e in get(PREFIX+'/recovery/math-late-candidate.json')['edits'] if e['id']=='C007')
    literal=plans['math-late']['probes'][2]['arguments']['expression']
    assert literal in bad['after']
    assert final['actor_calls']==final['judge_calls']==0 and not final['goal_complete']
    balance=get(PREFIX+'/recovery/balance-reconciled.json')
    assert balance['aggregate_matches'] and Decimal(balance['experiment_increment_usd'])==total
    result={'verified':True,'archive_member_counts':counts,'unique_frozen_and_raw_files':len(blobs),'requests':request_count,'cost_usd':str(total),'unknown_charges':0,'model_selected_native_calls':native,'setup_native_calls':4,'catalog_reads':18,'generated_edits':edits,'actor_calls':0,'judge_calls':0,'admitted':False,'goal_complete':False,'semantic_truth':'manual source/receipt review retained; this script verifies provenance/arithmetic/compilation and the decisive literal inclusion, not semantic correctness automatically'}
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()

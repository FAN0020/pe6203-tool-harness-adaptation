"""Offline frozen-source, actual product-review, score and cost verification."""
import json
import statistics
import tarfile
from decimal import Decimal
from pathlib import Path
from raw_cell_verifier import archive_files,inspect_cell,sha

HERE=Path(__file__).resolve().parent

def main():
    files,manifest=archive_files(HERE);prefix=manifest['prefix']+'/'
    def read(name):return json.loads(files[prefix+name])
    plan=read('plan.json');spec=plan['research']['spec']
    assert sha(files[prefix+'plan.json'])==files[prefix+'plan.sha256'].decode().strip()
    assert len(plan['cells'])==15
    assert {(c['task_id'],c['version'],c['strategy']) for c in plan['cells']}=={(t,s,a) for t,s in [(133,'middle'),(133,'late'),(283,'middle'),(283,'late'),(235,'late')] for a in ['selective_patch','instruction_scope','instruction_scope_quote']}
    sm=json.loads((HERE/'prefreeze-manifest.json').read_text());source_archive=HERE/sm['archive']
    assert sha(source_archive.read_bytes())==sm['archive_sha256']
    with tarfile.open(source_archive) as tf:source={m.name:tf.extractfile(m).read() for m in tf if m.isfile()}
    assert all(sha(source[k])==v for k,v in plan['files'].items())
    lock=read('knowledge-lock.json');assert lock['plan_sha256']==sha(files[prefix+'plan.json'])
    assert all(sha(files[prefix+k])==v for k,v in lock['files'].items())
    assert read('knowledge-review.json')['accepted'] and read('knowledge-review.json')['lock_sha256']==sha(files[prefix+'knowledge-lock.json'])
    state=read('experiment.json');assert len(state['cells'])==15 and all(x['status']=='evaluated' for x in state['cells'].values())
    for x in state['cells'].values():assert all(sha(files[prefix+k])==v for k,v in x['files'].items())
    mapping=json.loads((HERE/'blind-map.json').read_text());reverse={v:k for k,v in mapping.items()}
    freeze=json.loads((HERE/'review-freeze.json').read_text())
    assert freeze['all_reviews_before_scores']
    for k,v in freeze['files'].items():assert sha((HERE/k).read_bytes())==v
    rows=[];ids=[]
    for cell in plan['cells']:
        rid=reverse[cell['id']];review=json.loads((HERE/'blind-reviews'/f'{rid}.json').read_text());packet=json.loads((HERE/'blind-inputs'/f'{rid}.json').read_text())
        assert sha((HERE/'blind-inputs'/f'{rid}.json').read_bytes())==review['input_sha256']
        expected={x['id'] for x in next(x for x in spec['quality_cases'] if x['task_id']==cell['task_id'])['properties']}
        assert set(review['properties'])==expected and set(review['properties'].values())<={'pass','fail','unknown'}
        assert review['core_pass']==all(v=='pass' for v in review['properties'].values())
        for artifact in packet['artifacts']:
            assert sha(files[prefix+f"cells/{cell['id']}/run/workspace/"+artifact['path']])==artifact['sha256']
        row,response_ids=inspect_cell(files,prefix,cell,'original_benchmark_development');ids.extend(response_ids)
        row.update(review_id=rid,core_pass=review['core_pass'],properties=review['properties']);rows.append(row)
    for task,stage in [(133,'middle'),(133,'late'),(283,'middle'),(283,'late'),(235,'late')]:
        baseline=read(f'adaptations/{task}-{stage}-selective_patch/knowledge.json')
        feedback=json.loads(source['experiments/instruction-scope-feedback-v1.json'])['observations']
        for arm in ['instruction_scope','instruction_scope_quote']:
            candidate=read(f'adaptations/{task}-{stage}-{arm}/knowledge.json')
            if task!=283:
                assert candidate==baseline
                continue
            import copy
            expected=copy.deepcopy(baseline)
            cert=next(r['result'] for r in feedback if r['stage']==stage)
            assert len(cert['edits'])=={'middle':2,'late':3}[stage]
            native=read(f'catalogs/{task}/{stage}.json')
            for edit in cert['edits']:
                raw=next(t for t in native['tools'] if t['tool_id']==edit['tool_id'])
                assert sha(json.dumps(raw,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode())==edit['record_sha256']
                node=next(t for t in expected['tools'] if t['tool_id']==edit['tool_id'])
                assert node['description']==edit['before']
                node['description']=edit['quoted' if arm.endswith('_quote') else 'after']
                assert edit['parameters_block'] in node['description']
            assert expected==candidate
    metrics={}
    for a in ('selective_patch','instruction_scope','instruction_scope_quote'):
        metrics[a]={}
        for group,tasks in [('project',{283}),('changed',{133,283}),('retention',{235})]:
            rs=[r for r in rows if r['strategy']==a and r['task_id'] in tasks]
            metrics[a][group]={'n':len(rs),'completed':sum(r['execution_status']=='completed' for r in rs),'core_pass':sum(r['core_pass'] for r in rs),'TF':statistics.mean(r['TF'] for r in rs),'PE':statistics.mean(r['PE'] for r in rs)}
    b=metrics['selective_patch'];c=metrics['instruction_scope'];gates={}
    for group in ('project','changed'):
        for k in ('completed','core_pass'):gates[group+'_'+k+'_strict_gain']=c[group][k]>b[group][k]
        gates[group+'_TF_nondecrease']=c[group]['TF']>=b[group]['TF']
    gates['retention_nondecrease']=all(c['retention'][k]>=b['retention'][k] for k in ('completed','core_pass','TF'))
    ledger_path='results/raw/instruction-scope-dev-costs-20261101/spend-ledger.json';ledger=json.loads(files[ledger_path])
    assert ledger['policy']['limit_usd'] is None and not ledger['blocked'] and Decimal(ledger['unknown_reserved_usd'])==0
    assert all(r['status']=='settled' and r['actual_provider']=='DigitalOcean' and r['actual_model']==ledger['policy']['model'] for r in ledger['requests'])
    preflight=[r for r in ledger['requests'] if r['max_completion_tokens']==32];assert len(preflight)==2
    assert len(ids)==len(set(ids)) and set(ids)=={r['response_id'] for r in ledger['requests'] if r not in preflight}
    cost=sum((Decimal(r['actual_usd']) for r in ledger['requests']),Decimal(0));assert cost==Decimal(ledger['known_usd'])
    out={'verified':True,'raw_files':len(files),'source_files':len(plan['files']),'rows':rows,'metrics':metrics,'gates':gates,'development_pass':all(gates.values()),'decision':'advance_same_candidate' if all(gates.values()) else 'close_instruction_scope_v1_no_validation','api_requests':len(ledger['requests']),'judge_slots':75,'known_usd':str(cost),'unknown_cost_items':0,'updater_calls':0,'native_calls_total':0,'native_negative_controls':0,'ECS':None,'goal_complete':False,'validation_started':False,'scope':'Fulloriginalfrozenchangedsubset plus235Late;15cells,3arms,1repeat;quotecontrolineligibleforpromotion;exposedfamilies,nocausalpopulationclaim.'}
    print(json.dumps(out,ensure_ascii=False,indent=2))

if __name__=='__main__':main()

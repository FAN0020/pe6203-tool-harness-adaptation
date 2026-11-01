"""Four one-shot setup calls, excluded from updater evidence and outcome metrics."""
import asyncio
import json
from copy import deepcopy
from run_generation import HERE, ROOT, native_probe, save
from pe6203.experiment import configure_runtime


async def main():
    marker=HERE/'fixture-readiness.json'
    assert not marker.exists(), 'Never repeat setup calls after observed results'
    inputs=json.loads((HERE/'updater-inputs.json').read_text())
    configure_runtime(ROOT)
    rows=[]
    for original in inputs['jobs']:
        if not original['id'].startswith('project-'):continue
        job=deepcopy(original);job['id']='fixture-'+job['stage']
        for i,(name,token,expected) in enumerate([
            ('get_project','$PROJECT','FixtureProjectOne'),
            ('get_task','$TASK','FixtureRecordAlpha')],1):
            tool=next(t for t in job['data']['target']['tools'] if t['name']==name)
            probe={'id':f'P{i}','basis':job['data']['changed_ids'][0],
                   'tool_id':tool['tool_id'],
                   'arguments':{'workingDirectory':'$WORKSPACE','id':token},
                   'question':'Setup only: can the frozen native runtime read the synthetic fixture record?'}
            row=await native_probe(job,probe,inputs['fixture'],inputs['bindings'])
            result=row.get('result',{})
            body=json.dumps(result.get('content',[]))
            valid=not result.get('isError',False) and expected in body and inputs['bindings'][token] in body
            rows.append({'stage':job['stage'],'tool':name,'readable':valid,
                         'receipt':f"native/{job['id']}/{probe['id']}/observation.json"})
    save(marker,{'checks':rows,'passed':all(r['readable'] for r in rows),
                 'setup_native_calls':4,'setup_catalog_reads':4,
                 'model_calls':0,'updater_evidence':False})
    assert all(r['readable'] for r in rows), 'Fixture unavailable; no model calls'
    print(json.dumps({'fixture_ready':True,'setup_native_calls':4,'model_calls':0}))


if __name__=='__main__':asyncio.run(main())

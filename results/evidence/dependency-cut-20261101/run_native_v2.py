"""Exact dependency-only deferral equivalence; no model calls."""
import asyncio
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path
from pe6203.experiment import configure_runtime
from pe6203.transport import sessions

EVIDENCE=Path(__file__).resolve().parent
HERE=EVIDENCE/'native-v2'
HERE.mkdir(exist_ok=True)
ROOT=EVIDENCE.parents[2]
PLAN=ROOT/'experiments/dependency-cut-native-v2.json'
spec=importlib.util.spec_from_file_location('prior_native_audit',ROOT/'results/evidence/native-batch-cost-diagnostic-20261101/run_diagnostic.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
save=prior.save
sha=prior.sha

def waves(nodes,defer):
    depth={}
    for n in nodes:
        refs=([n['parent']] if n['parent'] else [])+([] if defer else n['dependsOn'])
        depth[n['key']]=1+max((depth[k] for k in refs),default=0)
    # Includes create_project, readback and required final answer; dependency patch adds one layer.
    return max(depth.values())+3+int(defer)

async def main():
    p=json.loads(PLAN.read_text());case=p['case'];nodes=case['nodes']
    assert len(nodes)==8 and sum(bool(n['dependsOn']) for n in nodes)==5
    assert all(n['details']==n['details'].strip() and 0<len(n['details'])<=2000 and n['name']==n['name'].strip() and 0<len(n['name'])<=100 for n in nodes)
    assert not (HERE/'native-preexecution.json').exists()
    for source in p['sources']:assert sha(ROOT/source['path'])==source['sha256']
    save(HERE/'native-preexecution.json',{'plan_sha256':sha(PLAN),'runner_sha256':sha(Path(__file__)),'freeze_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'model_calls':0})
    configure_runtime(ROOT);all_results=[];global_calls=0
    for stage,method in p['schedule']:
        dest=HERE/f'native-{stage}-{method}';dest.mkdir(exist_ok=False);workspace=dest/'workspace';workspace.mkdir()
        statepath=workspace/'.agentic-tools-mcp/tasks/tasks.json';observations=[]
        async with sessions(ROOT,stage,[p['server']],workspace,dest/'mcp.stderr.log') as clients:
            client=clients[p['server']];save(dest/'catalog.json',(await client.list_tools()).model_dump(mode='json',by_alias=True))
            async def call(name,args,negative=False):
                nonlocal global_calls
                args=dict(args,workingDirectory=str(workspace));before=statepath.read_bytes() if statepath.exists() else None
                r=(await client.call_tool(name,args)).model_dump(mode='json',by_alias=True,exclude_none=True);global_calls+=1
                row={'index':len(observations)+1,'global_index':global_calls,'tool':name,'arguments':args,'response':r,'negative_control':negative}
                observations.append(row);save(dest/f'{len(observations):02d}-response.json',row);save(dest/'observations.json',observations)
                if statepath.exists():(dest/f'{len(observations):02d}-state.json').write_bytes(statepath.read_bytes())
                save(HERE/'native-ledger.json',{'native_calls_completed':global_calls,'model_calls':0,'model_tokens':0,'usd':'0','last_path':dest.name})
                error=bool(r.get('isError')) or prior.content(r).startswith('Error:')
                assert error==negative,(stage,method,name,r)
                if negative:assert before==statepath.read_bytes()
                return r
            pid=prior.new_id(await call('create_project',{'name':'Dependency cut canary','description':'Independent field and edge preservation probe.'}));ids={}
            for n in nodes:
                args={k:n[k] for k in prior.FIELDS}
                if n['parent']:args['parentId']=ids[n['parent']]
                if method=='direct':args['dependsOn']=[ids[k] for k in n['dependsOn']]
                ids[n['key']]=prior.new_id(await call('create_task',dict(args,projectId=pid)))
            if method=='defer_dependencies':
                for n in nodes:
                    if n['dependsOn']:await call('update_task',{'id':ids[n['key']],'dependsOn':[ids[k] for k in n['dependsOn']]})
                await call('update_task',{'id':ids['H'],'dependsOn':['00000000-0000-0000-0000-000000000000']},negative=True)
            r=await call('list_tasks',{'projectId':pid,'showHierarchy':False,'includeCompleted':True})
            assert prior.listed_ids(r,nodes)==ids
            normalized,expected=prior.audit_state(json.loads(statepath.read_text()),case,pid,ids)
            result={'stage':stage,'method':method,'state_matches':normalized==expected,'normalized_state':normalized,'expected_state':expected,'native_calls':len(observations),'negative_controls':sum(o['negative_control'] for o in observations),'theoretical_waves_including_answer':waves(nodes,method=='defer_dependencies')}
            save(dest/'result.json',result);all_results.append(result);save(HERE/'native-results.json',all_results)
            print(json.dumps({k:v for k,v in result.items() if k not in ('normalized_state','expected_state')}),flush=True)
    assert global_calls==52 and all(r['state_matches'] for r in all_results)
    save(HERE/'native-decision.json',{'admitted':True,'native_calls':52,'catalog_calls':4,'model_calls':0,'usd':'0','stages':['middle','late'],'all_required_fields_equal':True,'negative_controls':2,'benchmark_success':False,'rows':[{k:v for k,v in r.items() if k not in ('normalized_state','expected_state')} for r in all_results]})

if __name__=='__main__':asyncio.run(main())

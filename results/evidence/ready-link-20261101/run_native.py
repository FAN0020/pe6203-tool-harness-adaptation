"""Frozen equivalence test, not an actor scheduler or benchmark performance test."""
import asyncio
import importlib.util
import json
import subprocess
from pathlib import Path
from pe6203.experiment import configure_runtime
from pe6203.transport import sessions

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PLAN = ROOT/'experiments/ready-link-native-v1.json'
spec = importlib.util.spec_from_file_location('native_helpers', ROOT/'results/evidence/native-batch-cost-diagnostic-20261101/run_diagnostic.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
save, sha = prior.save, prior.sha

def schedule(nodes, route):
    """Precompute symbolic waves; no IDs are invented or passed to native tools."""
    known, linked, waves = set(), set(), []
    while len(known) < len(nodes) or len(linked) < len(nodes):
        ops = []
        for n in nodes:
            key, deps = n['key'], set(n['dependsOn'])
            if key not in known and (not n['parent'] or n['parent'] in known):
                if route == 'direct' and not deps <= known: continue
                inline = route != 'global_defer' and deps <= known
                ops.append(('create', key, inline))
            elif key in known and key not in linked and deps <= known:
                if route != 'global_defer' or len(known) == len(nodes):
                    ops.append(('link', key, False))
        assert ops, 'Cyclic or unsatisfiable input'
        for op, key, inline in ops:
            n = next(n for n in nodes if n['key'] == key)
            if op == 'create':
                known.add(key)
                if inline or not n['dependsOn']: linked.add(key)
            else: linked.add(key)
        waves.append(ops)
    return waves

async def main():
    p=json.loads(PLAN.read_text())
    assert not (HERE/'native-preexecution.json').exists()
    for source in p['sources']: assert sha(ROOT/source['path']) == source['sha256'], source['path']
    # Pure schedule checks run for every case before opening any native session.
    for case in p['cases']:
        for route in ['direct','global_defer','ready_link']:
            known,linked=set(),set()
            for wave in schedule(case['nodes'],route):
                before=set(known)
                for op,key,inline in wave:
                    n=next(n for n in case['nodes'] if n['key']==key)
                    assert set(n['dependsOn']) <= before if op=='link' or inline else True
                    if op=='create':
                        assert not n['parent'] or n['parent'] in before
                        known.add(key)
                        if inline or not n['dependsOn']: linked.add(key)
                    else: assert key in before; linked.add(key)
            assert len(known)==len(linked)==8
    save(HERE/'native-preexecution.json',dict(plan_sha256=sha(PLAN), runner_sha256=sha(Path(__file__)),
        freeze_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),model_calls=0))
    configure_runtime(ROOT)
    results=[]; count=0
    for stage,case_id,route in p['schedule']:
        case=next(c for c in p['cases'] if c['id']==case_id); nodes=case['nodes']
        dest=HERE/f'native/{stage}-{case_id}-{route}'; dest.mkdir(parents=True,exist_ok=False)
        workspace=dest/'workspace'; workspace.mkdir()
        statepath=workspace/'.agentic-tools-mcp/tasks/tasks.json'
        observations=[]; ids={}; waves=schedule(nodes,route)
        async with sessions(ROOT,stage,[p['server']],workspace,dest/'mcp.stderr.log') as clients:
            client=clients[p['server']]
            save(dest/'catalog.json',(await client.list_tools()).model_dump(mode='json',by_alias=True))
            async def call(name,args,wave,negative=False):
                nonlocal count
                args=dict(args,workingDirectory=str(workspace))
                before=statepath.read_bytes() if statepath.exists() else None
                response=(await client.call_tool(name,args)).model_dump(mode='json',by_alias=True,exclude_none=True)
                count+=1
                row=dict(index=len(observations)+1,tool=name,arguments=args,response=response,wave=wave,negative_control=negative)
                observations.append(row); save(dest/f'{len(observations):02d}-response.json',row)
                save(dest/'observations.json',observations)
                if statepath.exists(): (dest/f'{len(observations):02d}-state.json').write_bytes(statepath.read_bytes())
                save(HERE/'native-ledger.json',dict(native_calls=count,model_calls=0,usd='0'))
                assert (bool(response.get('isError')) or prior.content(response).startswith('Error:')) == negative
                if negative: assert before == statepath.read_bytes()
                return response
            pid=prior.new_id(await call('create_project',dict(name='Ready-link canary',description='Generic field and edge preservation.'),0))
            for w,ops in enumerate(waves,1):
                before=dict(ids)
                for op,key,inline in ops:
                    n=next(n for n in nodes if n['key']==key)
                    if op=='create':
                        args={k:n[k] for k in prior.FIELDS}
                        if n['parent']: args['parentId']=before[n['parent']]
                        if inline: args['dependsOn']=[before[k] for k in n['dependsOn']]
                        ids[key]=prior.new_id(await call('create_task',dict(args,projectId=pid),w))
                    else: await call('update_task',dict(id=before[key],dependsOn=[before[k] for k in n['dependsOn']]),w)
            normal_calls=len(observations)+1
            if route=='ready_link':
                await call('update_task',dict(id=ids['H'],dependsOn=['00000000-0000-0000-0000-000000000000']),None,True)
            response=await call('list_tasks',dict(projectId=pid,showHierarchy=False,includeCompleted=True),len(waves)+1)
            assert prior.listed_ids(response,nodes)==ids
            normalized,expected=prior.audit_state(json.loads(statepath.read_text()),case,pid,ids)
            row=dict(stage=stage,case_id=case_id,kind=case['kind'],route=route,state_matches=normalized==expected,
                native_calls=len(observations),normal_calls=normal_calls,negative_controls=int(route=='ready_link'),
                theoretical_waves_including_answer=len(waves)+3,creation_waves=waves,
                normalized_state=normalized,expected_state=expected)
            save(dest/'result.json',row); results.append(row); save(HERE/'native-results.json',results)
            print(json.dumps({k:v for k,v in row.items() if k not in ('creation_waves','normalized_state','expected_state')}),flush=True)
    admitted=all(r['state_matches'] for r in results) and len(results)==18
    save(HERE/'native-decision.json',dict(admitted=admitted,native_calls=count,catalog_calls=18,negative_controls=6,model_calls=0,usd='0',
        rows=[{k:v for k,v in r.items() if k not in ('creation_waves','normalized_state','expected_state')} for r in results],
        limitation='Deterministic manually specified graphs, native serial operations; static wave opportunities are not measured LLM completion or quality.'))
    assert admitted

if __name__=='__main__': asyncio.run(main())

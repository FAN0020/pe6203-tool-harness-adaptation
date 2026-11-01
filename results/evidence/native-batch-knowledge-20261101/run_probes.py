"""Twelve frozen task-free native calls; retain state before every assertion."""
import asyncio
import hashlib
import json
import subprocess
from pathlib import Path

from pe6203.experiment import configure_runtime
from pe6203.transport import sessions

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PLAN = ROOT / 'experiments/native-batch-probes-v1.json'


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def main():
    assert not (HERE/'preexecution.json').exists(), 'Do not repeat an executed probe'
    plan = json.loads(PLAN.read_text())
    for source in plan['sources']:
        assert sha(ROOT/source['path']) == source['sha256']
    configure_runtime(ROOT)
    work = HERE/'workspace'
    work.mkdir(exist_ok=False)
    save(HERE/'preexecution.json', {'plan_sha256':sha(PLAN), 'sources':plan['sources'],
         'freeze_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
         'model_calls':0})
    rows = []
    statepath = work/'.agentic-tools-mcp/tasks/tasks.json'
    async with sessions(ROOT,'late',[plan['server']],work,HERE/'mcp.stderr.log') as clients:
        client = clients[plan['server']]
        save(HERE/'catalog.json',(await client.list_tools()).model_dump(mode='json',by_alias=True))

        def state(): return json.loads(statepath.read_text())

        async def call(name, args):
            args = dict(args,workingDirectory=str(work))
            result = (await client.call_tool(name,args)).model_dump(mode='json',by_alias=True,exclude_none=True)
            index = len(rows)+1
            row = {'index':index,'tool':name,'arguments':args,'result':result}
            save(HERE/f'{index:02d}-response.json',row)
            if statepath.exists():
                (HERE/f'{index:02d}-state.json').write_bytes(statepath.read_bytes())
                row['state_sha256'] = sha(statepath)
            rows.append(row)
            save(HERE/'observations.json',rows)
            assert not result.get('isError'), (index,name,result)
            return result

        await call('create_project',{'name':'Native import canary','description':'Independent ASCII record preservation only.'})
        project = state()['projects'][0]['id']
        common = {'projectId':project,'generateSubtasks':True,'estimateComplexity':True}
        await call('parse_prd',dict(common,prdContent='\n\n'.join(plan['positive_paragraphs'])))
        ts=state()['tasks']; assert len(ts)==3 and len({t['id'] for t in ts})==3
        for t, paragraph in zip(ts,plan['positive_paragraphs'],strict=True):
            assert t['name']==paragraph.splitlines()[0][2:] and t['details']==paragraph
            assert not t.get('parentId') and t['dependsOn']==[]
        ids={t['name']:t['id'] for t in ts}
        result=await call('list_tasks',{'projectId':project,'showHierarchy':False,'includeCompleted':True})
        text='\n'.join(c.get('text','') for c in result['content'])
        assert all(text.count(value)==1 for value in ids.values())
        await call('create_task',{'projectId':project,'name':'CANARY_CONTAINER','details':'Container for the ALPHA record only; BETA and GAMMA stay independent.','complexity':3})
        parent=next(t['id'] for t in state()['tasks'] if t['name']=='CANARY_CONTAINER')
        await call('update_task',{'id':ids['CANARY_ALPHA'],'parentId':parent,'dependsOn':[ids['CANARY_BETA']]})
        await call('list_tasks',{'projectId':project,'showHierarchy':False,'includeCompleted':True})
        alpha=next(t for t in state()['tasks'] if t['id']==ids['CANARY_ALPHA'])
        assert alpha['parentId']==parent and alpha['dependsOn']==[ids['CANARY_BETA']]
        assert alpha['details']==plan['positive_paragraphs'][0] and len(state()['tasks'])==4
        await call('parse_prd',dict(common,prdContent=plan['negative_grammar']))
        await call('list_tasks',{'projectId':project,'showHierarchy':False,'includeCompleted':True})
        ts=state()['tasks']; assert len(ts)==5 and ts[-1]['name']=='Implement PRD Requirements'
        await call('parse_prd',dict(common,prdContent=plan['negative_long']))
        await call('list_tasks',{'projectId':project,'showHierarchy':False,'includeCompleted':True})
        ts=state()['tasks']; assert len(ts)==6
        assert ts[-1]['details']==plan['negative_long'][:500]+'...'
        assert 'END_CANARY_MUST_NOT_VANISH' not in ts[-1]['details']
        await call('parse_prd',dict(common,prdContent='\n\n'.join(plan['positive_paragraphs'])))
        await call('list_tasks',{'projectId':project,'showHierarchy':False,'includeCompleted':True})
        ts=state()['tasks']; assert len(ts)==9 and len({t['id'] for t in ts})==9
        assert all(sum(t['name']==name for t in ts)==2 for name in ids)
    assert len(rows)==12
    save(HERE/'probe-decision.json',{'native_contract_admitted':True,'calls':12,'catalogs':1,
        'positive_records_preserved':3,'explicit_parent_dependency_update_verified':True,
        'implicit_hierarchy_dependencies':False,'nonidempotence_observed':True,
        'bad_grammar_fallback_observed':True,'long_paragraph_truncation_observed':True,
        'model_calls':0,'model_cost_usd':0,'benchmark_success_claim':False,
        'observations_sha256':sha(HERE/'observations.json')})
    print(json.dumps(json.loads((HERE/'probe-decision.json').read_text()),indent=2))


if __name__=='__main__':asyncio.run(main())

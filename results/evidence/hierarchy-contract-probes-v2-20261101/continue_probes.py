"""Execute only four preregistered remaining calls after the collector stopped."""
import asyncio
import hashlib
import json
from pathlib import Path
from pe6203.experiment import configure_runtime
from pe6203.transport import sessions

FOLDER=Path(__file__).resolve().parent
ROOT=FOLDER.parents[2]

async def main():
    plan=json.loads((ROOT/'experiments/hierarchy-contract-probes-v2.json').read_text())
    amend=json.loads((ROOT/'experiments/hierarchy-contract-probes-v2-continuation.json').read_text())
    work=FOLDER/'workspaces/late'
    statepath=work/'.agentic-tools-mcp/tasks/tasks.json'
    assert hashlib.sha256(statepath.read_bytes()).hexdigest()==amend['post_error_state_sha256']
    assert not (FOLDER/'late/12-state.json').exists()
    state=json.loads(statepath.read_text());parent=next(t for t in state['tasks'] if not t.get('parentId'))
    configure_runtime(ROOT)
    async with sessions(ROOT,'late',[plan['server']],work,FOLDER/'late-continuation-stderr.log') as clients:
        client=clients[plan['server']]
        calls=[]
        for _ in range(2):
            calls.extend([('analyze_task_complexity',dict(plan['fixed_analysis'],workingDirectory=str(work),taskId=parent['id'],autoCreateSubtasks=True)),('list_tasks',{'workingDirectory':str(work),'projectId':parent['projectId'],'showHierarchy':False})])
        for index,(tool,args) in enumerate(calls,12):
            result=(await client.call_tool(tool,args)).model_dump(mode='json',by_alias=True,exclude_none=True)
            snapshot=FOLDER/'late'/f'{index:02d}-state.json';snapshot.write_bytes(statepath.read_bytes())
            row={'stage':'late','index':index,'tool':tool,'arguments':args,'result':result,'snapshot':str(snapshot.relative_to(FOLDER)),'state_sha256':hashlib.sha256(snapshot.read_bytes()).hexdigest(),'continuation':'87ce944 after collector assertion; no completed call rerun'}
            (FOLDER/'late'/f'{index:02d}-{tool}.json').write_text(json.dumps(row,ensure_ascii=False,indent=2)+'\n')
    rows=[]
    for stage in plan['stages']:
        for p in sorted((FOLDER/stage).glob('*.json')):
            if not p.name.endswith('-state.json'):rows.append(json.loads(p.read_text()))
    assert len(rows)==29
    for item in plan['source']:
        p=ROOT/item['path'];assert (hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None)==item['sha256']
    (FOLDER/'observations.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'tool_calls':len(rows),'catalog_calls':2,'native_tool_errors':sum(bool(r['result'].get('isError')) for r in rows),'source_unchanged':True,'model_calls':0,'new_calls_in_continuation':4}))

if __name__=='__main__':asyncio.run(main())

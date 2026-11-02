"""One frozen, task-free equivalence diagnostic; no model, benchmark or judge."""
import asyncio
import hashlib
import json
import subprocess
from pathlib import Path

from pe6203.experiment import configure_runtime
from pe6203.transport import sessions

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


async def main():
    plan_path = HERE / 'native-plan.json'
    plan = json.loads(plan_path.read_text())
    assert (HERE/'native-preexecution.json').exists()
    assert not (HERE/'native-recovery-preexecution.json').exists()
    assert not list((HERE/'native').glob('*-??.json')), 'No observed call may be repeated'
    for work in (HERE/'native-workspaces').glob('*'):
        assert not list(work.iterdir()), 'Original pre-launch workspace must be empty'
    assert all(sha(ROOT/n) == h for n,h in plan['files'].items())
    commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    tracked = subprocess.check_output(['git','show',f'{commit}:{plan_path.relative_to(ROOT)}'],cwd=ROOT)
    assert tracked == plan_path.read_bytes(), 'Commit diagnostic freeze before executing'
    save(HERE/'native-recovery-preexecution.json', {'plan_sha256':sha(plan_path),'freeze_commit':commit,'runner_sha256':sha(Path(__file__)),'model_calls':0})
    (HERE/'native').mkdir(exist_ok=True)
    configure_runtime(ROOT)
    records = []
    for run in plan['runs']:
        work = HERE/'native-workspaces'/run['id']
        work.mkdir(parents=True, exist_ok=True)
        async with sessions(ROOT,run['stage'],['math-mcp'],work,HERE/'native'/f"{run['id']}-stderr.log") as clients:
            client = clients['math-mcp']
            catalog = (await client.list_tools()).model_dump(mode='json',by_alias=True,exclude_none=True)
            save(HERE/'native'/f"{run['id']}-catalog.json",catalog)
            for i,call in enumerate(run['calls']):
                try:
                    result = (await asyncio.wait_for(client.call_tool(call['tool'],call['arguments']),30)).model_dump(mode='json',by_alias=True,exclude_none=True)
                except Exception as exc:
                    result = {'diagnostic_exception':type(exc).__name__,'message':str(exc)}
                row = {'run':run['id'],'stage':run['stage'],'index':i,**call,'result':result}
                save(HERE/'native'/f"{run['id']}-{i:02d}.json",row)
                records.append(row)
        print(json.dumps({'run':run['id'],'calls':len(run['calls'])}),flush=True)
    checks = []
    for stage in ['middle','late']:
        left = [r for r in records if r['run']==stage+'-original']
        right = [r for r in records if r['run']==stage+'-replacement']
        assert len(left)==len(right)
        for a,b in zip(left,right):
            checks.append({'stage':stage,'index':a['index'],'pass':a['result']==b['result'] and 'diagnostic_exception' not in a['result']})
    assert all(sha(ROOT/n)==h for n,h in plan['files'].items())
    save(HERE/'native-result.json',{'checks':checks,'all_pass':all(c['pass'] for c in checks),'behavior_calls':len(records),'catalog_calls':len(plan['runs']),'model_calls':0,'cost_usd':0,'goal_complete':False,'limit':'Finite public-boundary checks plus manual source proof; not efficacy or benchmark success.'})


if __name__ == '__main__':
    asyncio.run(main())

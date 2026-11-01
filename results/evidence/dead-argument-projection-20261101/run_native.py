"""Execute only the frozen native diagnostic, retaining all observations."""
import asyncio
import hashlib
import json
import subprocess
from pathlib import Path
from pe6203.experiment import configure_runtime
from pe6203.transport import sessions

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PLAN = ROOT / 'experiments/dead-argument-native-v1.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


async def main():
    assert not (HERE / 'native-preexecution.json').exists()
    plan = json.loads(PLAN.read_text())
    for row in plan['source']:
        assert sha(ROOT / row['path']) == row['sha256'], row['path']
    assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).strip(), 'Commit freeze first'
    save(HERE / 'native-preexecution.json', dict(plan_sha256=sha(PLAN), freeze_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(), model_calls=0))
    configure_runtime(ROOT)
    observations = []
    for run in plan['runs']:
        work = HERE / 'native-workspaces' / run['id']
        work.mkdir(parents=True, exist_ok=False)
        async with sessions(ROOT, run['stage'], [run['server']], work, HERE / 'native' / f"{run['id']}-stderr.log") as clients:
            client = clients[run['server']]
            save(HERE / 'native' / f"{run['id']}-catalog.json", (await client.list_tools()).model_dump(mode='json', by_alias=True, exclude_none=True))
            for i, call in enumerate(run['calls']):
                result = (await client.call_tool(call['tool'], call['arguments'])).model_dump(mode='json', by_alias=True, exclude_none=True)
                row = dict(run=run['id'], stage=run['stage'], server=run['server'], index=i, **call, result=result)
                save(HERE / 'native' / f"{run['id']}-{i:03d}.json", row)
                observations.append(row)
        print(json.dumps(dict(session=run['id'], finished=len(run['calls']))), flush=True)
    save(HERE / 'native-observations.json', observations)
    checks = []
    for stage in ['middle', 'late']:
        rows = [r for r in observations if r['stage'] == stage]
        for group in sorted({r['group'] for r in rows if 'group' in r}):
            values = [r['result'] for r in rows if r.get('group') == group]
            checks.append(dict(stage=stage, group=group, n=len(values), pass_=all(v == values[0] for v in values)))
        for r in rows:
            if r['expect'] == 'error':
                checks.append(dict(stage=stage, control='invalid_argument', run=r['run'], index=r['index'], pass_=r['result'].get('isError') is True))
            if r['expect'] == 'related_paths_change':
                checks.append(dict(stage=stage, control='effective_related_paths', pass_=r['result'].get('structuredContent', {}).get('convergencePoints') == ['synthetic_beta']))
        valid = next(r['result'] for r in rows if r.get('group') == '8-3')
        invalid = next(r['result'] for r in rows if r.get('group') == '8+')
        checks.append(dict(stage=stage, control='effective_expression', pass_=valid != invalid))
        for step, active in [(1, ['synthetic_alpha']), (2, [])]:
            value = next(r['result'] for r in rows if r.get('group') == f'parallel-{step}')
            checks.append(dict(stage=stage, control=f'effective_state_{step}', pass_=not value.get('isError') and value.get('structuredContent', {}).get('activePaths') == active))
    for row in plan['source']:
        assert sha(ROOT / row['path']) == row['sha256'], row['path']
    result = dict(checks=checks, all_pass=all(c['pass_'] for c in checks), tool_calls=len(observations), expected_calls=plan['tool_calls'], catalog_calls=len(plan['runs']), model_calls=0, cost_usd=0,
                  source_hashes_verified=True, benchmark_development=False, validation=False)
    save(HERE / 'native-result.json', result)
    assert len(observations) == plan['tool_calls']
    print(json.dumps({k: v for k, v in result.items() if k != 'checks'}))
    assert result['all_pass']


if __name__ == '__main__':
    (HERE / 'native').mkdir(exist_ok=False)
    asyncio.run(main())

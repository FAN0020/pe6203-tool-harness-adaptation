"""Independently recompute the complete native diagnostic from archived bytes."""
import hashlib
import json
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREFIX = str(HERE.relative_to(ROOT)) + '/'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    manifest = json.loads((HERE / 'native-manifest.json').read_text())
    archive = HERE / manifest['archive']
    assert sha(archive.read_bytes()) == manifest['archive_sha256']
    with tarfile.open(archive) as tf:
        files = {m.name: tf.extractfile(m).read() for m in tf if m.isfile()}
    assert set(files) == set(manifest['files'])
    assert all(sha(files[n]) == v for n, v in manifest['files'].items())
    read = lambda n: json.loads(files[PREFIX + n])
    plan_name = 'experiments/dead-argument-native-v1.json'
    plan = json.loads(files[plan_name])
    assert read('native-preexecution.json')['plan_sha256'] == sha(files[plan_name])
    assert read('native-preexecution.json')['freeze_commit'].startswith('353073c')
    assert read('native-resume-preexecution.json')['freeze_commit'].startswith('53f21bf')
    assert read('native-resume-preexecution.json')['plan_sha256'] == sha(files[plan_name])
    assert all(sha(files[r['path']]) == r['sha256'] for r in plan['source'])
    recovery = read('native-recovery-freeze.json')
    assert all(sha(files[n]) == v for n, v in recovery['files'].items())
    observations = []
    expected_names = set()
    for run in plan['runs']:
        catalog = read(f"native/{run['id']}-catalog.json")
        tools = {t['name']: t for t in catalog['tools']}
        for i, call in enumerate(run['calls']):
            name = f"native/{run['id']}-{i:03d}.json"
            expected_names.add(PREFIX + name)
            row = read(name)
            expected = dict(run=run['id'], stage=run['stage'], server=run['server'], index=i, **call)
            assert {k: v for k, v in row.items() if k != 'result'} == expected
            assert call['tool'] in tools
            observations.append(row)
    actual_names = {n for n in files if n.startswith(PREFIX + 'native/') and n.endswith('.json') and not n.endswith('-catalog.json')}
    assert actual_names == expected_names
    assert observations == read('native-observations.json')
    assert len(observations) == plan['tool_calls'] == 333
    assert len(plan['runs']) == plan['catalog_calls'] == 22
    checks = []
    for stage in ['middle', 'late']:
        rows = [r for r in observations if r['stage'] == stage]
        for group in sorted({r['group'] for r in rows if 'group' in r}):
            grouped = [r for r in rows if r.get('group') == group]
            expected_count = 9 if group.startswith('parallel-') or stage == 'middle' else 81
            assert len(grouped) == expected_count
            assert sorted(r['variant'] for r in grouped) == list(range(expected_count))
            values = [r['result'] for r in grouped]
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
            result = next(r['result'] for r in rows if r.get('group') == f'parallel-{step}')
            checks.append(dict(stage=stage, control=f'effective_state_{step}', pass_=not result.get('isError') and result.get('structuredContent', {}).get('activePaths') == active))
    assert checks == read('native-result.json')['checks']
    assert len(checks) == 27 and all(c['pass_'] for c in checks)
    errors = [r for r in observations if 'exception_type' in r['result']]
    assert len(errors) == 18
    assert all(r['group'] == 'parallel-3' and r['result']['exception_type'] == 'RuntimeError' and
               "Additional properties are not allowed ('pathsSummary', 'synthesisReady' were unexpected)" in r['result']['exception'] for r in errors)
    original_exception = files[PREFIX + 'native-console.log'].decode().split('      | RuntimeError: ', 1)[1].rsplit('\n      +', 1)[0]
    assert read('native/middle-parallel-00-002.json')['result']['exception'] == original_exception
    initial = files[PREFIX + 'native-console.log'].decode().splitlines()
    resumed = files[PREFIX + 'native-resume-console.log'].decode().splitlines()
    initial_completed = [json.loads(x) for x in initial if x.startswith('{"session"')]
    resumed_completed = [json.loads(x) for x in resumed if x.startswith('{"session"')]
    assert [(r['session'], r['finished']) for r in initial_completed] == [('middle-math', 28)]
    assert [r['session'] for r in resumed_completed] == [r['id'] for r in plan['runs'][2:]]
    assert sum(r['finished'] for r in resumed_completed) == recovery['remaining_calls'] == 302
    assert recovery['completed_calls'] == 31
    assert not any(r['session'] in {'middle-math', 'middle-parallel-00'} for r in resumed_completed)
    result = dict(verified=True, archive_files=len(files), source_files=len(plan['source']), native_calls=333,
                  native_catalog_calls=22, checks_passed=27, captured_exceptions=18, new_sampled_calls_in_recovery=302,
                  repeated_sampled_calls=0, model_calls=0, cost_usd=0, development=False, validation=False, goal_complete=False)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

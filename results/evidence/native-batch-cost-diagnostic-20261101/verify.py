"""Independent stdlib-only replay of frozen native diagnostic state and costs."""
import hashlib
import json
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREFIX = str(HERE.relative_to(ROOT))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    manifest = json.loads((HERE/'manifest.json').read_text())
    archive = HERE/manifest['archive']
    assert digest(archive.read_bytes()) == manifest['sha256']
    with tarfile.open(archive, 'r:gz') as tf:
        assert len([m for m in tf.getmembers() if m.isfile()]) == len(manifest['files'])
        for member in manifest['files']:
            assert digest(tf.extractfile(member['path']).read()) == member['sha256']
        def data(path):
            return tf.extractfile(path).read()
        def read(path):
            return json.loads(data(path))
        plan_path = 'experiments/native-batch-cost-diagnostic-v1.json'
        plan = read(plan_path)
        pre = read(PREFIX+'/preexecution.json')
        assert digest(data(plan_path)) == pre['plan_sha256']
        assert digest(data(PREFIX+'/run_diagnostic.py')) == pre['runner_sha256']
        assert pre['freeze_commit'].startswith('68493fe')
        for source in plan['sources']:
            assert digest(data(source['path'])) == source['sha256']
        total = 0
        normalized_by_case = {}
        methods = []
        global_indices = []
        for case_id, method in plan['schedule']:
            case = next(c for c in plan['cases'] if c['id'] == case_id)
            prefix = PREFIX+f'/{case_id}-{method}'
            obs = read(prefix+'/observations.json')
            result = read(prefix+'/result.json')
            state = read(prefix+f'/{len(obs):02d}-state.json')
            assert obs[0]['tool'] == 'create_project' and obs[-1]['tool'] == 'list_tasks'
            assert len(obs) == result['native_calls']
            assert not any(o['response'].get('isError') for o in obs)
            for i, o in enumerate(obs, 1):
                assert o['index'] == i and o == read(prefix+f'/{i:02d}-response.json')
                assert len(json.dumps({'tool':o['tool'],'arguments':o['arguments']}, ensure_ascii=False).encode()) == o['request_bytes']
                assert len(json.dumps(o['response'], ensure_ascii=False).encode()) == o['response_bytes']
                global_indices.append(o['global_index'])
            assert sum(o['request_bytes'] for o in obs) == result['request_bytes']
            assert sum(o['response_bytes'] for o in obs) == result['response_bytes']
            assert len(state['projects']) == 1 and not state.get('subtasks')
            project = state['projects'][0]['id']
            tasks = state['tasks']
            by_name = {t['name']:t for t in tasks}
            ids = {t['id']:t['name'] for t in tasks}
            expected = {n['key']:n for n in case['nodes']}
            assert len(by_name) == len(ids) == len(tasks) == len(expected)
            assert all(ids) and all(t['projectId'] == project for t in tasks)
            levels = {}; depth = {}; canonical = []
            for node in case['nodes']:
                task = by_name[node['name']]
                for field in ('name','details','priority','complexity','estimatedHours','tags','status'):
                    assert task[field] == node[field], (case_id, method, node['key'], field)
                assert task['completed'] is False
                assert (ids[task['parentId']] if task.get('parentId') else None) == (expected[node['parent']]['name'] if node['parent'] else None)
                assert [ids[i] for i in task.get('dependsOn',[])] == [expected[k]['name'] for k in node['dependsOn']]
                levels[node['key']] = 0 if node['parent'] is None else 1+levels[node['parent']]
                assert task.get('level',0) == levels[node['key']]
                refs = node['dependsOn']+([node['parent']] if node['parent'] else [])
                depth[node['key']] = 1+max((depth[k] for k in refs), default=0)
                canonical.append({**node,'completed':False,'level':levels[node['key']]})
            normalized_by_case.setdefault(case_id,canonical)
            assert normalized_by_case[case_id] == canonical
            if method == 'direct':
                expected_calls = len(tasks)+2; expected_waves = max(depth.values())+2
            elif method == 'direct_deferred':
                expected_calls = len(tasks)+sum(bool(n['parent'] or n['dependsOn']) for n in case['nodes'])+2
                expected_waves = 4
            else:
                expected_calls = len(tasks)+4 if case['batch_restore_every_record'] else 3
                expected_waves = 5 if case['batch_restore_every_record'] else 3
            assert len(obs) == expected_calls and result['theoretical_dependency_waves'] == expected_waves
            assert result['state_matches'] and result['normalized_state'] == result['expected_state']
            total += len(obs)
            methods.append({'case_id':case_id,'method':method,'calls':len(obs),'dependency_waves':expected_waves})
        assert global_indices == list(range(1,total+1)) and total == plan['native_calls'] == 69
        ledger = read(PREFIX+'/native-ledger.json')
        assert ledger['native_calls_completed'] == 69 and ledger['catalog_calls_completed'] == 8
        assert ledger['model_calls'] == ledger['model_tokens'] == 0 and ledger['usd'] == '0'
        decision = read(PREFIX+'/decision.json')
        assert decision['all_state_equal'] and decision['native_calls'] == 69
        assert decision['model_calls'] == 0 and not decision['benchmark_success'] and not decision['validation_started']
    result = {'verified': True, 'archive_files': len(manifest['files']), 'paths':len(methods),
              'native_calls':total,'catalog_calls':8,'all_required_fields_equal':True,'model_calls':0,'usd':'0',
              'methods':methods,'goal_complete':False}
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()

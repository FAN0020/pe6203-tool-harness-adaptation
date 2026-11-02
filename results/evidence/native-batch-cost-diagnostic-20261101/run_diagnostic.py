"""Frozen native comparison; receipts drive calls, persisted state is evaluation only."""
import asyncio
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path

from pe6203.experiment import configure_runtime
from pe6203.transport import sessions

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PLAN = ROOT / 'experiments/native-batch-cost-diagnostic-v1.json'
FIELDS = ['name', 'details', 'priority', 'complexity', 'estimatedHours', 'tags', 'status']


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def content(result):
    return '\n'.join(c.get('text', '') for c in result.get('content', []))


def new_id(result):
    match = re.search(r'\(ID: ([0-9a-f-]{36})\)', content(result))
    if match is None:
        raise ValueError('Native creation receipt has no ID')
    return match.group(1)


def listed_ids(result, nodes):
    text = content(result)
    ids = {}
    for node in nodes:
        match = re.search(r'\*\*' + re.escape(node['name']) + r'\*\*[^\n]*\n\s*ID: ([0-9a-f-]{36})', text)
        if match is None:
            raise ValueError('Missing exact named record in native flat list')
        identity = match.group(1)
        if text.count(identity) != 1:
            raise ValueError('Duplicate identifier in native flat list')
        ids[node['key']] = identity
    if len(set(ids.values())) != len(nodes):
        raise ValueError('Duplicate IDs across records')
    return ids


def record_args(node, ids):
    args = {k: node[k] for k in FIELDS}
    if node['parent']:
        args['parentId'] = ids[node['parent']]
    args['dependsOn'] = [ids[k] for k in node['dependsOn']]
    return args


def audit_state(state, case, project_id, ids):
    tasks = state['tasks']
    by_id = {t['id']: t for t in tasks}
    assert len(tasks) == len(by_id) == len(case['nodes'])
    assert set(by_id) == set(ids.values()) and all(ids.values())
    assert len(state['projects']) == 1 and state['projects'][0]['id'] == project_id
    assert not state.get('subtasks')
    inverse = {v: k for k, v in ids.items()}
    normalized = []
    expected = []
    levels = {}
    for node in case['nodes']:
        levels[node['key']] = 0 if node['parent'] is None else levels[node['parent']] + 1
        task = by_id[ids[node['key']]]
        assert task['projectId'] == project_id
        normalized.append({**{k: task.get(k) for k in FIELDS}, 'key': node['key'],
                           'parent': inverse[task['parentId']] if task.get('parentId') else None,
                           'dependsOn': [inverse[v] for v in task.get('dependsOn', [])],
                           'completed': task['completed'], 'level': task.get('level', 0)})
        expected.append({**{k: node[k] for k in FIELDS}, 'key': node['key'],
                         'parent': node['parent'], 'dependsOn': node['dependsOn'],
                         'completed': False, 'level': levels[node['key']]})
    return normalized, expected


def waves(case, method):
    if method == 'direct_deferred':
        return 4
    if method == 'batch':
        return 5 if case['batch_restore_every_record'] else 3
    depth = {}
    for node in case['nodes']:
        refs = node['dependsOn'] + ([node['parent']] if node['parent'] else [])
        depth[node['key']] = 1 + max((depth[k] for k in refs), default=0)
    return 2 + max(depth.values())


def validate_plan(plan):
    count = 0
    for case_id, method in plan['schedule']:
        case = next(c for c in plan['cases'] if c['id'] == case_id)
        known = set()
        for node in case['nodes']:
            assert len(node['details']) <= 500 and node['details'].isascii()
            assert node['details'].splitlines()[0] == '- ' + node['name']
            assert len(node['name']) > 5 and node['key'] not in known
            assert set(node['dependsOn']).issubset(known)
            assert node['parent'] is None or node['parent'] in known
            known.add(node['key'])
        if method == 'direct_deferred':
            count += len(case['nodes']) + sum(bool(n['parent'] or n['dependsOn']) for n in case['nodes']) + 2
        else:
            count += len(case['nodes']) + 2 if method == 'direct' else (len(case['nodes']) + 4 if case['batch_restore_every_record'] else 3)
    assert count == plan['native_calls'] == 69
    assert len(plan['schedule']) == len(set(map(tuple, plan['schedule']))) == 8
    return count


async def main():
    plan = json.loads(PLAN.read_text())
    validate_plan(plan)
    for source in plan['sources']:
        assert sha(ROOT / source['path']) == source['sha256']
    assert not (HERE / 'preexecution.json').exists(), 'Never resample a started diagnostic'
    configure_runtime(ROOT)
    save(HERE / 'preexecution.json', {'plan_sha256': sha(PLAN), 'runner_sha256': sha(Path(__file__)),
         'sources': plan['sources'], 'freeze_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
         'model_calls': 0})
    results = []
    global_index = 0
    for case_id, method in plan['schedule']:
        case = next(c for c in plan['cases'] if c['id'] == case_id)
        folder = HERE / f'{case_id}-{method}'
        folder.mkdir(exist_ok=False)
        workspace = folder / 'workspace'
        workspace.mkdir()
        state_path = workspace / '.agentic-tools-mcp/tasks/tasks.json'
        rows = []
        started = time.perf_counter()
        async with sessions(ROOT, 'late', [plan['server']], workspace, folder / 'mcp.stderr.log') as clients:
            client = clients[plan['server']]
            save(folder / 'catalog.json', (await client.list_tools()).model_dump(mode='json', by_alias=True))

            async def call(tool, arguments):
                nonlocal global_index
                args = dict(arguments, workingDirectory=str(workspace))
                response = (await client.call_tool(tool, args)).model_dump(mode='json', by_alias=True, exclude_none=True)
                global_index += 1
                row = {'index': len(rows) + 1, 'global_index': global_index, 'tool': tool, 'arguments': args, 'response': response,
                       'request_bytes': len(json.dumps({'tool': tool, 'arguments': args}, ensure_ascii=False).encode()),
                       'response_bytes': len(json.dumps(response, ensure_ascii=False).encode())}
                save(folder / f'{row["index"]:02d}-response.json', row)
                if state_path.exists():
                    (folder / f'{row["index"]:02d}-state.json').write_bytes(state_path.read_bytes())
                rows.append(row)
                save(folder / 'observations.json', rows)
                save(HERE / 'native-ledger.json', {'model_calls': 0, 'model_tokens': 0, 'usd': '0', 'native_calls_completed': global_index,
                     'last_path': folder.name, 'catalog_calls_completed': len(results) + 1})
                assert not response.get('isError'), (folder.name, tool, response)
                return response

            result = await call('create_project', {'name': f'Canary {case_id}', 'description': 'Independent native field and topology preservation comparison.'})
            project_id = new_id(result)
            ids = {}
            list_args = {'projectId': project_id, 'showHierarchy': False, 'includeCompleted': True}
            if method in ('direct', 'direct_deferred'):
                for node in case['nodes']:
                    args = record_args(node, ids) if method == 'direct' else {k: node[k] for k in FIELDS}
                    result = await call('create_task', dict(args, projectId=project_id))
                    ids[node['key']] = new_id(result)
                if method == 'direct_deferred':
                    for node in case['nodes']:
                        if node['parent'] or node['dependsOn']:
                            links = {k: v for k, v in record_args(node, ids).items() if k in ('parentId', 'dependsOn')}
                            await call('update_task', dict(links, id=ids[node['key']]))
                result = await call('list_tasks', list_args)
                assert listed_ids(result, case['nodes']) == ids
            else:
                await call('parse_prd', {'projectId': project_id, 'prdContent': '\n\n'.join(n['details'] for n in case['nodes']),
                           'estimateComplexity': True, 'generateSubtasks': False, 'defaultPriority': 5})
                result = await call('list_tasks', list_args)
                ids = listed_ids(result, case['nodes'])
                if case['batch_restore_every_record']:
                    for node in case['nodes']:
                        args = {k: v for k, v in record_args(node, ids).items() if k not in ('name', 'details')}
                        await call('update_task', dict(args, id=ids[node['key']]))
                    result = await call('list_tasks', list_args)
                    assert listed_ids(result, case['nodes']) == ids
            # The evaluation-only state read cannot supply an actor-visible identifier.
            state = json.loads(state_path.read_text())
            normalized, expected = audit_state(state, case, project_id, ids)
            outcome = {'case_id': case_id, 'kind': case['kind'], 'method': method, 'native_calls': len(rows),
                       'state_matches': normalized == expected, 'normalized_state': normalized, 'expected_state': expected,
                       'request_bytes': sum(r['request_bytes'] for r in rows),
                       'response_bytes': sum(r['response_bytes'] for r in rows),
                       'max_request_bytes': max(r['request_bytes'] for r in rows),
                       'theoretical_dependency_waves': waves(case, method),
                       'native_wall_seconds': time.perf_counter() - started}
            save(folder / 'result.json', outcome)
            results.append(outcome)
            save(HERE / 'results.json', results)
            print(json.dumps({k: v for k, v in outcome.items() if k not in ('normalized_state', 'expected_state')}), flush=True)
    assert global_index == plan['native_calls']
    save(HERE / 'decision.json', {'all_state_equal': all(r['state_matches'] for r in results), 'native_calls': global_index,
         'model_calls': 0, 'usd': '0', 'benchmark_success': False, 'validation_started': False,
         'paired': [{'case_id': c['id'], 'kind': c['kind'],
                     'methods': {r['method']: {k: r[k] for k in ['native_calls', 'theoretical_dependency_waves', 'request_bytes', 'response_bytes']}
                                 for r in results if r['case_id'] == c['id']}}
                    for c in plan['cases']]})


if __name__ == '__main__':
    asyncio.run(main())

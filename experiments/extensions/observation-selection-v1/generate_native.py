"""Generate authentic historical receipts and isolated fixtures before model calls."""
import asyncio
import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path
from pe6203.experiment import configure_runtime
from pe6203.transport import sessions

B = Path(__file__).resolve().parent
ROOT = B.parents[2]
E = ROOT / 'results/evidence/observation-selection-20261101'


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text(result):
    return '\n'.join(c.get('text', '') for c in result.get('content', []))


def identity(result):
    found = re.search(r'\(ID: ([a-f0-9-]{36})\)', text(result))
    assert found
    return found.group(1)


async def main():
    protocol = json.loads((B / 'protocol.json').read_text())
    for s in protocol['sources']:
        assert sha(ROOT / s['path']) == s['sha256']
    dest = E / 'native'
    dest.mkdir(exist_ok=False)
    work = dest / 'workspace'
    work.mkdir()
    store = work / '.agentic-tools-mcp/tasks/tasks.json'
    save(E / 'native-preexecution.json', {
        'protocol_sha256': sha(B / 'protocol.json'),
        'generator_sha256': sha(Path(__file__)),
        'freeze_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'model_calls': 0,
    })
    configure_runtime(ROOT)
    observations = []
    server = '@pimzino/agentic-tools-mcp'
    async with sessions(ROOT, 'late', [server], work, dest / 'stderr.log') as cs:
        client = cs[server]
        save(dest / 'catalog.json', (await client.list_tools()).model_dump(mode='json', by_alias=True))

        async def call(tool, args, readonly=False):
            before = store.read_bytes() if store.exists() else None
            args = dict(args, workingDirectory=str(work))
            result = (await client.call_tool(tool, args)).model_dump(mode='json', by_alias=True, exclude_none=True)
            observations.append({'tool': tool, 'args': args, 'result': result})
            save(dest / 'observations.json', observations)
            save(E / 'native-ledger.json', {'native_calls': len(observations), 'catalog_calls': 1, 'model_calls': 0, 'usd': '0'})
            assert not result.get('isError') and not text(result).startswith('Error:')
            if readonly:
                assert before == store.read_bytes(), 'Readonly prerequisite changed task store'
            return result

        rule = protocol['native_generation']
        pid = identity(await call('create_project', rule['project']))
        receipt = await call('create_task', dict(rule['initial_task'], projectId=pid))
        tid = identity(receipt)
        before = store.read_bytes()
        get_before = await call('get_task', {'id': tid}, readonly=True)
        rec_before = await call('get_next_task_recommendation', {'projectId': pid, 'maxRecommendations': 1}, readonly=True)
        updated = await call('update_task', dict(rule['update'], id=tid))
        after = store.read_bytes()
        get_after = await call('get_task', {'id': tid}, readonly=True)
        rec_after = await call('get_next_task_recommendation', {'projectId': pid, 'maxRecommendations': 1}, readonly=True)
    assert len(observations) == 7
    assert 'Larch checkpoint' in text(get_before) and 'Cedar checkpoint' in text(get_after)
    assert 'Priority:' not in text(get_before) and 'Priority:' not in text(get_after)
    assert 'Priority: 3/10' in text(rec_before) and 'Priority: 7/10' in text(rec_after)
    assert 'Priority: 3/10' in text(receipt) and 'Priority: 7/10' in text(updated)
    servers = json.loads((ROOT / 'experiments/extensions/dependency-factorial-v1/task-901001.json').read_text())['servers']
    manifest = {}
    for case in protocol['cases']:
        task_id = case['task_id']
        raw = before if case['freshness'] == 'fresh' else after
        fixture = B / 'fixtures' / str(task_id) / '.agentic-tools-mcp/tasks/tasks.json'
        fixture.parent.mkdir(parents=True)
        fixture.write_bytes(raw)
        state = json.loads(raw)
        assert len(state['projects']) == len(state['tasks']) == 1 and not state['subtasks']
        record = state['tasks'][0]
        assurance = ('This is the latest receipt and no changes to this task have occurred since it was issued.'
                     if case['freshness'] == 'fresh' else
                     'This receipt is historical. The task has been edited since it was issued; details of that later edit are not supplied here.')
        question = (
            'This is an independent synthetic read-only record audit. The workspace already contains the project and task below. '
            'Do not create, update, delete, move, migrate or otherwise change any task, project or memory while auditing. '
            f'Report the current {case["field"]} of task {tid} in project {pid}. '
            'Identify the task and project in your final answer, give the requested value, and briefly identify the evidence supporting that current value. '
            'Do not claim unobserved values are verified or claim implementation work was completed. '
            f'{assurance}\n\nAuthentic earlier task-creation receipt:\n{text(receipt)}'
        )
        task = {'idx': task_id, 'extension_id': f'ext-observation-selection-{task_id}-v1',
                'dataset_kind': 'controlled_synthetic_extension', 'question': question, 'servers': copy.deepcopy(servers)}
        save(B / f'task-{task_id}.json', task)
        oracle = {'task_id': task_id, 'freshness': case['freshness'], 'field': case['field'],
                  'value': record[case['field']], 'project_id': pid, 'record_id': tid,
                  'initial_store_sha256': sha(fixture), 'receipt_current': case['freshness'] == 'fresh',
                  'eval_only': True, 'live_witness': 'get_task or other exact name output' if case['field'] == 'name' else 'get_next_task_recommendation exact numeric priority (other actual witnesses accepted)'}
        save(B / 'evaluation' / f'oracle-{task_id}.json', oracle)
    for p in sorted(B.rglob('*.json')):
        if p.name not in ('data-manifest.json', 'protocol.json'):
            manifest[str(p.relative_to(B))] = sha(p)
    save(B / 'data-manifest.json', manifest)
    save(E / 'native-decision.json', {'admitted': True, 'native_calls': 7, 'catalog_calls': 1, 'model_calls': 0,
         'readonly_calls_preserved_state': 4, 'get_name_visible_priority_hidden': True,
         'alternative_readonly_priority_visible': True, 'fresh_and_stale_fixture_values_differ': True,
         'authentic_receipt_reused_for_all4cases': True, 'original_benchmark_success': False})
    print(json.dumps({'native_calls': 7, 'cases': 4, 'model_calls': 0, 'admitted': True}))


if __name__ == '__main__':
    asyncio.run(main())

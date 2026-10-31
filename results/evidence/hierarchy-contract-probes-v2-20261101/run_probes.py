"""Execute the preregistered local hierarchy probes; no model calls."""
import asyncio
import hashlib
import json
import re
from pathlib import Path

from pe6203.experiment import configure_runtime
from pe6203.transport import sessions

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[2]
PLAN = ROOT / 'experiments/hierarchy-contract-probes-v2.json'
UUID = re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b')


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def main():
    assert not (FOLDER / 'observations.json').exists()
    plan = json.loads(PLAN.read_text())
    for item in plan['source']:
        path = ROOT / item['path']
        assert (sha(path) if path.exists() else None) == item['sha256']
    configure_runtime(ROOT)
    save(FOLDER / 'preexecution.json', {'plan_sha256': sha(PLAN), 'freeze_commit': 'da268fc',
                                      'source': plan['source'], 'model_calls': 0})
    rows = []
    for stage in plan['stages']:
        work = FOLDER / 'workspaces' / stage
        work.mkdir(parents=True, exist_ok=False)
        dest = FOLDER / stage
        dest.mkdir(exist_ok=False)
        async with sessions(ROOT, stage, [plan['server']], work,
                            FOLDER / f'{stage}-stderr.log') as clients:
            client = clients[plan['server']]
            catalog = (await client.list_tools()).model_dump(mode='json', by_alias=True)
            save(FOLDER / f'{stage}-catalog.json', catalog)
            schemas = {t['name']: t['inputSchema'] for t in catalog['tools']}
            index = 0

            async def call(tool, args):
                nonlocal index
                index += 1
                args = dict(args)
                if 'workingDirectory' in schemas[tool].get('properties', {}):
                    args['workingDirectory'] = str(work)
                result = (await client.call_tool(tool, args)).model_dump(
                    mode='json', by_alias=True, exclude_none=True)
                state = work / '.agentic-tools-mcp/tasks/tasks.json'
                snapshot = dest / f'{index:02d}-state.json'
                assert state.exists(), (stage, index, tool, result)
                snapshot.write_bytes(state.read_bytes())
                row = {'stage': stage, 'index': index, 'tool': tool, 'arguments': args,
                       'result': result, 'snapshot': str(snapshot.relative_to(FOLDER)),
                       'state_sha256': sha(state)}
                save(dest / f'{index:02d}-{tool}.json', row)
                rows.append(row)
                assert not result.get('isError'), (stage, index, tool, result)
                return result

            def state():
                return json.loads((work / '.agentic-tools-mcp/tasks/tasks.json').read_text())

            result = await call('create_project', {'name': 'Synthetic hierarchy probe',
                                                   'description': 'Independent record-copy canaries only.'})
            project_id = state()['projects'][0]['id']
            assert project_id in json.dumps(result)
            result = await call('create_task', dict(plan['parent'], projectId=project_id))
            parent_id = state()['tasks'][0]['id']
            assert parent_id in json.dumps(result)
            analysis = dict(plan['fixed_analysis'], autoCreateSubtasks=False)
            await call('analyze_task_complexity', dict(analysis, taskId=parent_id))
            children = [dict(c, parentId=parent_id) for c in plan['children']]
            child_results = []
            for child in children:
                child_results.append(await call('create_task', dict(child, projectId=project_id)))
            ids = {t['name']: t['id'] for t in state()['tasks']}
            assert all(ids[c['name']] in json.dumps(result) for c, result in zip(children, child_results, strict=True))
            await call('analyze_task_complexity', dict(analysis, projectId=project_id))
            for child in children:
                await call('analyze_task_complexity', dict(analysis, taskId=ids[child['name']]))
            await call('list_tasks', {'projectId': project_id, 'showHierarchy': True})
            await call('list_tasks', {'projectId': project_id, 'showHierarchy': False})
            if stage == 'late':
                await call('review_project_status', {'projectId': project_id, 'includeCompletedTasks': True, 'maxTasks': 20})
            for _ in range(2):
                await call('analyze_task_complexity', dict(analysis, taskId=parent_id,
                                                          autoCreateSubtasks=True))
                await call('list_tasks', {'projectId': project_id, 'showHierarchy': False})
            assert index == (15 if stage == 'late' else 14)
    assert len(rows) == plan['planned_tool_calls']
    for item in plan['source']:
        path = ROOT / item['path']
        assert (sha(path) if path.exists() else None) == item['sha256']
    save(FOLDER / 'observations.json', rows)
    print(json.dumps({'tool_calls': len(rows), 'catalog_calls': 2, 'source_unchanged': True,
                      'model_calls': 0, 'errors': 0}))


if __name__ == '__main__':
    asyncio.run(main())

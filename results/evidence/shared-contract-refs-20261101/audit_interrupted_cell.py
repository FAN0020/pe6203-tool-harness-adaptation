"""Offline projection of the stopped actor; no scores, reasoning, or model calls."""
import hashlib
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUN = ROOT / 'results/raw/shared-contract-refs-pilot-20261101/cells/cell-006/run'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit():
    paths = [RUN / 'events.jsonl', RUN / 'result.json',
             RUN / 'workspace/.agentic-tools-mcp/tasks/tasks.json', HERE / 'knowledge-audit.json']
    archived = read(HERE / 'raw-at-stop-manifest.json')['files']
    for p in paths[:3]:
        assert sha(p) == archived[str(p.relative_to(ROOT))]
    trace_path = RUN / 'raw_trace.json'
    assert sha(trace_path) == archived[str(trace_path.relative_to(ROOT))]
    assert not read(trace_path).get('answer'), 'Final delivery unexpectedly present'
    store = read(paths[2]); tasks = store['tasks']
    ids = [t['id'] for t in tasks]; by_id = {t['id']: t for t in tasks}
    assert all(ids) and len(ids) == len(set(ids))
    assert all(t['projectId'] in {p['id'] for p in store['projects']} for t in tasks)
    for field in ['parentId', 'dependsOn']:
        edges = {t['id']: ([t[field]] if t.get(field) else []) if field == 'parentId'
                 else t.get(field, []) for t in tasks}
        assert all(x in by_id for targets in edges.values() for x in targets)
        visiting = set(); done = set()

        def visit(node):
            assert node not in visiting, f'{field} cycle'
            if node in done:
                return
            visiting.add(node)
            for target in edges[node]:
                visit(target)
            visiting.remove(node); done.add(node)

        for node in ids:
            visit(node)
    children = Counter(t.get('parentId') for t in tasks)
    affected = {e['tool_id'].split('::')[-1]
                for row in read(paths[3]) if row['task_id'] == 283 and row['stage'] == 'late'
                for e in row['edits']}
    counts = Counter(); references = []; errors = []; responses = 0
    for line in paths[0].read_text().splitlines():
        event = json.loads(line)
        responses += event['type'] == 'agent_response'
        if event['type'] != 'tool_result':
            continue
        call = event['call']['function']; name = call['name'].split('__')[0]
        arguments = json.loads(call['arguments']); counts[name] += 1
        if name in affected:
            references.append({'tool': name, 'working_directory_matches':
                               arguments.get('workingDirectory') == str(RUN / 'workspace'),
                               'isError': event['result'].get('isError', False)})
        if event['result'].get('isError'):
            errors.append({'tool': name, 'reported_error': event['result']})
    return {
        'cell_id': 'cell-006', 'scope': 'Interrupted candidate output, not a blinded completed trajectory',
        'source_sha256': {str(p.relative_to(ROOT)): sha(p) for p in [*paths, trace_path]},
        'normal_completion': False, 'official_scores': None,
        'graph': {'projects': len(store['projects']), 'tasks': len(tasks),
                  'dependency_edges': sum(len(t.get('dependsOn', [])) for t in tasks),
                  'valid_ids_and_acyclic_references': True,
                  'roots': [{'name': t['name'], 'children': children[t['id']]}
                            for t in tasks if not t.get('parentId')]},
        'actor_responses': responses, 'tool_call_counts': dict(counts),
        'affected_calls': references, 'anchor_update_project_calls': counts['update_project'],
        'native_errors': errors,
        'properties': {'coverage': 'fail', 'structure_and_scope': 'fail',
                       'delivery_truth': 'unknown', 'scope_preserved': 'pass'},
        'core_pass': False,
        'review_evidence': [
            'CSV has eight concrete child tasks and logs six. Visualization and integration roots explicitly promise delivery through children, but have none at interruption. Visualization has no executable breakdown.',
            'IDs and references are valid and acyclic. This does not satisfy all scope/decomposition requirements; remaining milestone work is incomplete.',
            'No final handover; judge not started. Missing score is not zero or pass.',
            'Observed mutations create project/tasks and update dependencies; no deletion or substantive scope relabeling observed.'
        ],
        'mechanism_evidence': [
            'Exactly three observed calls use tools whose workingDirectory description is a reference. All supply the exact run workspace. No anchor update_project call occurs.',
            'One native tool reports memoryStorage.listMemories is not a function despite the correct path. This error is separate from the later HTTP429. Whether knowledge altered the decision to call it is unknown.',
            'Correct parameters do not prove the actor resolved the description reference; other context or prior knowledge may suffice. No paired effect or completion benefit is established.'
        ],
        'decision': 'Retain failed interrupted product. No actor rerun, no candidate edit, no validation promotion. Existing A2 accounting question remains pending.',
        'new_model_calls': 0, 'new_native_calls': 0, 'new_cost_usd': 0,
    }


if __name__ == '__main__':
    result = audit(); output = HERE / 'interrupted-cell006-review.json'
    if output.exists():
        assert read(output) == result
    else:
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'graph': result['graph'], 'affected_calls': len(result['affected_calls']),
                      'all_affected_paths_match': all(x['working_directory_matches'] for x in result['affected_calls']),
                      'core_pass': result['core_pass'], 'new_model_calls': 0}))

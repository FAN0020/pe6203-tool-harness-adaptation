"""Read-only independent graph checks on opaque product-review packets."""
import hashlib
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent


def audit(review_id):
    packet = json.loads((HERE / 'blind-inputs' / (review_id + '.json')).read_text())
    out = {'review_id': review_id, 'call_counts': dict(Counter(c['tool'].split('__')[0] for c in packet['calls']))}
    for artifact in packet['artifacts']:
        p = HERE / 'blind-artifacts' / review_id / artifact['path']
        assert hashlib.sha256(p.read_bytes()).hexdigest() == artifact['sha256']
        data = json.loads(p.read_text())
        tasks = data['tasks']; ids = [t.get('id') for t in tasks]; by_id = {t['id']: t for t in tasks}
        parents = {t.get('parentId') for t in tasks if t.get('parentId')}
        project_ids = {p['id'] for p in data['projects']}
        errors = []
        if not all(ids) or len(ids) != len(set(ids)): errors.append('empty_or_duplicate_task_id')
        if any(t.get('projectId') not in project_ids for t in tasks): errors.append('invalid_project_id')
        for field in ('parentId', 'dependsOn'):
            edges = {t['id']: ([t[field]] if field == 'parentId' and t.get(field) else t.get(field, []) if field == 'dependsOn' else []) for t in tasks}
            if any(x not in by_id for values in edges.values() for x in values): errors.append(field + '_dangling')
            active = set(); done = set()
            def visit(node):
                if node in active: raise ValueError(field + '_cycle')
                if node in done or node not in edges: return
                active.add(node)
                for nxt in edges[node]: visit(nxt)
                active.remove(node); done.add(node)
            try:
                for key in edges: visit(key)
            except ValueError as exc: errors.append(str(exc))
        out['graph'] = {'projects': len(data['projects']), 'tasks': len(tasks), 'roots': sum(not t.get('parentId') for t in tasks), 'leaves': sum(t['id'] not in parents for t in tasks), 'dependency_edges': sum(len(t.get('dependsOn', [])) for t in tasks), 'errors': errors}
    out['non_dependency_updates'] = []
    for c in packet['calls']:
        if c['tool'].startswith('update_task'):
            args = json.loads(c['arguments'])
            substantive = {k:v for k,v in args.items() if k not in ('id','workingDirectory','dependsOn','status')}
            if substantive: out['non_dependency_updates'].append({'id': args['id'], **substantive})
    return out


if __name__ == '__main__':
    import sys
    print(json.dumps([audit(r) for r in sys.argv[1:]], ensure_ascii=False, indent=2))

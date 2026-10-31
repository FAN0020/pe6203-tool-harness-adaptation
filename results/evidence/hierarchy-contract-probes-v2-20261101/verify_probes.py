"""Offline integrity and synthetic-state checks; no tool/model calls."""
import hashlib
import json
import re
import tarfile
from pathlib import Path

FOLDER = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    manifest = json.loads((FOLDER / 'archive-manifest.json').read_text())
    archive = FOLDER / 'probe-and-source.tar.gz'
    assert sha(archive.read_bytes()) == manifest['archive_sha256']
    with tarfile.open(archive) as tar:
        files = {m.name: tar.extractfile(m).read() for m in tar if m.isfile()}
    assert {k: sha(v) for k, v in files.items()} == manifest['files']
    rows = json.loads((FOLDER / 'observations.json').read_text())
    assert len(rows) == 29
    assert sum(bool(r['result'].get('isError')) for r in rows) == 1
    plan = json.loads(files['protocol/hierarchy-contract-probes-v2.json'])
    for item in plan['source']:
        if item['sha256'] is None:
            assert 'source/' + item['path'] not in files
        else:
            assert sha(files['source/' + item['path']]) == item['sha256']
    summaries = []
    for stage, count in [('middle', 14), ('late', 15)]:
        calls = {r['index']: r for r in rows if r['stage'] == stage}
        assert sorted(calls) == list(range(1, count + 1))
        states = {}
        for index, row in calls.items():
            path = FOLDER / row['snapshot']
            assert sha(path.read_bytes()) == row['state_sha256']
            assert files['evidence/' + row['snapshot']] == path.read_bytes()
            states[index] = json.loads(path.read_text())

        def text(index):
            return '\n'.join(c.get('text', '') for c in calls[index]['result']['content'])

        parent = states[2]['tasks'][0]
        for state in states.values():
            match = next((t for t in state['tasks'] if t['id'] == parent['id']), None)
            if match:
                for k, value in plan['parent'].items():
                    assert match[k] == value
        assert 'Average complexity: 9.0/10' in text(3)
        assert '(Complexity: 9/10)' in text(6)
        assert 'Complex tasks (≥7): 1' in text(6)
        assert all('Average complexity: 3.0/10' in text(i) for i in (7, 8))
        before = states[10]['tasks']
        assert len(before) == 3 and all(t['id'] for t in before)
        assert len(set(t['id'] for t in before)) == 3
        tree_occurrences = {t['name']: text(9).count(t['id']) for t in before}
        flat_occurrences = {t['name']: text(10).count(t['id']) for t in before}
        assert sorted(tree_occurrences.values()) == [1, 2, 2]
        assert set(flat_occurrences.values()) == {1}
        assert 'Total: 5 tasks' in text(9) and 'Found 3 task(s)' in text(10)
        first_auto = 11 if stage == 'middle' else 12
        assert len(states[first_auto]['tasks']) == 3
        assert len(states[first_auto]['subtasks']) == 3
        assert all(t['id'] == '' for t in states[first_auto]['subtasks'])
        assert len(states[first_auto + 1]['tasks']) == 6
        assert len(states[first_auto + 1]['subtasks']) == 0
        assert len(states[first_auto + 2]['subtasks']) == 3
        final = states[count]
        assert len(final['tasks']) == 9 and not final['subtasks']
        assert sum(t['id'] == '' for t in final['tasks']) == 6
        assert len(set(t['id'] for t in final['tasks'])) == 4
        if stage == 'late':
            assert calls[11]['result']['isError']
            assert 'storage.getTasksByProject is not a function' in text(11)
        summaries.append({'stage': stage, 'calls': count, 'parent_score_before_and_after': 9,
                          'child_scores': [3, 3], 'parent_fields_unchanged': True,
                          'tree_occurrences': tree_occurrences, 'flat_occurrences': flat_occurrences,
                          'before_auto_tasks': 3, 'after_first_auto_and_list': 6,
                          'after_second_auto_and_list': 9, 'final_empty_task_ids': 6})
    print(json.dumps({'verified': True, 'archive_files': len(files), 'tool_calls': 29,
                      'catalog_calls': 2, 'separate_failed_v1_tool_calls': 1,
                      'separate_failed_v1_catalog_calls': 1, 'model_calls': 0,
                      'native_tool_errors': 1, 'rows': summaries,
                      'limits': 'Synthetic behavior only; Late tail resumed in a fresh MCP process after collector assertion. No agent improvement proven.'}, indent=2))


if __name__ == '__main__':
    main()

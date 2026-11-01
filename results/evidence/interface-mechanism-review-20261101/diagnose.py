"""Offline, bounded design-admission diagnostics; no models, network, or score changes.

Run from the repository root. Only named fixtures and four already-selected review
inputs are read. Character counts are NOT model-token counts or wire measurements.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
FIXTURE = 'tests/fixtures/prefix-workflow-catalogs.json'
REVIEW_ROOT = 'results/evidence/prefix-workflow-pilot-20261101/blind-inputs'
REVIEW_IDS = ('W02', 'W04', 'W05', 'W06')
FIELDS = ('name', 'parameters', 'description', 'output_schema', 'routing')
BULK = 'slidev-mcp::create_bulk_slides'


def read(relative):
    return json.loads((ROOT / relative).read_text())


def sha(relative):
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def diagnose():
    catalogs = read(FIXTURE)['457']
    old = {t['tool_id']: t for t in catalogs['early']['tools']}
    stages = {}
    for stage in ('early', 'middle', 'late'):
        catalog = catalogs[stage]
        current = {t['tool_id']: t for t in catalog['tools']}
        changed = {
            tid: [f for f in FIELDS if record[f] != old[tid][f]]
            for tid, record in current.items() if tid in old
        }
        stages[stage] = {
            'tools': len(current),
            'description_characters': sum(len(t['description']) for t in current.values()),
            'parameters_json_characters': sum(len(json.dumps(t['parameters'], ensure_ascii=False)) for t in current.values()),
            'usage_rule_characters': sum(sum(len(r) for r in t['usage_rules']) for t in current.values()),
            'added_ids': sorted(current.keys() - old.keys()),
            'changed_fields': {k: v for k, v in changed.items() if v},
            'bulk_exists_in_early': BULK in old,
            'bulk_description_characters': len(current[BULK]['description']),
        }
    rows = []
    sources = [FIXTURE]
    for rid in REVIEW_IDS:
        path = f'{REVIEW_ROOT}/{rid}.json'
        source = read(path)
        # This guard only establishes the already-declared task identity. It is not
        # a new task-selection rule and no question or answer enters an updater.
        assert 'Embodied AI' in source['question'], rid
        names = [c['tool'].split('__')[0] for c in source['calls']]
        rows.append({
            'review_id': rid, 'actual_tools_in_order': names,
            'bulk_calls': names.count('create_bulk_slides'),
            'set_page_calls': names.count('set_page'),
            'add_page_calls': names.count('add_page'),
        })
        sources.append(path)
    return {
        'scope': '457 catalog fixture and four prior original457 development tool-name lists; not new executions and not a failure census',
        'measurement': 'Unicode character counts, parameters serialized by json.dumps(ensure_ascii=False) with default separators; NOT tokens; metadata only, excludes tool observations',
        'stages': stages,
        'prior_execution_projection': rows,
        'total_bulk_calls': sum(r['bulk_calls'] for r in rows),
        'total_content_write_calls': sum(r['set_page_calls'] + r['add_page_calls'] for r in rows),
        'input_sha256': {p: sha(p) for p in sources},
        'limits': [
            'No bulk invocation does not rule out influence from exposing its definition.',
            'Short descriptions do not rule out schema, observation, or semantic complexity.',
            'Counts cannot establish the cause of reasoning-token exhaustion.',
            'No task completion, quality, TF, PE, ECS, or retention result is newly measured here.',
        ],
    }


if __name__ == '__main__':
    result = diagnose()
    target = HERE / 'diagnostic.json'
    if target.exists():
        assert read(str(target.relative_to(ROOT))) == result, 'Frozen diagnostic mismatch'
        print(json.dumps({'verified': True, 'inputs': len(result['input_sha256']), 'prior_runs': len(REVIEW_IDS), 'bulk_calls': result['total_bulk_calls'], 'new_model_calls': 0}))
    else:
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        print('Wrote bounded diagnostic; rerun to verify the frozen result.')

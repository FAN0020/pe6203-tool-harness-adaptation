"""Offline verification and predeclared contrasts, only after all reviews freeze."""
import json
import statistics
import tarfile
from decimal import Decimal
from pathlib import Path
from raw_cell_verifier import archive_files, inspect_cell, sha

E = Path(__file__).resolve().parent


def main():
    freeze = json.loads((E / 'review-freeze.json').read_text())
    assert freeze['all_reviews_before_scores'] and freeze['reviews'] == 16
    assert all(sha((E / k).read_bytes()) == v for k, v in freeze['files'].items())
    files, manifest = archive_files(E)
    prefix = manifest['prefix'] + '/'
    read = lambda n: json.loads(files[prefix + n])
    plan = read('plan.json')
    assert sha(files[prefix + 'plan.json']) == files[prefix + 'plan.sha256'].decode().strip()
    assert plan['cells'] == plan['diagnostic_spec']['schedule'] and len(plan['cells']) == 16
    sm = json.loads((E / 'prefreeze-manifest.json').read_text())
    assert sha((E / sm['archive']).read_bytes()) == sm['archive_sha256']
    with tarfile.open(E / sm['archive']) as tf:
        source = {m.name: tf.extractfile(m).read() for m in tf if m.isfile()}
    assert all(sha(source[k]) == v for k, v in plan['files'].items())
    lock = read('knowledge-lock.json')
    assert lock['plan_sha256'] == sha(files[prefix + 'plan.json'])
    assert all(sha(files[prefix + k]) == v for k, v in lock['files'].items())
    assert read('knowledge-review.json')['accepted']
    state = read('experiment.json')
    assert len(state['cells']) == 16 and not state.get('stop_reason')
    assert all(c['status'] == 'evaluated' for c in state['cells'].values())
    for c in state['cells'].values():
        assert all(sha(files[prefix + k]) == v for k, v in c['files'].items())
    reverse = {v: k for k, v in json.loads((E / 'blind-map.json').read_text()).items()}
    cases = {c['task_id']: c for c in plan['diagnostic_spec']['cases']}
    rows, ids = [], []
    for cell in plan['cells']:
        rid = reverse[cell['id']]
        review = json.loads((E / 'blind-reviews' / f'{rid}.json').read_text())
        packet = json.loads((E / 'blind-inputs' / f'{rid}.json').read_text())
        assert review['input_sha256'] == sha((E / 'blind-inputs' / f'{rid}.json').read_bytes())
        assert set(review['properties']) == {'state_preserved', 'current_value', 'evidence', 'claims'}
        assert review['core_pass'] == all(v == 'pass' for v in review['properties'].values())
        oracle = json.loads(source[f'experiments/extensions/observation-selection-v1/evaluation/oracle-{cell["task_id"]}.json'])
        store_path = f'cells/{cell["id"]}/run/workspace/.agentic-tools-mcp/tasks/tasks.json'
        state_unchanged = sha(files[prefix + store_path]) == oracle['initial_store_sha256']
        assert len(packet['artifacts']) == 1
        assert sha(files[prefix + store_path]) == packet['artifacts'][0]['sha256']
        old = source[f'results/raw/observation-coverage-pilot-20261101/adaptations/283-late-{cell["strategy"]}/knowledge.json']
        assert files[prefix + f'adaptations/{cell["task_id"]}-late-{cell["strategy"]}/knowledge.json'] == old
        row, requests = inspect_cell(files, prefix, cell, 'controlled_observation_selection_diagnostic')
        ids.extend(requests)
        row.update(review_id=rid, repeat=cell['seed'], freshness=cases[cell['task_id']]['freshness'],
                   field=cases[cell['task_id']]['field'], properties=review['properties'],
                   core_pass=review['core_pass'], store_bytes_unchanged=state_unchanged,
                   evidence_measurements=review['evidence_measurements'])
        rows.append(row)
    ledger = read('spend-ledger.json')
    assert not ledger['blocked'] and Decimal(ledger['unknown_reserved_usd']) == 0
    assert ledger['policy']['limit_usd'] is None
    assert all(r['status'] == 'settled' and r['actual_provider'] == 'DigitalOcean' and r['actual_model'] == ledger['policy']['model'] for r in ledger['requests'])
    pre = [r for r in ledger['requests'] if r['max_completion_tokens'] == 32]
    assert len(pre) == 2
    assert len(ids) == len(set(ids)) and set(ids) == {r['response_id'] for r in ledger['requests'] if r not in pre}
    cost = sum((Decimal(r['actual_usd']) for r in ledger['requests']), Decimal(0))
    assert cost == Decimal(ledger['known_usd'])
    groups = []
    for case in cases.values():
        for arm in ('selective_patch', 'observation_coverage'):
            selected = [r for r in rows if r['task_id'] == case['task_id'] and r['strategy'] == arm]
            assert len(selected) == 2
            groups.append({**case, 'strategy': arm, 'n': 2,
                           'normal_completion': sum(r['execution_status'] == 'completed' for r in selected),
                           'core_pass': sum(r['core_pass'] for r in selected),
                           **{k: statistics.mean(r[k] for r in selected) for k in ('TF', 'PE', 'rounds', 'tool_calls')}})
    contrasts = []
    for block in (0, 1):
        for task in cases:
            pair = {r['strategy']: r for r in rows if r['repeat'] == block and r['task_id'] == task}
            a, b = pair['selective_patch'], pair['observation_coverage']
            contrasts.append({'repeat': block, 'task_id': task,
                              'core_delta': int(b['core_pass']) - int(a['core_pass']),
                              'calls_delta': b['tool_calls'] - a['tool_calls'],
                              'non_witness_reads_delta': b['evidence_measurements']['non_witness_read_calls'] - a['evidence_measurements']['non_witness_read_calls'],
                              'fresh_reads_delta': b['evidence_measurements']['fresh_read_calls'] - a['evidence_measurements']['fresh_read_calls']})
    accuracy = all(x['core_delta'] > 0 for x in contrasts if x['task_id'] == 902004) and all(x['core_delta'] >= 0 for x in contrasts if x['task_id'] != 902004)
    efficient = all(r['core_pass'] for r in rows)
    efficient = efficient and all(x['non_witness_reads_delta'] < 0 for x in contrasts if x['task_id'] == 902004)
    efficient = efficient and all(sum(x['fresh_reads_delta'] for x in contrasts if x['repeat'] == block and x['task_id'] in (902001, 902002)) < 0 for block in (0, 1))
    supported = accuracy or efficient
    out = {'verified': True, 'raw_files': len(files), 'source_files': len(plan['files']),
           'rows': rows, 'groups': groups, 'contrasts': contrasts,
           'mechanism_support': supported, 'accuracy_support': accuracy, 'efficiency_support': efficient,
           'decision': 'bounded_diagnostic_support_only' if supported else 'no_predeclared_replicated_advantage_deprioritize_v1',
           'api_requests': len(ledger['requests']), 'judge_slots': 80, 'known_usd': str(cost),
           'unknown_cost_items': 0, 'updater_calls': 0, 'native_setup_calls': 7,
           'original_development_reopened': False, 'formal_validation_started': False, 'goal_complete': False}
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

"""Verify preserved interrupted evidence and completed A2 cells; never impute TF."""
import copy
import json
import statistics
import tarfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from raw_cell_verifier import archive_files, inspect_cell, sha

HERE = Path(__file__).resolve().parent


def main():
    files, manifest = archive_files(HERE); prefix = manifest['prefix'] + '/'
    read = lambda name: json.loads(files[prefix + name])
    plan = read('plan.json'); state = read('experiment.json'); spec = plan['research']['spec']
    assert sha(files[prefix + 'plan.json']) == files[prefix + 'plan.sha256'].decode().strip()
    assert len(plan['cells']) == len(state['cells']) == 10
    assert {c['id'] for c in plan['cells']} == set(state['cells'])
    assert sum(c['status'] == 'evaluated' for c in state['cells'].values()) == 9
    assert state['cells']['cell-006']['status'] == 'blocked'
    source_manifest = json.loads((HERE / 'prefreeze-manifest.json').read_text())
    source_path = HERE / source_manifest['archive']
    assert sha(source_path.read_bytes()) == source_manifest['archive_sha256']
    with tarfile.open(source_path) as t:
        source = {m.name: t.extractfile(m).read() for m in t if m.isfile()}
    assert all(sha(source[n]) == h for n, h in plan['files'].items())
    lock = read('knowledge-lock.json')
    assert lock['plan_sha256'] == sha(files[prefix + 'plan.json'])
    assert all(sha(files[prefix + n]) == h for n, h in lock['files'].items())
    assert read('knowledge-review.json')['accepted']
    assert read('knowledge-review.json')['lock_sha256'] == sha(files[prefix + 'knowledge-lock.json'])
    for item in state['cells'].values():
        assert all(sha(files[prefix + n]) == h for n, h in item['files'].items())
    for item in json.loads((HERE / 'knowledge-audit.json').read_text()):
        stem = f"adaptations/{item['task_id']}-{item['stage']}-"
        baseline = read(stem + 'selective_patch/knowledge.json')
        candidate = read(stem + 'shared_contract_refs/knowledge.json')
        restored = copy.deepcopy(candidate); by = {t['tool_id']: t for t in restored['tools']}
        assert item['SP_sha256'] == sha(files[prefix + stem + 'selective_patch/knowledge.json'])
        assert item['candidate_sha256'] == sha(files[prefix + stem + 'shared_contract_refs/knowledge.json'])
        for edit in item['edits']:
            prop = by[edit['tool_id']]['parameters']['properties'][edit['parameter']]
            anchor = by[edit['anchor_tool_id']]['parameters']['properties'][edit['parameter']]
            assert prop['description'] == edit['after'] and anchor['description'] == edit['before']
            prop['description'] = anchor['description']; assert prop == anchor
        assert restored == baseline
    freeze = json.loads((HERE / 'review-freeze.json').read_text())
    assert freeze['all_reviews_before_scores'] and freeze['reviews'] == 10
    assert all(sha((HERE / n).read_bytes()) == h for n, h in freeze['files'].items())
    mapping = json.loads((HERE / 'blind-map.json').read_text()); reverse = {v:k for k,v in mapping.items()}
    rows = []; ids = []
    for cell in plan['cells']:
        rid = reverse[cell['id']]; review = json.loads((HERE / 'blind-reviews' / (rid + '.json')).read_text())
        packet_path = HERE / 'blind-inputs' / (rid + '.json'); packet = json.loads(packet_path.read_text())
        assert sha(packet_path.read_bytes()) == review['input_sha256']
        expected = {p['id'] for p in next(q for q in spec['quality_cases'] if q['task_id'] == cell['task_id'])['properties']}
        assert set(review['properties']) == expected
        assert review['core_pass'] == all(v == 'pass' for v in review['properties'].values())
        for artifact in packet['artifacts']:
            assert sha(files[prefix + f"cells/{cell['id']}/run/workspace/" + artifact['path']]) == artifact['sha256']
        if cell['id'] != 'cell-006':
            row, response_ids = inspect_cell(files, prefix, cell, 'original_benchmark_development_A2')
            ids.extend(response_ids)
        else:
            base = 'cells/cell-006/run/'
            r = read(base + 'result.json'); trace = read(base + 'raw_trace.json')
            assert r['status'] == 'blocked' and r['execution_status'] == 'failed'
            assert r['judge_status'] == 'not_started' and r['TF'] is None and r['PE'] is None
            assert not trace['answer'] and not packet['answer']
            assert trace['question'] == next(t['question'] for t in plan['tasks'] if t['idx'] == cell['task_id'])
            for key, value in plan['config'].items(): assert r['config'][key] == value
            k = f"adaptations/{cell['task_id']}-{cell['version']}-{cell['strategy']}/knowledge.json"
            assert read(base + 'knowledge.json') == read(k)
            responses = [e['response'] for e in trace['events'] if e['type'] == 'agent_response']
            calls = [e for e in trace['events'] if e['type'] == 'tool_result']
            assert len(responses) == 5 and len(calls) == 28
            for response in responses:
                assert response['provider'] == 'DigitalOcean' and response['model'] == plan['config']['agent']['model']
                ids.append(response['id'])
            row = {'cell_id': cell['id'], 'task_id': cell['task_id'], 'stage': cell['version'],
                   'strategy': cell['strategy'], 'execution_status': 'failed', 'TF': None, 'PE': None,
                   'rounds': len(responses), 'tool_calls': len(calls),
                   'tool_errors': sum(bool(e['result'].get('isError')) for e in calls),
                   'seconds': r['seconds'], 'judge_values': [], 'infrastructure_interruption': True}
        row.update(review_id=rid, core_pass=review['core_pass'], properties=review['properties'])
        rows.append(row)
    ledger_name = 'results/raw/shared-contract-refs-dev-costs-20261101/spend-ledger.json'
    ledger = json.loads(files[ledger_name]); before_manifest = json.loads((HERE / 'raw-at-stop-manifest.json').read_text())
    before_path = HERE / before_manifest['archive']; assert sha(before_path.read_bytes()) == before_manifest['archive_sha256']
    with tarfile.open(before_path) as t:
        before = {m.name:t.extractfile(m).read() for m in t if m.isfile()}
    assert {n:sha(b) for n,b in before.items()} == before_manifest['files']
    original_ledger = json.loads(before[ledger_name])
    assert ledger['requests'][:54] == original_ledger['requests'] and ledger['policy'] == original_ledger['policy']
    continuation_path = HERE / 'continuation-a2.json'
    continuation = json.loads(continuation_path.read_text())
    authorization = json.loads((HERE / 'continuation-authorization.json').read_text())
    assert authorization['approved'] is True and authorization['manifest_sha256'] == sha(continuation_path.read_bytes())
    assert sha(continuation_path.read_bytes()) == (HERE / 'continuation-a2.sha256').read_text().strip()
    for name, expected in continuation['frozen_files'].items():
        content = before[name] if name in before else (HERE.parents[2] / name).read_bytes()
        assert sha(content) == expected
    assert all(datetime.fromisoformat(r['started_at']) >= datetime.fromisoformat(authorization['recorded_at'])
               for r in ledger['requests'][54:])
    before_state = json.loads(before[prefix + 'experiment.json'])
    assert all(state['cells'][c] == item for c,item in before_state['cells'].items())
    unchanged_original_cells = {n:b for n,b in before.items() if n.startswith(prefix + 'cells/')}
    assert all(files[n] == b for n,b in unchanged_original_cells.items())
    assert [i for i,r in enumerate(ledger['requests']) if r['status'] != 'settled'] == [53]
    assert ledger['requests'][53]['actual_usd'] is None and ledger['blocked'] is True
    assert ledger['policy']['limit_usd'] is None and ledger['unknown_reserved_usd'] == original_ledger['unknown_reserved_usd']
    settled = [r for r in ledger['requests'] if r['status'] == 'settled']
    assert all(r['actual_provider'] == 'DigitalOcean' and r['actual_model'] == ledger['policy']['model'] for r in settled)
    preflight = [r for r in settled if r['max_completion_tokens'] == 32]; assert len(preflight) == 2
    assert len(ids) == len(set(ids)) and set(ids) == {r['response_id'] for r in settled if r not in preflight}
    cost = sum((Decimal(r['actual_usd']) for r in settled), Decimal(0)); assert cost == Decimal(ledger['known_usd'])
    metrics = {}
    for arm in ['selective_patch', 'shared_contract_refs']:
        metrics[arm] = {}
        for group,tasks in [('project',{283}),('changed',{133,283}),('retention',{235})]:
            subset = [r for r in rows if r['strategy'] == arm and r['task_id'] in tasks]
            observed = [r for r in subset if r['TF'] is not None]
            metrics[arm][group] = {'n':len(subset), 'completed':sum(r['execution_status'] == 'completed' for r in subset),
                                  'core_pass':sum(r['core_pass'] for r in subset), 'scored_n':len(observed),
                                  'TF':statistics.mean(r['TF'] for r in observed) if len(observed) == len(subset) else None,
                                  'observed_TF_mean':statistics.mean(r['TF'] for r in observed) if observed else None,
                                  'observed_PE_mean':statistics.mean(r['PE'] for r in observed) if observed else None}
    b,c = metrics['selective_patch'],metrics['shared_contract_refs']; gates = {}
    for group in ['project','changed']:
        for key in ['completed','core_pass']: gates[group + '_' + key + '_strict_gain'] = c[group][key] > b[group][key]
        gates[group + '_TF_nondecrease'] = None if c[group]['TF'] is None or b[group]['TF'] is None else c[group]['TF'] >= b[group]['TF']
    gates['retention_nondecrease'] = all(c['retention'][k] >= b['retention'][k] for k in ['completed','core_pass','TF'])
    out = {'integrity_verified':True, 'rows':rows, 'metrics':metrics, 'gates':gates,
           'development_pass':False, 'validation_started':False, 'goal_complete':False,
           'decision':'Close this incomplete development cohort; no resampling or validation. Mechanism not established; one actor has missing TF after infrastructure interruption.',
           'api_requests':len(ledger['requests']), 'settled_requests':len(settled), 'unknown_requests':1,
           'known_usd':str(cost), 'a2_increment_known_usd':str(cost - Decimal(original_ledger['known_usd'])),
           'unknown_reserved_usd':ledger['unknown_reserved_usd'], 'judge_slots':45,
           'updater_calls':0, 'new_behavioral_probes':0, 'actor_native_tool_calls':sum(r['tool_calls'] for r in rows),
           'original_source_files_verified':len(plan['files']), 'raw_files_verified':len(files),
           'original_first_six_cells_unchanged':True, 'original_unknown_row_unchanged':True,
           'ECS':None, 'limitations':['One trajectory per condition, exposed tasks, coordinator reviews, one interrupted actor and missing TF.',
                                     'Observed TF means use unequal counts and cannot establish the frozen complete-cohort nondecrease gate.']}
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

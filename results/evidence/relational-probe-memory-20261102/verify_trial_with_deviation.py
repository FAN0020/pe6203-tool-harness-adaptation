"""Offline replay of frozen evidence, product judgments, five slots and receipts."""
import json
import statistics
import tarfile
from decimal import Decimal
from pathlib import Path

from raw_cell_verifier import archive_files, inspect_cell, sha

HERE = Path(__file__).resolve().parent


def main():
    files, manifest = archive_files(HERE)
    prefix = manifest['prefix'] + '/'
    def read(name):
        return json.loads(files[prefix + name])
    plan, state = read('plan.json'), read('experiment.json')
    spec = plan['research']['spec']
    candidate = spec['candidates'][0]
    assert sha(files[prefix+'plan.json']) == files[prefix+'plan.sha256'].decode().strip()
    assert len(plan['cells']) == len(state['cells']) == 10
    assert all(c['status'] == 'evaluated' for c in state['cells'].values())
    source_manifest = json.loads((HERE/'prefreeze-manifest.json').read_text())
    source_archive = HERE/source_manifest['archive']
    assert sha(source_archive.read_bytes()) == source_manifest['archive_sha256']
    with tarfile.open(source_archive) as tar:
        source = {m.name:tar.extractfile(m).read() for m in tar if m.isfile()}
    assert all(sha(source[n]) == h for n,h in plan['files'].items())
    lock = read('knowledge-lock.json')
    assert lock['plan_sha256'] == sha(files[prefix+'plan.json'])
    assert all(sha(files[prefix+n]) == h for n,h in lock['files'].items())
    assert read('knowledge-review.json')['accepted']
    assert read('knowledge-review.json')['lock_sha256'] == sha(files[prefix+'knowledge-lock.json'])
    for item in state['cells'].values():
        assert all(sha(files[prefix+n]) == h for n,h in item['files'].items())
    for item in json.loads((HERE/'knowledge-audit.json').read_text()):
        stem = f"adaptations/{item['task_id']}-{item['stage']}-"
        assert sha(files[prefix+stem+'selective_patch/knowledge.json']) == item['SP_sha256']
        assert sha(files[prefix+stem+candidate+'/knowledge.json']) == item['candidate_sha256']
        if item['task_id'] != 283:
            assert read(stem+'selective_patch/knowledge.json') == read(stem+candidate+'/knowledge.json')
    freeze = json.loads((HERE/'review-freeze.json').read_text())
    assert freeze['reviews'] == 10 and freeze['all_reviews_before_individual_scores']
    assert freeze['reviews_before_aggregate_scores'] == 8 and not freeze['all_reviews_before_scores']
    deviation = json.loads((HERE/'blinding-deviation.json').read_text())
    assert all(sha((HERE/n).read_bytes()) == h for n,h in deviation['previous_8_review_hashes'].items())
    assert all(sha((HERE/n).read_bytes()) == h for n,h in freeze['files'].items())
    mapping = json.loads((HERE/'blind-map.json').read_text())
    reverse = {v:k for k,v in mapping.items()}
    rows, ids = [], []
    for cell in plan['cells']:
        rid = reverse[cell['id']]
        review = json.loads((HERE/'blind-reviews'/f'{rid}.json').read_text())
        packet_path = HERE/'blind-inputs'/f'{rid}.json'
        packet = json.loads(packet_path.read_text())
        assert sha(packet_path.read_bytes()) == review['input_sha256']
        expected = {p['id'] for p in next(q for q in spec['quality_cases'] if q['task_id'] == cell['task_id'])['properties']}
        assert set(review['properties']) == expected
        assert review['core_pass'] == all(v == 'pass' for v in review['properties'].values())
        for artifact in packet['artifacts']:
            assert sha(files[prefix+f"cells/{cell['id']}/run/workspace/"+artifact['path']]) == artifact['sha256']
        row, response_ids = inspect_cell(files, prefix, cell, 'original_benchmark_development')
        row.update(review_id=rid, core_pass=review['core_pass'], properties=review['properties'])
        ids.extend(response_ids)
        rows.append(row)
    ledger_name = plan['config']['spend_guard']['ledger']
    ledger = json.loads(files[ledger_name])
    settled = ledger['requests']
    assert all(r['status'] == 'settled' for r in settled)
    assert not ledger['blocked'] and Decimal(ledger['unknown_reserved_usd']) == 0
    assert ledger['policy']['limit_usd'] is None
    assert all(r['actual_provider'] == 'DigitalOcean' and r['actual_model'] == ledger['policy']['model'] for r in settled)
    preflight = [r for r in settled if r['max_completion_tokens'] == 32]
    assert len(preflight) == 2
    assert len(ids) == len(set(ids))
    assert set(ids) == {r['response_id'] for r in settled if r not in preflight}
    cost = sum((Decimal(r['actual_usd']) for r in settled), Decimal(0))
    assert cost == Decimal(ledger['known_usd'])
    metrics = {}
    for arm in ['selective_patch', candidate]:
        metrics[arm] = {}
        for group,tasks in [('treated_project',{283}),('changed',{133,283}),('math_regression',{133}),('retention',{235})]:
            subset = [r for r in rows if r['strategy'] == arm and r['task_id'] in tasks]
            metrics[arm][group] = {'n':len(subset),
                'completed':sum(r['execution_status'] == 'completed' for r in subset),
                'core_pass':sum(r['core_pass'] for r in subset),
                'TF':statistics.mean(r['TF'] for r in subset),
                'PE':statistics.mean(r['PE'] for r in subset)}
    b,c = metrics['selective_patch'], metrics[candidate]
    gates = {}
    for group in ['treated_project','changed']:
        for key in ['completed','core_pass']:
            gates[group+'_'+key+'_strict_gain'] = c[group][key] > b[group][key]
        gates[group+'_TF_nondecrease'] = c[group]['TF'] >= b[group]['TF']
    gates['retention_nondecrease'] = all(c['retention'][k] >= b['retention'][k] for k in ['completed','core_pass','TF'])
    out = {'integrity_verified':True,'candidate':candidate,'rows':rows,'metrics':metrics,'gates':gates,
        'numerical_development_pass':all(gates.values()),'development_pass':False,'review_blinding':'8 before aggregate scores; 2 partially exposed; all before individual mapping/scores','original_verifier_sha256':'8d02b0f5456ad712fbc6f9a53941430a97874ab0695c8a88d9ca2a0691a6af25','validation_started':False,'goal_complete':False,
        'api_requests':len(settled),'settled_requests':len(settled),'unknown_requests':0,'known_usd':str(cost),
        'judge_slots':50,'updater_calls_reported_separately':3,'new_behavioral_probes':7,
        'actor_native_tool_calls':sum(r['tool_calls'] for r in rows),
        'source_files_verified':len(plan['files']),'raw_files_verified':len(files),'ECS':None,
        'limitations':['One execution per condition; exposed tasks; same coordinator product reviewer. Aggregate-score exposure before last two judgments is separately preserved; no promotion on this run.',
                       'Unchanged133/235 knowledge means differences in those conditions cannot be attributed to this intervention.',
                       'Development counts are frozen gates, not inferential proof or independent validation.']}
    print(json.dumps(out,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()

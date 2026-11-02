"""Read-only, standard-library verification; no API, credentials or extraction."""
import ast
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
PREFIX = 'results/evidence/description-factor-control-20261101/'
read = lambda p: json.loads(p.read_text())
digest = lambda b: hashlib.sha256(b).hexdigest()
manifest = read(HERE / 'archive-manifest.json')
packs = {}
for label in ('source', 'raw'):
    path = HERE / f'{label}.tar.gz'
    assert digest(path.read_bytes()) == manifest[label]['sha256']
    with tarfile.open(path) as archive:
        data = {m.name: archive.extractfile(m).read()
                for m in archive.getmembers() if m.isfile()}
    assert set(data) == set(manifest[label]['files'])
    assert all(digest(b) == manifest[label]['files'][n] for n, b in data.items())
    packs[label] = data
source, raw = packs['source'], packs['raw']
freeze = read(HERE / 'freeze.json')
assert set(source) == set(freeze['files'])
assert all(digest(source[p]) == h for p, h in freeze['files'].items())
get = lambda n: json.loads(source[PREFIX + n])
cases = {c['id']: c for c in get('inputs.json')}
expected, plan = get('expected.json'), get('plan.json')
tree = ast.parse(source['results/evidence/description-factor-20261101/generate.py'])
prompt = next(ast.literal_eval(n.value) for n in tree.body
              if isinstance(n, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == 'PROMPT' for t in n.targets))
ledger = json.loads(raw['updater-ledger.json'])
assert len(ledger['requests']) == 8 and not ledger['blocked']
assert Decimal(ledger['unknown_reserved_usd']) == 0
assert len(plan['schedule']) == len({(r['case_id'], r['repeat']) for r in plan['schedule']}) == 8
cost, ids, rows = Decimal('0'), [], []
for item in plan['schedule']:
    a = json.loads(raw[item['run_id'] + '.json'])
    case, e = cases[item['case_id']], expected[item['case_id']]
    assert all(a[k] == v for k, v in item.items())
    assert len(a['attempts']) == 1 and not a.get('transport_retries')
    assert a['status'] == 'structurally_valid'
    rec = a['attempts'][0]
    assert rec['request'] == [
        {'role': 'system', 'content': prompt},
        {'role': 'user', 'content': json.dumps(case['input'], ensure_ascii=False)}]
    response = rec['response']
    assert response['provider'] == 'DigitalOcean'
    assert response['choices'][0]['finish_reason'] == 'stop'
    proposal = json.loads(response['choices'][0]['message']['content'])
    assert proposal == a['proposal']
    ids.append(response['id'])
    cost += Decimal(str(response['usage']['cost']))
    tool = case['target']['tools'][0]
    lines = tool['description'].splitlines()
    deleted = set()
    for d in proposal['deletions']:
        assert d['tool_id'] == tool['tool_id']
        assert all(isinstance(n, int) and 0 <= n < len(lines) for n in d['lines'])
        assert not deleted.intersection(d['lines'])
        deleted.update(d['lines'])
    for d in proposal['deletions']:
        for coverage in d['coverage']:
            if coverage['kind'] == 'description':
                assert not deleted.intersection(coverage['lines'])
                assert coverage['quote'] == '\n'.join(lines[n] for n in coverage['lines'])
            else:
                assert coverage['kind'] == 'parameters'
                value = tool['parameters']
                for part in coverage['path']:
                    value = value[part]
                assert coverage['quote'] == value
    # Reconstruct the only allowed mutation without importing the production compiler.
    candidate = deepcopy(case['target'])
    candidate['tools'][0]['description'] = ''.join(
        line for n, line in enumerate(tool['description'].splitlines(keepends=True))
        if n not in deleted)
    assert a['knowledge']['tools'] == candidate['tools']
    removed = len(tool['description']) - len(candidate['tools'][0]['description'])
    retained = not deleted.intersection(e['unique_lines'])
    if e['category'] == 'exact_duplicate':
        retained = retained and not {1, 2}.issubset(deleted)
    passed = retained and (removed >= 500 if e['positive'] else removed == 0)
    rows.append({**item, 'category': e['category'], 'positive': e['positive'],
                 'status': a['status'], 'deleted_lines': sorted(deleted),
                 'characters_removed': removed, 'unique_information_retained': retained,
                 'control_pass': passed, 'attempts': 1})
assert len(ids) == len(set(ids)) == 8
assert set(ids) == {r['response_id'] for r in ledger['requests']}
assert all(r['status'] == 'settled' and r['actual_provider'] == 'DigitalOcean'
           for r in ledger['requests'])
decision = json.loads(raw['decision.json'])
assert decision == read(HERE / 'decision.json') and decision['rows'] == rows
assert cost == Decimal(ledger['known_usd']) == Decimal(decision['known_usd'])
assert decision['positive_passes'] == sum(r['control_pass'] for r in rows if r['positive']) == 3
assert decision['negative_passes'] == sum(r['control_pass'] for r in rows if not r['positive']) == 2
assert decision['api_requests'] == 8 and decision['unknown_cost_items'] == 0
assert all(decision[k] == 0 for k in ('actor_calls', 'native_calls', 'judge_calls'))
assert not decision['original_candidate_promoted'] and not decision['goal_complete']
print(json.dumps({'verified': True, 'source_files': len(source), 'raw_files': len(raw),
                  'updater_requests': len(ids), 'known_usd': str(cost),
                  'unknown_cost_items': 0, 'positive_passes': '3/4',
                  'negative_passes': '2/4', 'unsafe_outputs': 3,
                  'decision': 'closed_failed_elementary_control_gate', 'goal_complete': False}))

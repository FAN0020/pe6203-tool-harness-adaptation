"""Standard-library, read-only archive/request/decision verification."""
import ast
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import tarfile
HERE = Path(__file__).resolve().parent
PREFIX = 'results/evidence/verified-coverage-20261101/'
read = lambda p: json.loads(p.read_text())
sha = lambda b: hashlib.sha256(b).hexdigest()
manifest = read(HERE / 'archive-manifest.json')
packs = {}
for label in ('source', 'raw'):
    path = HERE / (label + '.tar.gz')
    assert sha(path.read_bytes()) == manifest[label]['sha256']
    with tarfile.open(path) as archive:
        data = {m.name: archive.extractfile(m).read() for m in archive.getmembers() if m.isfile()}
    assert set(data) == set(manifest[label]['files'])
    assert all(sha(b) == manifest[label]['files'][p] for p, b in data.items())
    packs[label] = data
source, raw = packs['source'], packs['raw']
freeze = read(HERE / 'freeze.json')
assert set(source) == set(freeze['files'])
assert all(sha(source[p]) == h for p, h in freeze['files'].items())
tree = ast.parse(source[PREFIX + 'study.py'])
prompt = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == 'PROPOSE' for t in n.targets))
inputs = json.loads(source[PREFIX + 'inputs.json'])
ids, cost = [], Decimal('0')
for stage in ('middle', 'late'):
    a = json.loads(raw[stage + '-producer-audit.json'])
    expected_request = [{'role': 'system', 'content': prompt},
                        {'role': 'user', 'content': json.dumps(inputs[stage], ensure_ascii=False)}]
    assert a['attempts'][0]['request'] == expected_request
    assert not a.get('transport_retries')
    for rec in a['attempts']:
        r = rec['response']; ids.append(r['id']); cost += Decimal(str(r['usage']['cost']))
        assert r['provider'] == 'DigitalOcean' and r['choices'][0]['finish_reason'] == 'stop'
    if stage == 'middle':
        assert a['status'] == 'structural_rejection' and len(a['attempts']) == 2
        by_id = {t['tool_id']: t for t in inputs[stage]['tools']}
        for rec in a['attempts']:
            graph = json.loads(rec['response']['choices'][0]['message']['content'])
            assert len(graph['relations']) == 50
            assert any(s['kind'] == 'description' and s['line'] >= len(by_id[r['tool_id']]['description_lines'])
                       for r in graph['relations'] for s in r['support'])
    else:
        assert a['status'] == 'structurally_valid' and len(a['attempts']) == 1
        assert a['value'] == {'relations': []}
        report = json.loads(raw['late-report.json'])
        assert report['selected'] == report['checks'] == report['deletion_log'] == []
        assert report['feedback'] == {'checks': []}
ledger = json.loads(raw['updater-ledger.json'])
assert len(ids) == len(set(ids)) == len(ledger['requests']) == 3
assert set(ids) == {r['response_id'] for r in ledger['requests']}
assert all(r['status'] == 'settled' and r['actual_provider'] == 'DigitalOcean' for r in ledger['requests'])
assert not ledger['blocked'] and Decimal(ledger['unknown_reserved_usd']) == 0
decision = json.loads(raw['generation-decision.json'])
assert decision == read(HERE / 'generation-decision.json')
assert cost == Decimal(ledger['known_usd']) == Decimal(decision['known_usd'])
assert not any(s['manipulation_pass'] for s in decision['stages'])
assert all(decision[k] == 0 for k in ('actor_calls', 'judge_calls', 'native_calls'))
assert read(HERE / 'interpretation.json')['decision'] == 'reject_generation_v1_no_original_trial'
print(json.dumps({'verified': True, 'source_files': len(source), 'raw_files': len(raw),
                  'updater_requests': len(ids), 'checker_requests': 0, 'known_usd': str(cost),
                  'unknown_cost_items': 0, 'decision': 'reject_generation_v1_no_original_trial',
                  'goal_complete': False}))

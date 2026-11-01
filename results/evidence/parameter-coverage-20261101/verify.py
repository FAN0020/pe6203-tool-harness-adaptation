"""Read-only standard-library verification of frozen inputs, outputs and costs."""
import ast
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import tarfile
HERE = Path(__file__).resolve().parent
PREFIX = 'results/evidence/parameter-coverage-20261101/'
read = lambda p: json.loads(p.read_text())
sha = lambda b: hashlib.sha256(b).hexdigest()
manifest = read(HERE / 'archive-manifest.json'); packs = {}
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
inputs = json.loads(source[PREFIX + 'inputs.json'])
pairs = json.loads(source[PREFIX + 'pairs.json'])
cats = json.loads(source['tests/fixtures/dependency-cut-catalogs.json'])
tree = ast.parse(source['results/evidence/verified-coverage-20261101/study.py'])
prompt = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == 'CHECK' for t in n.targets))
ids, cost, selected_keys = [], Decimal('0'), set()
decision = json.loads(raw['generation-decision.json'])
for stage, expected_removed in (('middle', 323), ('late', 366)):
    a = json.loads(raw[stage + '-checker-audit.json'])
    assert len(a['attempts']) == 1 and not a.get('transport_retries')
    assert a['status'] == 'structurally_valid'
    rec = a['attempts'][0]
    assert rec['request'] == [{'role': 'system', 'content': prompt},
                              {'role': 'user', 'content': json.dumps(inputs[stage], ensure_ascii=False)}]
    r = rec['response']; ids.append(r['id']); cost += Decimal(str(r['usage']['cost']))
    assert r['provider'] == 'DigitalOcean' and r['choices'][0]['finish_reason'] == 'stop'
    fb = json.loads(r['choices'][0]['message']['content'])
    assert fb == a['value']
    report = json.loads(raw[stage + '-report.json'])
    assert report['pairs'] == pairs[stage] and report['feedback'] == fb
    selected = {x['id'] for x in fb['checks'] if not x['missing_claims'] and x['uncertain'] is False}
    assert selected == set(report['selected'])
    actual = json.loads(raw[stage + '-knowledge.json'])
    old = {t['tool_id']: t for t in cats['early']['tools']}
    new = {t['tool_id']: t for t in cats[stage]['tools']}
    # In this rule-free fixture SP keeps unchanged Early records and their order,
    # patches changed records, then appends added records in identity order.
    assert all(not t['usage_rules'] for t in [*old.values(), *new.values()])
    fields = ('name', 'parameters', 'description', 'output_schema', 'routing')
    expected = [deepcopy(new[tid] if any(t[f] != new[tid][f] for f in fields) else t)
                for tid, t in old.items() if tid in new]
    expected += [deepcopy(new[tid]) for tid in sorted(new.keys() - old.keys())]
    by_id = {t['tool_id']: t for t in expected}
    removals = {}
    for pair, check in zip(pairs[stage], inputs[stage]['checks']):
        tool = by_id[pair['tool_id']]
        assert pair['schema'] == tool['parameters']['properties'][pair['parameter']]
        assert pair['claim'] == tool['description'].splitlines()[pair['line']]
        assert check == {'id': pair['id'], 'claim': pair['claim'],
                         'evidence': [{'parameter': pair['parameter'], 'schema': pair['schema']}]}
        if pair['id'] in selected:
            removals.setdefault(pair['tool_id'], set()).add(pair['line'])
            selected_keys.add((stage, pair['id']))
    removed = 0
    for tool in expected:
        before = tool['description']
        tool['description'] = ''.join(s for n, s in enumerate(before.splitlines(keepends=True))
                                      if n not in removals.get(tool['tool_id'], set()))
        removed += len(before) - len(tool['description'])
    assert actual == {'schema_version': cats[stage]['schema_version'],
                      'benchmark_commit': cats[stage]['benchmark_commit'],
                      'version': stage, 'tools': expected}
    assert removed == expected_removed
    row = next(x for x in decision['stages'] if x['stage'] == stage)
    assert row['characters_removed'] == removed and not row['manipulation_pass']
ledger = json.loads(raw['updater-ledger.json'])
assert len(ids) == len(set(ids)) == len(ledger['requests']) == 2
assert set(ids) == {r['response_id'] for r in ledger['requests']}
assert all(r['status'] == 'settled' and r['actual_provider'] == 'DigitalOcean' for r in ledger['requests'])
assert not ledger['blocked'] and Decimal(ledger['unknown_reserved_usd']) == 0
assert cost == Decimal(ledger['known_usd']) == Decimal(decision['known_usd'])
assert decision == read(HERE / 'generation-decision.json')
review = json.loads(raw['semantic-review.json'])
assert {(r['stage'], r['id']) for r in review['rows']} == selected_keys
assert len(selected_keys) == 11 and all(r['verdict'] == 'pass' for r in review['rows'])
assert not review['version_admitted'] and not review['goal_complete']
assert all(decision[k] == 0 for k in ('actor_calls', 'judge_calls', 'native_calls'))
print(json.dumps({'verified': True, 'source_files': len(source), 'raw_files': len(raw),
                  'requests': len(ids), 'known_usd': str(cost), 'unknown_cost_items': 0,
                  'selected_lines_reviewed': len(selected_keys), 'removed_characters': [323, 366],
                  'decision': 'reject_generation_v1_below_frozen_size_gate', 'goal_complete': False}))

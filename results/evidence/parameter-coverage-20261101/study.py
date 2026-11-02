"""Two frozen metadata-only gap checks with host-generated same-field pairs."""
from decimal import Decimal
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from pe6203.parameter_coverage import parameter_pairs, compile_parameter_coverage
from pe6203.selective import adapt_result
from pe6203.experiment import verify_files

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE_PATH = ROOT / 'results/evidence/verified-coverage-20261101/study.py'
module_spec = importlib.util.spec_from_file_location('frozen_coverage_request_helper', BASE_PATH)
base = importlib.util.module_from_spec(module_spec); module_spec.loader.exec_module(base)
# Reuse the frozen audited request/repair helper, directing its new audits here.
# No previous file or ledger is modified.
base.HERE = HERE
load = lambda p: json.loads(p.read_text())
def save(p, x): p.write_text(json.dumps(x, ensure_ascii=False, indent=2) + '\n')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def prepare():
    assert not (HERE / 'freeze.json').exists()
    cats = load(ROOT / 'tests/fixtures/dependency-cut-catalogs.json')
    inputs, graphs, inventory = {}, {}, {}
    for stage in ('middle', 'late'):
        pairs = parameter_pairs(cats['early'], cats[stage]); graphs[stage] = pairs
        assert pairs
        inputs[stage] = {'checks': [{'id': p['id'], 'claim': p['claim'],
                                    'evidence': [{'parameter': p['parameter'], 'schema': p['schema']}]}
                                   for p in pairs]}
        inventory[stage] = {'pairs': len(pairs), 'maximum_description_characters_removed': sum(len(p['claim']) + 1 for p in pairs), 'warning': 'Upper bound only, not semantic approval; no manual pair selection.'}
    save(HERE / 'inputs.json', inputs); save(HERE / 'pairs.json', graphs); save(HERE / 'inventory.json', inventory)
    for suffix in ('updater', 'dev', 'validation-1', 'validation-2'):
        text = (ROOT / f'configs/verified-coverage-{suffix}-v1.json').read_text()
        text = text.replace('verified-coverage', 'parameter-coverage').replace('verified_coverage', 'parameter_coverage')
        config = json.loads(text)
        if suffix == 'updater': assert not (ROOT / config['spend_guard']['ledger']).exists()
        save(ROOT / f'configs/parameter-coverage-{suffix}-v1.json', config)
    text = (ROOT / 'experiments/verified-coverage-v1.json').read_text()
    spec = json.loads(text.replace('verified-coverage', 'parameter-coverage').replace('verified_coverage', 'parameter_coverage'))
    spec['id'] = 'parameter-coverage-v1'
    spec['generation'] = {
        'mechanism': 'The host enumerates every eligible parameter bullet whose exact parameter name exists in the same changed tool schema. It supplies the complete original property schema. The fixed LLM only lists missing claims or uncertainty; the host deletes a line iff both are empty/false. No model-generated source references or operations.',
        'input': 'Only claims and same-field schemas from original changed/added metadata. No benchmark questions, answers, scored trajectories or labels. Pair rule is uniform; no selection from the prior failed model outputs.',
        'rule': 'Use existing standalone bullet/numbered-line eligibility, then match ^- ([A-Za-z_][A-Za-z_0-9]*): followed by nonempty text. Require the named property to be an object with nonempty string description. All matches in catalog/line order are included. Complete schema includes types, enums and constraints; never altered.',
        'calls': 'One fresh-context checker per Middle then Late, unchanged CHECK prompt from a174fa1. Existing one structural repair and one transport retry only. Complete both stages unless infrastructure/unknown charge stops. No semantic retry, best-of or regeneration.',
        'semantic_gate': 'Main agent reviews every selected deletion against its exact complete same-field schema. Any missing unique qualifier, condition, limitation, example or recommendation rejects the whole version; no manual selection or edits afterward.',
        'manipulation_gate': 'At least 500 Unicode characters removed in each stage and strict serialized-knowledge size reduction; feasibility only, not evidence of actor gains.',
        'next': 'Only both stages passing all gates permit registration of exact reviewed candidate bytes, a new frozen 10-cell original plan and original development. Preserve the same strict gates and two 30-cell independent validation blocks.'}
    spec['execution_order'] = spec['generation']['calls'] + ' Conditional original execution uses the existing fixed task pairs and schedule rules.'
    spec['literature'] = {'new_record': str((HERE / 'research-decision.json').relative_to(ROOT)), 'pinned_prior_record': 'results/evidence/verified-coverage-20261101/research-decision.json', 'source_pins': 'results/evidence/verified-coverage-20261101/source-pins.json'}
    spec['cost'] = 'Independent updater/dev/validation1/validation2 ledgers; generation estimate USD 0.003–0.03, not a cap. No new total budget.'
    save(ROOT / 'experiments/parameter-coverage-v1.json', spec)
    paths = [str(p.relative_to(ROOT)) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in str(p)]
    paths += ['src/pe6203/parameter_coverage.py', 'src/pe6203/verified_coverage.py', 'src/pe6203/description_factor.py', 'src/pe6203/selective.py', 'src/pe6203/request_retry.py', 'src/pe6203/spend_guard.py', 'integration/baselines.py', 'tests/test_parameter_coverage.py', 'tests/fixtures/dependency-cut-catalogs.json', 'experiments/parameter-coverage-v1.json', str(BASE_PATH.relative_to(ROOT)), 'results/evidence/verified-coverage-20261101/research-decision.json', 'results/evidence/verified-coverage-20261101/source-pins.json']
    paths += [f'configs/parameter-coverage-{s}-v1.json' for s in ('updater', 'dev', 'validation-1', 'validation-2')]
    save(HERE / 'freeze.json', {'files': {p: sha(ROOT / p) for p in sorted(set(paths))}, 'model_calls': 0})
    print(json.dumps({'inventory': inventory, 'source_files': len(set(paths)), 'model_calls': 0}))

def run():
    verify_files(ROOT, load(HERE / 'freeze.json')['files'])
    cats = load(ROOT / 'tests/fixtures/dependency-cut-catalogs.json')
    inputs = load(HERE / 'inputs.json')
    settings = load(ROOT / 'configs/parameter-coverage-updater-v1.json'); settings['allow_metadata_api'] = True
    for stage in ('middle', 'late'):
        fb = base.call(stage + '-checker', base.CHECK, inputs[stage],
                       lambda x: compile_parameter_coverage(cats['early'], cats[stage], x), settings)
        if fb is None: continue
        knowledge, report = compile_parameter_coverage(cats['early'], cats[stage], fb)
        save(HERE / (stage + '-knowledge.json'), knowledge); save(HERE / (stage + '-report.json'), report)
        print(json.dumps({'stage': stage, 'selected': len(report['selected']), 'pairs': len(report['pairs'])}), flush=True)

def evaluate():
    verify_files(ROOT, load(HERE / 'freeze.json')['files'])
    cats = load(ROOT / 'tests/fixtures/dependency-cut-catalogs.json'); inputs = load(HERE / 'inputs.json')
    rows, ids, cost = [], [], Decimal('0')
    for stage in ('middle', 'late'):
        a = load(HERE / (stage + '-checker-audit.json'))
        assert a['attempts'][0]['request'] == [{'role': 'system', 'content': base.CHECK}, {'role': 'user', 'content': json.dumps(inputs[stage], ensure_ascii=False)}]
        for rec in a['attempts']:
            r = rec['response']; assert r['provider'] == 'DigitalOcean'
            ids.append(r['id']); cost += Decimal(str(r['usage']['cost']))
        if a['status'] != 'structurally_valid':
            rows.append({'stage': stage, 'status': a['status'], 'manipulation_pass': False}); continue
        knowledge, report = compile_parameter_coverage(cats['early'], cats[stage], a['value'])
        assert knowledge == load(HERE / (stage + '-knowledge.json')) and report == load(HERE / (stage + '-report.json'))
        sp = adapt_result(cats['early'], cats[stage])['knowledge']
        before = {t['tool_id']: t for t in sp['tools']}
        removed = sum(len(before[t['tool_id']]['description']) - len(t['description']) for t in knowledge['tools'])
        only_desc = json.loads(json.dumps(knowledge))
        for t in only_desc['tools']: t['description'] = before[t['tool_id']]['description']
        assert only_desc == sp
        smaller = len(json.dumps(knowledge, ensure_ascii=False)) < len(json.dumps(sp, ensure_ascii=False))
        rows.append({'stage': stage, 'status': a['status'], 'pairs': len(report['pairs']), 'selected': len(report['selected']), 'vetoes': len(report['pairs']) - len(report['selected']), 'characters_removed': removed, 'manipulation_pass': removed >= 500 and smaller})
    settings = load(ROOT / 'configs/parameter-coverage-updater-v1.json')
    ledger = load(ROOT / settings['spend_guard']['ledger'])
    assert len(ids) == len(set(ids)) == len(ledger['requests'])
    assert set(ids) == {r['response_id'] for r in ledger['requests']}
    assert cost == Decimal(ledger['known_usd']) and Decimal(ledger['unknown_reserved_usd']) == 0 and not ledger['blocked']
    decision = {'stages': rows, 'requests': len(ids), 'known_usd': str(cost), 'unknown_cost_items': 0, 'actor_calls': 0, 'judge_calls': 0, 'native_calls': 0, 'semantic_review_pending': True, 'goal_complete': False}
    save(HERE / 'generation-decision.json', decision); save(HERE / 'updater-ledger.json', ledger)
    print(json.dumps(decision))

if __name__ == '__main__': {'prepare': prepare, 'run': run, 'evaluate': evaluate}[sys.argv[1]]()

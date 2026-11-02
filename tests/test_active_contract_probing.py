from copy import deepcopy
import json
from pathlib import Path
import pytest
from pe6203.active_contract_probing import inventory, validate_probes, compile_decisions
from pe6203.selective import adapt_result

SERVER = '@pimzino/agentic-tools-mcp'

def cats():
    p = Path('tests/fixtures/dependency-cut-catalogs.json')
    d = json.loads(p.read_text())
    return d['early'], d['late']

def prepared():
    old, target = cats()
    data = inventory(old, target, SERVER)
    return old, target, data

def decision_rows(data):
    return [{'id': c['id'], 'action': 'retain', 'after': c['before'], 'evidence': [], 'reason': 'No established change.'} for c in data['claims']]

def probe(data):
    root = next(t for t in data['changed_ids'] if t.endswith('::create_project'))
    return {'id': 'P1', 'basis': root, 'tool_id': root, 'arguments': {'workingDirectory': '$WORKSPACE', 'name': 'ProbeProject', 'description': 'Synthetic native record'}, 'question': 'Does the declared creation operation persist the supplied description?'}

def test_inventory_has_changed_only_claims_and_same_host_peers():
    old, target, data = prepared()
    assert data['claims'] and data['changed_ids']
    assert all(c['tool_id'] in data['changed_ids'] for c in data['claims'])
    assert all(t['server_id'] == SERVER for t in data['target']['tools'])
    assert all(c['path'] == 'description' or c['path'].endswith('.description') for c in data['claims'])

@pytest.mark.parametrize('bad', ['outside_path', 'unknown_tool', 'unchanged_basis', 'extra_top_field', 'too_many', 'duplicate_id'])
def test_probe_authority_and_workspace_guards(bad):
    _, _, data = prepared(); row = probe(data); payload = {'probes': [row]}
    if bad == 'outside_path': row['arguments']['workingDirectory'] = '/tmp/other'
    elif bad == 'unknown_tool': row['tool_id'] = SERVER + '::bulk_create_tasks'
    elif bad == 'unchanged_basis': row['basis'] = SERVER + '::create_task'
    elif bad == 'extra_top_field': payload['run_shell'] = 'anything'
    elif bad == 'too_many': payload['probes'] = [deepcopy(row) for _ in range(5)]
    else: payload['probes'].append(deepcopy(row))
    with pytest.raises(ValueError): validate_probes(data, payload)

def test_valid_probe_is_not_mutated_or_silently_filtered():
    _, _, data = prepared(); payload = {'probes': [probe(data)]}; before = deepcopy(payload)
    assert validate_probes(data, payload) == payload['probes']
    assert payload == before

def test_compiler_preserves_unrelated_records_and_requires_actual_probe_evidence():
    old, target, data = prepared(); rows = decision_rows(data)
    row = rows[0]; row.update(action='replace', after='A source-reviewed operational statement.', evidence=['P1'])
    candidate, edits = compile_decisions(old, target, data, {'decisions': rows}, {'P1'})
    assert len(edits) == 1
    c = data['claims'][0]; tool = next(t for t in candidate['tools'] if t['tool_id'] == c['tool_id'])
    node = tool
    for k in c['path'].split('.')[:-1]: node = node[k]
    node[c['path'].split('.')[-1]] = c['before']
    assert candidate == adapt_result(old, target)['knowledge']
    with pytest.raises(ValueError): compile_decisions(old, target, data, {'decisions': rows}, set())

@pytest.mark.parametrize('bad', ['missing', 'duplicate', 'retain_changes', 'empty_reason', 'extra_field'])
def test_invalid_decision_batch_fails_without_partial_edits(bad):
    old, target, data = prepared(); rows = decision_rows(data)
    if bad == 'missing': rows.pop()
    elif bad == 'duplicate': rows.append(deepcopy(rows[0]))
    elif bad == 'retain_changes': rows[0]['after'] += ' unsupported'
    elif bad == 'empty_reason': rows[0]['reason'] = ''
    else: rows[0]['parameters'] = {}
    with pytest.raises(ValueError): compile_decisions(old, target, data, {'decisions': rows}, {'P1'})


def test_full_snapshot_application_requires_review_and_preserves_absent_hosts():
    from pe6203.active_contract_probing import frozen_knowledge
    old,target,data=prepared(); rows=decision_rows(data)
    rows[0].update(action='replace',after='A reviewed operation.',evidence=['P1'])
    cert={'kind':'model_designed_native_probes_v1','semantic_review':'accepted','inventory':data,'payload':{'decisions':rows},'evidence_ids':['P1']}
    fb=[{'stage':'late','server':SERVER,'tool':'__active_probes__','args':{},'result':cert}]
    result,edits=frozen_knowledge(old,target,fb)
    expected,_=compile_decisions(old,target,data,{'decisions':rows},{'P1'})
    assert result==expected and len(edits)==1
    cert['semantic_review']='pending'
    with pytest.raises(ValueError):frozen_knowledge(old,target,fb)

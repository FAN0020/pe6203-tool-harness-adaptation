from copy import deepcopy
import json
from pathlib import Path
import pytest
from pe6203.selective import adapt_result
from pe6203.shared_contract_refs import compile_knowledge, expand_references


def catalogs():
    x=json.loads(Path('tests/fixtures/dependency-cut-catalogs.json').read_text())
    return x['early'],x['late']


def test_references_expand_exactly_and_preserve_unchanged_records():
    old,target=catalogs();base=adapt_result(old,target)
    knowledge,edits=compile_knowledge(old,target)
    assert edits
    assert expand_references(knowledge,edits)==base['knowledge']
    changed={r['tool_id'] for r in base['diff']['changed']+base['diff']['added']}
    originals={t['tool_id']:t for t in base['knowledge']['tools']}
    for t in knowledge['tools']:
        if t['tool_id'] not in changed:assert t==originals[t['tool_id']]
    assert all(e['tool_id'] in changed for e in edits)


def test_structural_schema_routes_order_and_anchor_text_are_preserved():
    old,target=catalogs();base=adapt_result(old,target)['knowledge']
    knowledge,edits=compile_knowledge(old,target)
    restored=deepcopy(knowledge)
    by={t['tool_id']:t for t in restored['tools']}
    for e in edits:
        anchor=by[e['anchor_tool_id']]['parameters']['properties'][e['parameter']]
        assert anchor['description']==e['before']
        by[e['tool_id']]['parameters']['properties'][e['parameter']]['description']=e['before']
    assert restored==base


def test_unchanged_catalog_is_identity():
    old,_=catalogs();result,edits=compile_knowledge(old,old)
    assert result==adapt_result(old,old)['knowledge'] and edits==[]


@pytest.mark.parametrize('mutation',['description','type','required','server'])
def test_inexact_or_different_scope_cannot_supply_anchor(mutation):
    old,target=catalogs()
    # Isolate a changed create_project and one unchanged potential witness.
    selected=['create_project','update_project']
    for c in [old,target]:c['tools']=[t for t in c['tools'] if t['name'] in selected]
    if mutation=='description':
        for c in [old,target]:next(t for t in c['tools'] if t['name']=='update_project')['parameters']['properties']['workingDirectory']['description']+=' Extra unique condition.'
    elif mutation=='type':
        for c in [old,target]:next(t for t in c['tools'] if t['name']=='update_project')['parameters']['properties']['workingDirectory']['type']='integer'
    elif mutation=='required':
        for c in [old,target]:next(t for t in c['tools'] if t['name']=='update_project')['parameters']['required'].remove('workingDirectory')
    else:
        for c in [old,target]:
            t=next(t for t in c['tools'] if t['name']=='update_project')
            t['server_id']='another-host';t['tool_id']='another-host::update_project'
            t['routing']['server_id']='another-host'
    _,edits=compile_knowledge(old,target)
    assert not any(e['parameter']=='workingDirectory' for e in edits)


def test_missing_or_changed_anchor_fails_expansion():
    old,target=catalogs();knowledge,edits=compile_knowledge(old,target)
    altered=deepcopy(knowledge)
    e=edits[0];next(t for t in altered['tools'] if t['tool_id']==e['anchor_tool_id'])['parameters']['properties'][e['parameter']]['description']='Changed after freeze'
    with pytest.raises(ValueError):expand_references(altered,edits)

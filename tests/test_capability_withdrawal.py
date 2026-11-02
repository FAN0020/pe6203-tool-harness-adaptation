"""Scope and deletion certificates must fail closed, without touching other tools."""
import json
from copy import deepcopy
from pathlib import Path

import pytest

from pe6203.capability_withdrawal import compile_knowledge
from pe6203.selective import adapt_result


def inputs():
    cats = json.loads(Path('tests/fixtures/capability-withdrawal-catalogs.json').read_text())
    feedback = json.loads(Path('experiments/capability-withdrawal-feedback-v1.json').read_text())['observations']
    return cats['early'], cats['late'], feedback


def test_withdrawal_restricts_only_certified_tools_and_explicit_reference_sentences():
    old, target, feedback = inputs()
    pristine = deepcopy((old, target, feedback))
    base = adapt_result(old, target)
    result, changes = compile_knowledge(base, target, feedback, withdraw=True)
    original = {t['tool_id']: t for t in base['knowledge']['tools']}
    actual = {t['tool_id']: t for t in result['tools']}
    cert = feedback[0]['result']
    assert set(original) - set(actual) == {c['tool_id'] for c in cert['certificates']}
    edited = {r['tool_id']: r for r in cert['reference_edits']}
    for identity, tool in actual.items():
        expected = deepcopy(original[identity])
        if identity in edited:
            expected['description'] = edited[identity]['after']
        assert tool == expected
    assert len(changes) == 8
    assert (old, target, feedback) == pristine


def test_warning_ablation_retains_every_route_and_matches_shared_reference_cleanup():
    old, target, feedback = inputs()
    base = adapt_result(old, target)
    warning, _ = compile_knowledge(base, target, feedback, withdraw=False)
    withdrawn, _ = compile_knowledge(base, target, feedback, withdraw=True)
    ids = {t['tool_id'] for t in withdrawn['tools']}
    assert [t for t in warning['tools'] if t['tool_id'] in ids] == withdrawn['tools']
    assert len(warning['tools']) == len(base['knowledge']['tools'])


@pytest.mark.parametrize('mutation', ['cert', 'scope', 'source', 'missing', 'catalog', 'recommendation'])
def test_uncertified_changes_cannot_enter_actor_knowledge(mutation):
    old, target, feedback = inputs()
    if mutation == 'cert': feedback[0]['result']['certificates'][0]['warning'] += ' forged'
    elif mutation == 'scope': feedback[0]['result']['certificates'][0]['tool_id'] = 'unrelated::tool'
    elif mutation == 'source': feedback[0]['result']['sources'][0]['sha256'] = 'wrong'
    elif mutation == 'missing': feedback = []
    elif mutation == 'catalog': target['tools'][0]['description'] += ' unknown release'
    else: feedback[0]['result']['reference_edits'][0]['after'] += ' invented fallback'
    with pytest.raises(ValueError):
        compile_knowledge(adapt_result(old, target), target, feedback, withdraw=True)


def test_unchanged_and_other_server_knowledge_are_byte_equal_to_sp():
    old, _, _ = inputs()
    base = adapt_result(old, old)
    assert compile_knowledge(base, old, [], withdraw=True) == (base['knowledge'], [])
    cats = json.loads(Path('tests/fixtures/prefix-workflow-catalogs.json').read_text())['235']
    base = adapt_result(cats['early'], cats['late'])
    assert compile_knowledge(base, cats['late'], [], withdraw=True) == (base['knowledge'], [])

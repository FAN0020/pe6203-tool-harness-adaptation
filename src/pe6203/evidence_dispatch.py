"""Select source-backed repair/deletion operations without task-conditioned routing."""
from copy import deepcopy
import hashlib

from .selective import adapt_result, canonical
from .semantic_contract_maintenance import frozen_patch
from .reviewed_coverage import HOSTS, compile_knowledge as compact

MATH_ROOTS = {'math-mcp::validate_syntax', 'math-mcp::batch_evaluate'}
SEMANTIC_POLICIES = {
    'middle': 'c1c063299d160b52a4005672e8d163737eb08f099b56e8c791cea08fcd7404ce',
    'late': 'acbc6c5ece76a097a37c61ec562075da0166e2cc8b0cf285b47e5f2ee3c1e43f',
}


def compile_knowledge(old, target, feedback):
    base = adapt_result(old, target)
    knowledge = deepcopy(base['knowledge'])
    changed = {r['tool_id'] for r in base['diff']['changed'] + base['diff']['added']}
    policies = []
    if changed & MATH_ROOTS:
        rows = [r for r in feedback if r.get('stage') == target['version'] and r.get('server') == 'math-mcp']
        if len(rows) != 1 or hashlib.sha256(canonical(rows[0]['result']).encode()).hexdigest() != SEMANTIC_POLICIES.get(target['version']):
            raise ValueError('Exact reviewed claim-repair certificate required')
        policies.append(('claim_repair', *frozen_patch(old, target, feedback, False)))
    if changed & HOSTS:
        policies.append(('coverage', *compact(base, target, feedback)))
    before = {t['tool_id']: t for t in base['knowledge']['tools']}
    replacements = {}; edits = []
    for policy, candidate, log in policies:
        if [t['tool_id'] for t in candidate['tools']] != list(before):
            raise ValueError('Policy changed tool identity/order')
        for tool in candidate['tools']:
            tid = tool['tool_id']
            if tool == before[tid]: continue
            if tid not in changed or tid in replacements:
                raise ValueError('Overlapping or unrelated policy edit')
            replacements[tid] = deepcopy(tool)
        edits.extend(dict(row, policy=policy) for row in log)
    knowledge['tools'] = [replacements.get(t['tool_id'], t) for t in knowledge['tools']]
    return knowledge, edits

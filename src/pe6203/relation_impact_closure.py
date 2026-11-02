"""Distribute certified relation updates only to their two proven endpoint owners."""
import json
from copy import deepcopy

from .capability_relations import HOST
from .relation_witness_basis import compile_knowledge as compile_basis

NEIGHBOR = 'math-mcp::evaluate'
OWNERS = {'syntax_envelope': HOST, 'syntax_valid': HOST,
          'evaluated': NEIGHBOR, 'numeric_value': NEIGHBOR}


def compile_knowledge(base, target, feedback):
    # This validates the exact approved native certificate and BOTH catalog hashes.
    knowledge, root_edits = compile_basis(base, target, feedback)
    if not root_edits:
        return knowledge, []
    tools = {t['tool_id']: t for t in knowledge['tools']}
    if NEIGHBOR not in tools:
        raise ValueError('Certified relation endpoint missing')
    original = {t['tool_id']: t for t in base['knowledge']['tools']}
    note = json.loads(tools[HOST]['usage_rules'][-1].split(': ',1)[1])
    tools[HOST]['usage_rules'] = deepcopy(original[HOST]['usage_rules'])
    changes = []
    for identity in (HOST, NEIGHBOR):
        local = deepcopy(note)
        local['kind'] = 'predicate_owned_relation_closure'
        local['host_tool'] = identity
        local['relation_ownership'] = dict(OWNERS)
        local['relations'] = [edge for edge in note['relations'] if OWNERS[edge['if']] == identity]
        local['scope'] += ' This entry hosts only relations whose antecedent it owns. The two certified entries jointly retain the full finite relation set; no other tool is authorized by this edge.'
        before = deepcopy(tools[identity]['usage_rules'])
        tools[identity]['usage_rules'].append('Cross-operation evidence: '+json.dumps(local,ensure_ascii=False,separators=(',',':')))
        changes.append({'tool_id':identity,'field':'usage_rules','before':before,
                        'after':deepcopy(tools[identity]['usage_rules']),
                        'reason':'predicate-owned update closure over exact source/native-certified endpoints'})
    return knowledge, changes

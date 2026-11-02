"""Host-constructed same-field coverage pairs; LLM supplies only gap feedback."""
from copy import deepcopy
import re
from .selective import adapt_result
from .verified_coverage import make_inventory


def parameter_pairs(old, target):
    pairs = []
    for record in make_inventory(old, target):
        properties = record['parameters'].get('properties', {})
        for line in record['eligible_lines']:
            claim = record['description_lines'][line]
            match = re.match(r'^- ([A-Za-z_][A-Za-z_0-9]*):\s*(.+)$', claim)
            if not match:
                continue
            field = match[1]
            schema = properties.get(field)
            if not isinstance(schema, dict) or not isinstance(schema.get('description'), str) or not schema['description'].strip():
                continue
            pairs.append({'id': f'P{len(pairs) + 1:03d}', 'tool_id': record['tool_id'],
                          'line': line, 'parameter': field, 'claim': claim, 'schema': deepcopy(schema)})
    return pairs


def compile_parameter_coverage(old, target, feedback):
    pairs = parameter_pairs(old, target)
    if not isinstance(feedback, dict) or set(feedback) != {'checks'} or not isinstance(feedback['checks'], list):
        raise ValueError('Expected checks only')
    reviewed = {}
    for row in feedback['checks']:
        if not isinstance(row, dict) or set(row) != {'id', 'missing_claims', 'uncertain'}:
            raise ValueError('Invalid check fields')
        if not isinstance(row['id'], str) or row['id'] in reviewed or type(row['uncertain']) is not bool:
            raise ValueError('Invalid/duplicate ID or uncertainty')
        if not isinstance(row['missing_claims'], list) or any(not isinstance(s, str) or not s.strip() for s in row['missing_claims']):
            raise ValueError('Invalid missing claims')
        reviewed[row['id']] = row
    if set(reviewed) != {p['id'] for p in pairs}:
        raise ValueError('Every supplied pair must be reviewed exactly once')
    selected = [p for p in pairs if not reviewed[p['id']]['missing_claims'] and not reviewed[p['id']]['uncertain']]
    knowledge = deepcopy(adapt_result(old, target)['knowledge'])
    removed = {}
    for p in selected:
        removed.setdefault(p['tool_id'], set()).add(p['line'])
    for tool in knowledge['tools']:
        if tool['tool_id'] in removed:
            tool['description'] = ''.join(line for n, line in enumerate(tool['description'].splitlines(keepends=True))
                                          if n not in removed[tool['tool_id']])
            if not tool['description'].strip():
                raise ValueError('Empty description')
    return knowledge, {'pairs': pairs, 'feedback': deepcopy(feedback), 'selected': [p['id'] for p in selected]}

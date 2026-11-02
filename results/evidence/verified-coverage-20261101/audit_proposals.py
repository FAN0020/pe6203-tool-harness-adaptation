"""Post hoc structural audit of all visible relations; no model requests."""
import json
from collections import Counter
from pathlib import Path
from pe6203.verified_coverage import prepare_checks
HERE = Path(__file__).resolve().parent
load = lambda p: json.loads(p.read_text())
inputs = load(HERE / 'inputs.json')
rows = []
for stage in ('middle', 'late'):
    audit = load(HERE / (stage + '-producer-audit.json'))
    for attempt in audit['attempts']:
        graph = json.loads(attempt['response']['choices'][0]['message']['content'])
        errors, examples, valid = Counter(), [], 0
        for relation in graph['relations']:
            try:
                prepare_checks(inputs[stage]['tools'], {'relations': [relation]})
                valid += 1
            except (ValueError, TypeError, KeyError, IndexError) as exc:
                errors[str(exc)] += 1
                if len(examples) < 4:
                    record = next(r for r in inputs[stage]['tools'] if r['tool_id'] == relation['tool_id'])
                    examples.append({'relation': relation, 'description_line_count': len(record['description_lines']), 'error': str(exc)})
        rows.append({'stage': stage, 'attempt': attempt['attempt'], 'relations': len(graph['relations']), 'individually_structurally_valid': valid, 'errors': dict(errors), 'first_errors': examples})
result = {'rows': rows, 'scope': 'Post hoc structural projection only. Individually valid relations are not semantic approvals, cannot be selected into a candidate, and do not change the frozen whole-output rejection.'}
(HERE / 'proposal-audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps([{k: v for k, v in r.items() if k != 'first_errors'} for r in rows]))

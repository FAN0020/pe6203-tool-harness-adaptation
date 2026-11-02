"""Read-only task-free exact-coverage inventory; writes its own evidence only."""
import hashlib
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
path = ROOT / 'results/evidence/description-factor-20261101/updater-inputs.json'

def strings(x, path=()):
    if isinstance(x, str): yield path, x
    elif isinstance(x, dict):
        for k, v in x.items(): yield from strings(v, path + (k,))
    elif isinstance(x, list):
        for k, v in enumerate(x): yield from strings(v, path + (str(k),))

stages = {}
for stage, data in json.loads(path.read_text()).items():
    rows = []
    for t in data['tools']:
        lines = t['description_lines']
        schemas = [(kind, p, v) for kind in ('parameters', 'output_schema') for p, v in strings(t[kind])]
        matches = []
        for i, line in enumerate(lines):
            if not line.strip(): continue
            duplicate = next((j for j, s in enumerate(lines) if j < i and s == line), None)
            schema = next(((k, p) for k, p, v in schemas if line == v), None)
            if duplicate is not None or schema is not None:
                matches.append({'line': i, 'characters': len(line), 'earlier_duplicate': duplicate, 'schema': schema})
        rows.append({'tool_id': t['tool_id'], 'description_characters_excluding_newlines': sum(map(len, lines)), 'exact_covered_lines': matches})
    stages[stage] = rows
result = {'source': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'rule': 'Nonblank complete line identical to an earlier same-tool line or a complete same-tool schema string; no normalization, semantic inference or substring matching.', 'stages': stages, 'total_matches': sum(len(r['exact_covered_lines']) for rows in stages.values() for r in rows), 'scope': 'Static feasibility inventory, not a new model experiment and not proof that semantic coverage is absent.'}
(HERE / 'exact-inventory.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'total_matches': result['total_matches'], 'stage_records': {s: len(r) for s, r in stages.items()}}))

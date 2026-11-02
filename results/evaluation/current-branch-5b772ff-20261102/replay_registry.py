"""Re-evaluate the frozen 36-candidate inventory; no provider or MCP calls.

Only metadata, existing visible judge ratings, product judgments, and costs are
exported. Original conclusions and files are never overwritten.
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from scripts import research_reaudit as audit

OLD = ROOT / 'results/evidence/unified-reaudit-20261102'

def read(p):
    return json.loads(p.read_text())

def main():
    old_rows = read(OLD/'cells.json')
    old_by_id = {(r['cohort'], r['cell_id']): r for r in old_rows}
    cohorts = read(OLD/'cohorts.json')
    rows, receipts, errors = [], [], []
    for saved in cohorts:
        folder = ROOT/saved['path']
        plan = read(folder/'plan.json')
        if audit.sha(folder/'plan.json') != saved['plan_sha256']:
            errors.append({'cohort': saved['path'], 'error': 'plan_changed'})
        lock = audit.read(folder/'knowledge-lock.json', {})
        for n, digest in lock.get('files', {}).items():
            if not (folder/n).exists() or audit.sha(folder/n) != digest:
                errors.append({'cohort': saved['path'], 'error': 'knowledge_lock_changed', 'file': n})
        reviews = audit.review_index(folder)
        for cell in plan['cells']:
            row, ids = audit.inspect_cell(folder, plan, cell, reviews)
            old = old_by_id[(saved['path'], cell['id'])]
            differences = {k: {'saved': old.get(k), 'recomputed': v}
                           for k, v in row.items() if old.get(k) != v}
            if differences:
                errors.append({'cohort': saved['path'], 'cell_id': cell['id'], 'differences': differences})
            if row['audit_errors']:
                errors.append({'cohort': saved['path'], 'cell_id': cell['id'], 'errors': row['audit_errors']})
            row['condition_class'] = old['condition_class']
            row['protocol'] = old['protocol']
            rows.append(row)
            receipts.extend(ids)
    assert {(r['cohort'], r['cell_id']) for r in rows} == set(old_by_id)
    old_receipts = read(OLD/'response-receipts.json')
    assert receipts == old_receipts, 'raw receipt projection changed'
    assert len(audit.registry()) == 36
    result = {
        'integrity_pass': not errors, 'registered_candidates': 36,
        'cohorts': len(cohorts), 'planned_cells': len(rows),
        'executed_cells': sum(r['status'] != 'not_started' for r in rows),
        'judge_slots': sum(r['judge_slots'] for r in rows),
        'reviewed_products': sum(r['core_pass'] is not None for r in rows),
        'errors': errors, 'new_model_calls': 0, 'new_native_calls': 0,
        'method': 'Exact frozen cohort list; raw TF/PE slots, actor metadata, immutable knowledge, sourced prior product judgments.',
        'limitations': ['Existing semantic product judgments reused, not independently re-judged.',
                       'No new behavioral trial or independent validation.',
                       'Original, fixed-fixture, synthetic, and missing-input cases remain distinct.'],
        'inputs': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in [OLD/'cells.json', OLD/'cohorts.json', OLD/'response-receipts.json', ROOT/'scripts/research_reaudit.py']},
    }
    (HERE/'registry-replay.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    (HERE/'registry-cells.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('inputs', 'limitations')}, ensure_ascii=False))
    if errors:
        raise SystemExit(1)

if __name__ == '__main__':
    main()

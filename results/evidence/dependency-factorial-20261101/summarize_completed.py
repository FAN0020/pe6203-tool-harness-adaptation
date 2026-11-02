"""Reproduce descriptive phase/cost summaries without network, scores changes or reasoning text."""
import json
from decimal import Decimal
from pathlib import Path
E=Path(__file__).resolve().parent
rows=json.loads((E/'mechanism-projection.json').read_text()); d=json.loads((E/'decision.json').read_text()); phases=[]
for r,v in zip(rows,d['rows'],strict=True):
    groups={}
    for c in r['calls']:
        k='create' if c['tool'] in {'create_project','create_task'} else 'update' if c['tool']=='update_task' else 'read' if c['tool'] in {'list_tasks','get_task','get_project','get_task_hierarchy'} else 'other'
        g=groups.setdefault(k,{'calls':0,'rounds':set()});g['calls']+=1;g['rounds'].add(c['round'])
    groups={k:{'calls':v['calls'],'rounds':sorted(v['rounds'])} for k,v in groups.items()}
    assert sum(g['calls'] for g in groups.values())==v['tool_calls'] and len(r['responses'])==v['rounds']
    phases.append({'cell':r['cell_id'],'phases':groups,'errors':sum(c['error'] for c in r['calls']),'agent_completion_tokens':sum(x['completion_tokens'] for x in r['responses']),'rounds_at_4096':[x['round'] for x in r['responses'] if x['completion_tokens']==4096],'finish_length_rounds':[x['round'] for x in r['responses'] if x['finish_reason']=='length']})
(E/'phase-accounting.json').write_text(json.dumps(phases,indent=2)+'\n')
before=json.loads((E/'key-usage-before-a1.json').read_text());after=json.loads((E/'key-usage-after-a1.json').read_text());delta=Decimal(str(after['data']['usage']))-Decimal(str(before['metadata']['usage']))
a={'key_usage_delta_usd':str(delta),'continuation_settled_request_usd':d['new_known_usd_after_A1'],'difference_key_delta_minus_ledger_usd':str(delta-Decimal(d['new_known_usd_after_A1'])),'remaining_usd':str(after['data']['limit_remaining']),'key_limit_usd':after['data']['limit'],'key_cumulative_usage_usd':after['data']['usage'],'unknown_cost_items':d['unknown_cost_items'],'diagnostic_known_usd':d['known_usd'],'diagnostic_actual_total_usd':None,'conclusion':'Key aggregate is not a per-request reconciliation. Two captures are not exclusive-use evidence and their delta differs from response-level ledger. Neither the difference nor the balance settles the old unknown request. No causal attribution of discrepancy.','backup_activated':False,'read_only_inference_calls':0}
(E/'accounting-comparison.json').write_text(json.dumps(a,indent=2)+'\n')
print(json.dumps({'phase_rows':len(phases),'accounting':a},indent=2))

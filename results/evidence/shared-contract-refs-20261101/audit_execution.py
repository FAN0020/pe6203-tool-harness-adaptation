"""Post-review metadata/visible-call audit; never read or print reasoning text."""
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from raw_cell_verifier import archive_files

HERE=Path(__file__).resolve().parent


def main():
    decision=json.loads((HERE/'decision.json').read_text())
    files,manifest=archive_files(HERE);prefix=manifest['prefix']+'/'
    rows=[]
    for row in decision['rows']:
        trace=json.loads(files[prefix+'cells/'+row['cell_id']+'/run/raw_trace.json'])
        responses=[e['response'] for e in trace['events'] if e['type']=='agent_response']
        calls=[e for e in trace['events'] if e['type']=='tool_result']
        last=responses[-1]
        counts=Counter(e['call']['function']['name'].split('__')[0] for e in calls)
        errors=[{'tool':e['call']['function']['name'].split('__')[0],'result':e['result']} for e in calls if e['result'].get('isError')]
        rows.append({'review_id':row['review_id'],'task_id':row['task_id'],'stage':row['stage'],'strategy':row['strategy'],
                     'execution_status':row['execution_status'],'response_count':len(responses),
                     'finish_reason':last['choices'][0].get('finish_reason'),
                     'last_completion_tokens':last.get('usage',{}).get('completion_tokens'),
                     'last_reasoning_token_count':last.get('usage',{}).get('completion_tokens_details',{}).get('reasoning_tokens'),
                     'visible_final_characters':len(trace.get('answer') or ''),'call_counts':dict(counts),
                     'tool_errors':errors,'candidate_anchor_name':'list_projects' if row['stage']=='middle' else 'update_project',
                     'anchor_call_count':counts['list_projects' if row['stage']=='middle' else 'update_project'] if row['task_id']==283 else None})
    ledger=json.loads(files['results/raw/shared-contract-refs-dev-costs-20261101/spend-ledger.json'])
    before=json.loads((HERE/'credential-readiness.json').read_text());after=json.loads((HERE/'balance-after.json').read_text())
    delta=Decimal(str(after['usage_usd']))-Decimal(str(before['usage_usd']))
    actors=sum(r['response_count'] for r in rows)
    assert actors+50+2==decision['api_requests']
    print(json.dumps({'rows':rows,'actor_requests':actors,'judge_slots':50,'preflight_requests':2,
                      'ledger_statuses':dict(Counter(r['status'] for r in ledger['requests'])),
                      'known_usd':ledger['known_usd'],'aggregate_usage_delta_usd':str(delta),
                      'aggregate_matches_new_ledger':delta==Decimal(ledger['known_usd']),
                      'remaining_backup_usd':after['remaining_usd'],'hidden_reasoning_read':False,
                      'limits':'Stop fields establish stopping only. Anchor calls may be legitimate; counts alone do not establish confused reference resolution. No pure length causal claim.'},ensure_ascii=False,indent=2))


if __name__=='__main__':main()

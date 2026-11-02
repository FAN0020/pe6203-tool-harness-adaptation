"""Post-review visible operation-graph uptake; no reasoning text inspection."""
import json
from pathlib import Path
E=Path(__file__).resolve().parent
ROOT=E.parents[2]
RAW=ROOT/'results/raw/ready-link-pilot-20261101'

def main():
    assert (E/'review-freeze.json').exists()
    out=[]
    for cell in json.loads((RAW/'plan.json').read_text())['cells']:
        p=RAW/'cells'/cell['id']/'run'
        t=json.loads((p/'raw_trace.json').read_text());r=json.loads((p/'result.json').read_text())
        calls=[];responses=[]
        for event in t['events']:
            if event['type']=='agent_response':
                response=event['response'];usage=response['usage']
                responses.append(dict(round=event['round'],finish_reason=response['choices'][0]['finish_reason'],prompt_tokens=usage['prompt_tokens'],completion_tokens=usage['completion_tokens'],reasoning_tokens=usage.get('completion_tokens_details',{}).get('reasoning_tokens')))
            elif event['type']=='tool_result':
                f=event['call']['function'];name=r['model_tool_routes'].get(f['name'],{}).get('tool_name')
                args=json.loads(f['arguments']);text='\n'.join(x.get('text','') for x in event['result'].get('content',[]))
                calls.append(dict(round=event['round'],tool=name,fields=sorted(args),dependency_count=len(args.get('dependsOn',[])),error=bool(event['result'].get('isError')) or text.lstrip().startswith('Error:')))
        creates=[x for x in calls if x['tool']=='create_task']
        links=[x for x in calls if x['tool']=='update_task' and 'dependsOn' in x['fields']]
        last_create=max((x['round'] for x in creates),default=0)
        summary=dict(cell_id=cell['id'],task_id=cell['task_id'],stage=cell['version'],strategy=cell['strategy'],status=r['execution_status'],rounds=len(responses),native_calls=len(calls),creates=len(creates),
            creates_with_nonempty_dependencies=sum(x['dependency_count']>0 for x in creates),dependency_update_calls=len(links),
            dependency_update_rounds=sorted({x['round'] for x in links}),creation_rounds=sorted({x['round'] for x in creates}),
            updates_before_final_creation_round=sum(x['round']<last_create for x in links),
            updates_alongside_creation=sum(x['round'] in {y['round'] for y in creates} for x in links),
            native_errors=sum(x['error'] for x in calls),finish_length_rounds=[x['round'] for x in responses if x['finish_reason']=='length'],
            completion_tokens=sum(x['completion_tokens'] for x in responses),reasoning_text_read=False,
            limitation='Visible inline/update/interleaving counts are descriptive. They do not prove actor intended final edges at creation, optimal scheduling, or causal effect; no hidden reasoning text inspected.')
        out.append(dict(summary=summary,calls=calls,response_metadata=responses))
    (E/'behavior-projection.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps([x['summary'] for x in out],indent=2))

if __name__=='__main__':main()

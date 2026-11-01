"""Post-review descriptive call/round projections; no reasoning text or causal adoption label."""
import json
from pathlib import Path
E=Path(__file__).resolve().parent;ROOT=E.parents[2];RAW=ROOT/'results/raw/observation-coverage-pilot-20261101'
def main():
 assert (E/'review-freeze.json').exists()
 plan=json.loads((RAW/'plan.json').read_text());out=[]
 for cell in plan['cells']:
  p=RAW/'cells'/cell['id']/'run';t=json.loads((p/'raw_trace.json').read_text());r=json.loads((p/'result.json').read_text());calls=[];responses=[]
  for e in t['events']:
   if e['type']=='agent_response':
    q=e['response'];u=q['usage'];responses.append({'round':e['round'],'finish_reason':q['choices'][0]['finish_reason'],'completion_tokens':u['completion_tokens'],'prompt_tokens':u['prompt_tokens'],'reasoning_tokens':u.get('completion_tokens_details',{}).get('reasoning_tokens')})
   elif e['type']=='tool_result':
    f=e['call']['function'];n=r['model_tool_routes'].get(f['name'],{}).get('tool_name');args=json.loads(f['arguments']);txt='\n'.join(x.get('text','') for x in e['result'].get('content',[]));calls.append({'round':e['round'],'tool':n,'argument_fields':sorted(args),'error':bool(e['result'].get('isError')) or txt.lstrip().startswith('Error:'),'id':args.get('id')})
  writes={'create_project','update_project','delete_project','create_task','update_task','delete_task','move_task','create_subtask','update_subtask','delete_subtask','parse_prd','migrate_tasks','migrate_subtasks'}
  reads={'get_task','get_project','list_tasks','list_projects','get_task_hierarchy'}
  lastwrite=max((x['round'] for x in calls if x['tool'] in writes),default=0)
  summary={'cell_id':cell['id'],'task_id':cell['task_id'],'stage':cell['version'],'strategy':cell['strategy'],'status':r['execution_status'],'rounds':len(responses),'native_calls':len(calls),'get_task_calls':sum(x['tool']=='get_task' for x in calls),'read_calls':sum(x['tool'] in reads for x in calls),'read_rounds':sorted({x['round'] for x in calls if x['tool'] in reads}),'write_rounds':sorted({x['round'] for x in calls if x['tool'] in writes}),'last_write_round':lastwrite,'post_last_write_read_calls':sum(x['tool'] in reads and x['round']>lastwrite for x in calls),'native_errors':sum(x['error'] for x in calls),'finish_length_rounds':[x['round'] for x in responses if x['finish_reason']=='length'],'completion_tokens':sum(x['completion_tokens'] for x in responses),'reasoning_text_read':False,'interpretation':'Read counts are descriptive,notproofreads were unnecessary or candidate adopted evidence model.'}
  out.append({'summary':summary,'calls':[{k:v for k,v in c.items() if k!='id'} for c in calls],'response_metadata':responses})
 (E/'behavior-projection.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps([x['summary'] for x in out],indent=2))
if __name__=='__main__':main()

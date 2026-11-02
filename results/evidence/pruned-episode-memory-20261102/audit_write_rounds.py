"""Read response metadata and visible tool arguments only; never inspect reasoning text."""
import hashlib
import json
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
RAW=ROOT/'results/raw/pruned-episode-memory-pilot-20261102'
WRITES={'create_project','create_task','update_task','delete_task','delete_project','parse_prd','create_memory','update_memory'}


def main():
    verdict=json.loads((HERE/'trial-verification.json').read_text());output=[]
    for row in verdict['rows']:
        if row['task_id']!=283:continue
        path=RAW/'cells'/row['cell_id']/'run/raw_trace.json'
        trace=json.loads(path.read_text());rounds=[]
        for event in trace['events']:
            if event['type']!='agent_response':continue
            response=event['response'];message=response['choices'][0]['message']
            calls=message.get('tool_calls') or []
            names=[c['function']['name'].split('__')[0] for c in calls]
            rounds.append({'round':len(rounds)+1,'tools':dict(Counter(names)),'write_calls':sum(n in WRITES for n in names),'visible_argument_chars':sum(len(c['function']['arguments']) for c in calls),'completion_tokens':response['usage'].get('completion_tokens'),'finish_reason':response['choices'][0]['finish_reason']})
        item={'cell_id':row['cell_id'],'stage':row['stage'],'strategy':row['strategy'],'trace_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'rounds':rounds,'write_bearing_rounds':sum(r['write_calls']>0 for r in rounds),'nonwrite_tool_rounds':sum(r['write_calls']==0 and bool(r['tools']) for r in rounds),'empty_no_tool_rounds':sum(not r['tools'] for r in rounds),'total_visible_argument_chars':sum(r['visible_argument_chars'] for r in rounds),'limit':'Counts describe this realized execution; deleting a read does not prove a counterfactual actor would reuse the same rounds or produce a correct final answer.'}
        output.append(item)
    (HERE/'write-round-evidence.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps([{k:v for k,v in r.items() if k not in ['rounds','limit','trace_sha256']} for r in output],indent=2))


if __name__=='__main__':main()

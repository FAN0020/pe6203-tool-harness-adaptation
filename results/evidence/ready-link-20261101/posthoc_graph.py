"""Final-graph counterfactual only; assumes all final tasks/edges known in advance."""
import json
from pathlib import Path
from run_native import schedule
E=Path(__file__).resolve().parent
rows=[]
for rid in ['R02','R06','R08']:
    state=json.loads((E/'blind-artifacts'/rid/'.agentic-tools-mcp/tasks/tasks.json').read_text())
    nodes=[dict(key=t['id'],parent=t.get('parentId'),dependsOn=t.get('dependsOn',[])) for t in state['tasks']]
    routes={}
    for route in ['direct','global_defer','ready_link']:
        waves=schedule(nodes,route)
        routes[route]=dict(theoretical_waves_including_project_read_answer=len(waves)+3,
            normal_calls_including_project_and_read=sum(map(len,waves))+2,
            link_calls=sum(op[0]=='link' for wave in waves for op in wave))
    rows.append(dict(review_id=rid,records=len(nodes),routes=routes))
stored=json.loads((E/'posthoc-final-graph.json').read_text())
assert rows==stored['rows']
print(json.dumps(dict(verified=True,rows=rows,limits=stored['limits']),indent=2))

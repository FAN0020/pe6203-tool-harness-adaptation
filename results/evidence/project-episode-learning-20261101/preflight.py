"""Offline admissibility checks only; never model calls or artifact repair."""
import copy
import hashlib
import json
from pathlib import Path
from pe6203.project_episode_projection import audit_store

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'experiments/extensions/project-episode-training-v1'
result=[]
for task_id in (900401,900402):
    oracle=json.loads((BASE/'evaluation'/f'oracle-{task_id}.json').read_text())
    task=json.loads((BASE/f'task-{task_id}.json').read_text())
    assert task['idx']==task_id and task['dataset_kind']=='controlled_synthetic_extension'
    ids={n['key']:f'fixture-{n["key"]}' for n in oracle['nodes']}
    rows=[]
    for n in oracle['nodes']:
        row={k:n[k] for k in ('name','details','priority','complexity','estimatedHours','status','tags')}
        row.update(id=ids[n['key']],projectId='project-fixture',parentId=ids.get(n['parent']),
            level=0 if n['parent'] is None else 1,dependsOn=[ids[k] for k in n['dependsOn']],completed=False)
        rows.append(row)
    store={'projects':[{'id':'project-fixture','name':oracle['project_name'],'description':oracle['project_description']}],
           'tasks':rows,'subtasks':[]}
    assert audit_store(oracle,store)=={'records':'pass','fields':'pass','structure':'pass'}
    bad=copy.deepcopy(store);bad['tasks'][-1]['estimatedHours']+=1
    assert audit_store(oracle,bad)['fields']=='fail'
    bad=copy.deepcopy(store);bad['tasks'][-1]['dependsOn']=[]
    assert audit_store(oracle,bad)['structure']=='fail'
    assert len(rows)==oracle['total_records']
    assert sum(r['parentId'] is None for r in rows)==oracle['root_records']
    result.append({'task':task_id,'records':len(rows),'oracle_graph_and_acceptance_valid':True,'catalog_tools':sum(map(len,task['servers'].values()))})
for path,digest in json.loads((BASE/'data-manifest.json').read_text()).items():
    assert hashlib.sha256((BASE/path).read_bytes()).hexdigest()==digest
print(json.dumps({'passed':True,'synthetic_inputs':result,'model_calls':0},indent=2))

"""No calls: verify source bounds, frozen factors and exact acceptance before execution."""
import hashlib,json,runpy
from pathlib import Path
from pe6203.project_episode_projection import audit_store
ROOT=Path(__file__).resolve().parents[3];B=ROOT/'experiments/extensions/dependency-factorial-v1'
m=runpy.run_path(str(B/'generate.py'));spec=json.loads((B/'protocol.json').read_text())
assert len(spec['schedule'])==16
assert len({(c['task_id'],c['strategy'],c['seed']) for c in spec['schedule']})==16
src=(ROOT/'.cache/mcpevol/iter5/node_modules/@pimzino/agentic-tools-mcp/dist/features/task-management/tools/tasks/create.js').read_text()
assert 'details.trim().length > 2000' in src and 'name.trim().length > 100' in src
rows=[]
for c in m['cases']():
    task=json.loads((B/f'task-{c["task_id"]}.json').read_text());oracle=json.loads((B/'evaluation'/f'oracle-{c["task_id"]}.json').read_text())
    assert oracle==m['oracle'](c) and audit_store(oracle,m['fixture_store'](c))=={'records':'pass','fields':'pass','structure':'pass'}
    assert all(0<len(n['name'])<=100 and 0<len(n['details'])<=2000 and n['details'].strip()==n['details'] for n in c['nodes'])
    assert len(c['project_description'])<=1000
    rows.append({'task':c['task_id'],'topology':c['topology'],'payload':c['payload'],'detail_chars_each':len(c['nodes'][0]['details']),'question_chars':len(task['question']),'tools':sum(map(len,task['servers'].values()))})
for p,h in json.loads((B/'data-manifest.json').read_text()).items():assert hashlib.sha256((B/p).read_bytes()).hexdigest()==h
print(json.dumps({'admitted':True,'source_native_bounds_checked':True,'cases':rows,'models':0},indent=2))

"""Task-free two-factor persistence inputs, independent of original benchmark outputs."""
import copy
import hashlib
import json
import random
from pathlib import Path

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]
SEED=801001

def write(path,data):
    raw=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode()
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.read_bytes()!=raw:raise ValueError('Frozen input overwrite')
    path.write_bytes(raw);return hashlib.sha256(raw).hexdigest()

def cases():
    rng=random.Random(SEED);templates=[]
    for i in range(8):
        text=' '.join(f'Record{i+1:02d} segment{j:03d} seal{rng.randrange(10000,99999)} preserve this ledger marker.' for j in range(80))
        # The same full text provides both lengths; a fixed final period avoids trim changes.
        templates.append(text)
    out=[]
    for k,(topology,payload) in enumerate((('shallow','short'),('chain','short'),('shallow','long'),('chain','long')),901001):
        nchar=128 if payload=='short' else 1920
        nodes=[]
        for i in range(8):
            nodes.append({'key':f'N{i+1:02d}','name':f'Pollen record N{i+1:02d}',
                'details':templates[i][:nchar-1]+'.','priority':2+i%7,'complexity':2+i%4,
                'estimatedHours':3+i,'tags':['controlled',f'group{i%2+1}'],'status':'pending',
                'parent':None if i<2 else f'N{i%2+1:02d}',
                'dependsOn':[] if topology=='shallow' or i==0 else [f'N{i:02d}']})
        out.append({'task_id':k,'seed':SEED,'topology':topology,'payload':payload,
                    'project_name':'Pollen record ledger',
                    'project_description':'Independent fictional ledger. Preserve the supplied work definitions and references; all work remains pending.',
                    'nodes':nodes})
    return out

def oracle(case):
    return copy.deepcopy(case)|{'total_records':8,'root_records':2,'non_root_records':6,'status':'evaluation_only_never_updater'}

def fixture_store(case):
    ids={n['key']:f'fixture-{n["key"]}' for n in case['nodes']};rows=[]
    for n in case['nodes']:
        r={k:n[k] for k in ('name','details','priority','complexity','estimatedHours','tags','status')}
        r.update(id=ids[n['key']],projectId='fixture-project',parentId=ids.get(n['parent']),level=0 if n['parent'] is None else 1,dependsOn=[ids[z] for z in n['dependsOn']],completed=False);rows.append(r)
    return {'projects':[{'id':'fixture-project','name':case['project_name'],'description':case['project_description']}],'tasks':rows,'subtasks':[]}

def generate():
    catalog=json.loads((ROOT/'tests/fixtures/capability-withdrawal-catalogs.json').read_text())['late'];servers={}
    for t in catalog['tools']:servers.setdefault(t['server_id'],[]).append(t['name'])
    manifest={}
    for c in cases():
        question=('This is an independent synthetic project-persistence task. Create and save the project and all supplied work records in the workspace. '
          'The records below are the complete required set. Preserve each supplied name, details, priority, complexity, estimatedHours, tags and pending status. '
          'Parent and dependency entries refer to symbolic record keys in this input; resolve them to the actual stored task identifiers. '
          'All work remains pending and incomplete; record definitions do not mean the work was performed. Do not replace the supplied work with a redesigned plan. '
          'In the final answer identify the saved project and report total records, root records and non-root records, and accurately describe whether the supplied relationships were saved. '
          'All inputs are provided here; no external information is needed.\n\n'+json.dumps({'project_name':c['project_name'],'project_description':c['project_description'],'records':c['nodes']},ensure_ascii=False,indent=2))
        t=c['task_id']; task={'idx':t,'extension_id':f'ext-dependency-factorial-{t}-v1','dataset_kind':'controlled_synthetic_extension','question':question,'servers':servers}
        manifest[f'task-{t}.json']=write(BASE/f'task-{t}.json',task)
        manifest[f'evaluation/oracle-{t}.json']=write(BASE/f'evaluation/oracle-{t}.json',oracle(c))
    write(BASE/'data-manifest.json',manifest)
    print(json.dumps({'cases':4,'files':len(manifest),'model_calls':0}))

if __name__=='__main__':generate()

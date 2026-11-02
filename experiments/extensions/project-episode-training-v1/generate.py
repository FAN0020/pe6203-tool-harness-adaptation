"""Independent fixed project inputs; no original question, answer or trajectory read."""
import hashlib
import json
import random
from pathlib import Path

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]


def write(path,data):
    blob=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode()
    path.parent.mkdir(exist_ok=True,parents=True)
    if path.exists() and path.read_bytes()!=blob:raise ValueError('Cannot overwrite frozen input')
    path.write_bytes(blob)
    return hashlib.sha256(blob).hexdigest()


def generate():
    catalog=json.loads((ROOT/'tests/fixtures/capability-withdrawal-catalogs.json').read_text())['late']
    servers={}
    for t in catalog['tools']:servers.setdefault(t['server_id'],[]).append(t['name'])
    manifest={}
    for task_id,n,roots,prefix in [(900401,6,2,'Cobalt'),(900402,12,3,'Juniper')]:
        rng=random.Random(task_id-100000)
        nodes=[]
        for i in range(n):
            key=f'R{i+1:02d}'
            nodes.append({'key':key,'name':f'{prefix} record {key}',
                'details':f'Preserve ledger marker {rng.randrange(10000,99999)} for this fictional planning record. This is a stored work definition, not completed real-world work.',
                'priority':rng.randrange(2,9),'complexity':rng.randrange(2,7),
                'estimatedHours':rng.randrange(3,13),'tags':['synthetic',f'group{(i%roots)+1}'],'status':'pending',
                'parent':None if i<roots else f'R{((i-roots)%roots)+1:02d}',
                'dependsOn':[] if i<=roots else [f'R{i:02d}']})
        name=f'{prefix} planning ledger'
        description='Fictional project for exact preservation of supplied work records and references.'
        question=(
            'This is an independent synthetic project-persistence task. Create and save the project and all supplied work records in the workspace. '
            'The records below are the complete required set. Preserve each supplied name, details, priority, complexity, estimatedHours, tags and pending status. '
            'Parent and dependency entries refer to symbolic record keys in this input; resolve them to the actual stored task identifiers. '
            'All work remains pending and incomplete; record definitions do not mean the work was performed. Do not replace the supplied work with a redesigned plan. '
            'In the final answer identify the saved project and report total records, root records and non-root records, and accurately describe whether the supplied relationships were saved. '
            'All inputs are provided here; no external information is needed.\n\n'
            +json.dumps({'project_name':name,'project_description':description,'records':nodes},ensure_ascii=False,indent=2))
        task={'idx':task_id,'extension_id':f'ext-project-episode-{task_id}-v1','dataset_kind':'controlled_synthetic_extension','question':question,'servers':servers}
        oracle={'task_id':task_id,'seed':task_id-100000,'project_name':name,'project_description':description,'nodes':nodes,
                'total_records':n,'root_records':roots,'non_root_records':n-roots,'status':'evaluation_only_never_updater'}
        manifest[f'task-{task_id}.json']=write(BASE/f'task-{task_id}.json',task)
        manifest[f'evaluation/oracle-{task_id}.json']=write(BASE/f'evaluation/oracle-{task_id}.json',oracle)
    write(BASE/'data-manifest.json',manifest)
    print(json.dumps({'input_files':len(manifest),'models':0}))

if __name__=='__main__':generate()

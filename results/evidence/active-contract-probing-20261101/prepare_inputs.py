"""Prepare task-free metadata and synthetic native state; no model/native calls."""
import json
from pathlib import Path
from copy import deepcopy
from pe6203.active_contract_probing import inventory, PROJECT
from pe6203.benchmark import write_json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BINDINGS={'$PROJECT':'10000000-0000-4000-8000-000000000001',
          '$OTHER_PROJECT':'10000000-0000-4000-8000-000000000002',
          '$TASK':'20000000-0000-4000-8000-000000000001',
          '$CHILD':'20000000-0000-4000-8000-000000000002',
          '$DONE_TASK':'20000000-0000-4000-8000-000000000003'}

def main():
    timestamp='2026-01-01T00:00:00.000Z'
    projects=[{'id':BINDINGS[token],'name':name,'description':'Isolated synthetic contract fixture.','createdAt':timestamp,'updatedAt':timestamp} for token,name in [('$PROJECT','FixtureProjectOne'),('$OTHER_PROJECT','FixtureProjectTwo')]]
    tasks=[]
    for token,name,project,status,priority,complexity,hours,parent,deps in [
        ('$TASK','FixtureRecordAlpha','$PROJECT','pending',3,2,1,None,[]),
        ('$CHILD','FixtureRecordBeta','$PROJECT','blocked',5,4,2,'$TASK',['$TASK']),
        ('$DONE_TASK','FixtureRecordGamma','$OTHER_PROJECT','done',6,2,1,None,[])]:
        t={'id':BINDINGS[token],'name':name,'details':'Synthetic native record; not a benchmark task or answer.','projectId':BINDINGS[project],'completed':status=='done','createdAt':timestamp,'updatedAt':timestamp,'dependsOn':[BINDINGS[x] for x in deps],'priority':priority,'complexity':complexity,'status':status,'tags':['fixture'],'estimatedHours':hours,'level':int(parent is not None)}
        if parent:t['parentId']=BINDINGS[parent]
        tasks.append(t)
    fixture={'projects':projects,'tasks':tasks,'subtasks':[],'migration':{'version':'1.8.1'}}
    write_json(HERE/'native-fixture.json',fixture)
    jobs=[]
    for stage in ['middle','late']:
        for label,task,server in [('project',283,PROJECT),('math',133,'math-mcp')]:
            cats={}
            for version in ['early',stage]:
                raw=json.loads((ROOT/f'results/raw/instruction-scope-pilot-20261101/catalogs/{task}/{version}.json').read_text())
                cats[version]={k:deepcopy(raw[k]) for k in ['schema_version','benchmark_commit','version','tools']}
            data=inventory(cats['early'],cats[stage],server)
            jobs.append({'id':f'{label}-{stage}','stage':stage,'data':data})
    write_json(HERE/'updater-inputs.json',{'jobs':jobs,'bindings':BINDINGS,'fixture':fixture})
    config=json.loads((ROOT/'configs/daily-migration-updater-v1.json').read_text())
    config['spend_guard']['ledger']='results/raw/active-contract-probing-generation-20261101/spend-ledger.json'
    write_json(ROOT/'configs/active-contract-probing-updater-v1.json',config)
    print(json.dumps({'jobs':[{'id':j['id'],'claims':len(j['data']['claims']),'changed_tools':len(j['data']['changed_ids'])} for j in jobs],'model_calls':0,'native_calls':0}))

if __name__=='__main__':main()

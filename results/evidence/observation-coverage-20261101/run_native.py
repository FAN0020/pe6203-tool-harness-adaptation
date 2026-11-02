"""Task-free native observation discrimination; persisted state is evaluation only."""
import asyncio,hashlib,json,re,subprocess
from pathlib import Path
from pe6203.experiment import configure_runtime
from pe6203.transport import sessions
E=Path(__file__).resolve().parent;ROOT=E.parents[2];P=ROOT/'experiments/observation-coverage-native-v1.json'
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def text(r):return '\n'.join(c.get('text','') for c in r.get('content',[]))
def identity(r):
 m=re.search(r'\(ID: ([a-f0-9-]{36})\)',text(r));assert m;return m.group(1)
def normalize(r):
 return '\n'.join(s for s in text(r).splitlines() if not s.startswith(('**Created:**','**Last Updated:**')))
async def main():
 p=json.loads(P.read_text());assert not (E/'native-preexecution.json').exists()
 for source in p['sources']:assert sha(ROOT/source['path'])==source['sha256']
 save(E/'native-preexecution.json',{'plan_sha256':sha(P),'runner_sha256':sha(Path(__file__)),'freeze_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'model_calls':0})
 configure_runtime(ROOT);count=0;results=[]
 for stage in p['stages']:
  dest=E/f'native-{stage}';dest.mkdir(exist_ok=False);work=dest/'workspace';work.mkdir();statepath=work/'.agentic-tools-mcp/tasks/tasks.json';obs=[]
  async with sessions(ROOT,stage,[p['server']],work,dest/'stderr.log') as cs:
   c=cs[p['server']];save(dest/'catalog.json',(await c.list_tools()).model_dump(mode='json',by_alias=True))
   async def call(tool,args,negative=False):
    nonlocal count
    before=statepath.read_bytes() if statepath.exists() else None
    args=dict(args,workingDirectory=str(work));r=(await c.call_tool(tool,args)).model_dump(mode='json',by_alias=True,exclude_none=True);count+=1
    obs.append({'index':len(obs)+1,'tool':tool,'args':args,'result':r,'negative_control':negative});save(dest/'observations.json',obs)
    if statepath.exists():(dest/f'{len(obs):02d}-state.json').write_bytes(statepath.read_bytes())
    save(E/'native-ledger.json',{'native_calls':count,'catalog_calls_completed':len(results)+1,'model_calls':0,'model_tokens':0,'usd':'0'})
    error=bool(r.get('isError')) or text(r).startswith('Error:');assert error==negative,(stage,tool,text(r))
    if negative:assert before==statepath.read_bytes()
    return r
   pid=identity(await call('create_project',p['project']));ids={};created={}
   for n in p['nodes']:
    args={k:v for k,v in n.items() if k not in ('key','parent','dependencies')};args['projectId']=pid
    if n['parent']:args['parentId']=ids[n['parent']]
    args['dependsOn']=[ids[k] for k in n['dependencies']]
    created[n['key']]=await call('create_task',args);ids[n['key']]=identity(created[n['key']])
   before_get=await call('get_task',{'id':ids['C']});before_flat=await call('list_tasks',{'projectId':pid,'showHierarchy':False,'includeCompleted':True});before_tree=await call('list_tasks',{'projectId':pid,'showHierarchy':True,'includeCompleted':True})
   changed=await call('update_task',{'id':ids['C'],'dependsOn':[ids['A']],'priority':3,'complexity':5})
   after_get=await call('get_task',{'id':ids['C']});after_flat=await call('list_tasks',{'projectId':pid,'showHierarchy':False,'includeCompleted':True});after_tree=await call('list_tasks',{'projectId':pid,'showHierarchy':True,'includeCompleted':True})
   await call('update_task',{'id':ids['C'],'dependsOn':['00000000-0000-0000-0000-000000000000']},negative=True)
   zero=await call('update_task',{'id':ids['C'],'estimatedHours':0});zero_get=await call('get_task',{'id':ids['C']});zero_flat=await call('list_tasks',{'projectId':pid,'showHierarchy':False,'includeCompleted':True})
   stored=json.loads(statepath.read_text());by={n['id']:n for n in stored['tasks']};target=by[ids['C']]
   assert stored['projects'][0]['description']==p['project']['description'] and len(stored['tasks'])==3
   assert target['dependsOn']==[ids['A']] and target['parentId']==ids['A'] and target['priority']==3 and target['complexity']==5 and target['estimatedHours']==0
   assert target['status']=='blocked' and target['completed'] is False and target['tags']==['obs-canary-δ']
   checks={'get_projection_unchanged_after_dependency_priority_complexity_change':normalize(before_get)==normalize(after_get),'flat_projection_unchanged_after_same_change':text(before_flat)==text(after_flat),'hierarchy_projection_unchanged_after_same_change':text(before_tree)==text(after_tree),'write_receipts_distinguish_dependency_ids':f'Dependencies: {ids["B"]}' in text(created['C']) and f'Dependencies: {ids["A"]}' in text(changed),'write_receipts_distinguish_priority_complexity':'Priority: 2/10' in text(created['C']) and 'Complexity: 4/10' in text(created['C']) and 'Priority: 3/10' in text(changed) and 'Complexity: 5/10' in text(changed),'get_hides_domain_status':target['status']=='blocked' and '**Status:** ⏳ Pending' in text(after_get),'zero_estimate_not_explicit_in_update_receipt':'Estimated Hours: Not set' in text(zero) and target['estimatedHours']==0,'get_projection_unchanged_after_zero_estimate':normalize(zero_get)==normalize(after_get),'negative_write_did_not_mutate':True,'details_marker_preserved':target['details']==p['nodes'][2]['details'],'all_receipt_ids_match_storage':set(by)==set(ids.values()),'flat_has_unique_ids':all(text(after_flat).count(i)==1 for i in ids.values())}
   save(dest/'result.json',{'stage':stage,'checks':checks,'native_calls':len(obs),'admitted':all(checks.values())});results.append({'stage':stage,'checks':checks,'native_calls':len(obs),'admitted':all(checks.values())});save(E/'native-results.json',results)
   assert all(checks.values()),checks
   assert len(obs)==15
 assert count==30
 save(E/'native-decision.json',{'admitted':True,'stages':p['stages'],'native_calls':count,'catalog_calls':2,'negative_controls':2,'model_calls':0,'usd':'0','rows':results,'benchmark_success':False,'limitations':'Finite generic probes plus fixedsource. Observational equality alone cannot certify desiredstate; source/receipt conditions and mutation invalidation matter. No task answer, trajectory or score enters knowledge.'})
 print(json.dumps({'admitted':True,'native_calls':count,'model_calls':0,'usd':'0'}))
if __name__=='__main__':asyncio.run(main())

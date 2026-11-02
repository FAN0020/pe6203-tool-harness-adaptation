from pathlib import Path
import json,hashlib,decimal,collections,tarfile,shutil
from pe6203.benchmark import digest
from pe6203.artifact_validation import settings as artifact_settings
root=Path.cwd();home=root/'results/raw/v6-r1-full-five-20261103';out=root/'evaluation/v6/revisions/r1';out.mkdir(parents=True,exist_ok=True)
plan=json.load(open(home/'plan.json'));receipts=[json.loads(x) for x in (home/'api/receipts.jsonl').read_text().splitlines()]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checks={'frozen_source':all(sha(root/p)==h for p,h in plan['source_files_sha256'].items()),'frozen_inputs':all(sha(home/p)==h for p,h in plan['catalogs_sha256'].items()),'known_pinned_receipts':all(r.get('usd') is not None and r.get('provider')=='DigitalOcean' and r.get('model')==plan['model'] for r in receipts),'original_artifact_protocol':sha(home/'python-protocol.json')==plan['artifact_protocol_sha256'],'original_artifact_context':sha(home/'python-task-context.txt')==plan['artifact_context_sha256']}
freeze=json.load(open(home/'knowledge-freeze.json'))['files'];checks['frozen_knowledge']=all(sha(home/p)==v['sha256'] for p,v in freeze.items())
rows=[]
for c in plan['cell_order']:
 p=home/'runs'/c['id'];adapt=json.load(open(home/c['adaptation']))
 if adapt['status']!='validated':
  rows.append({**c,'status':'update_failed_not_run','verified':not p.exists() and (home/'blocked-cells'/(c['id']+'.json')).exists()});continue
 r=json.load(open(p/'result.json'));ev=json.load(open(p/'EVAL'/f"{c['task_id']}.json"))['eval_result']['aggregate']
 cs={role:sum((decimal.Decimal(str(x['usd'])) for x in receipts if x['cell']==c['id'] and x['phase']==role),decimal.Decimal(0)) for role in ['agent','judge']}
 trace=json.load(open(p/'raw_trace.json'));rounds=sum(e.get('type')=='agent_response' for e in trace['events']);artifact=r.get('artifact_validation')
 good=ev['successful_runs']==5 and abs(ev['task_fulfillment_mean']-r['TF'])<1e-10 and abs(ev['planning_and_efficiency_mean']-r['PE'])<1e-10 and all(abs(cs[role]-decimal.Decimal(str(r['cost'][role]['usd'])))<decimal.Decimal('1e-10') for role in cs) and rounds<=12
 good=good and json.load(open(p/'knowledge.json'))==json.load(open((home/c['adaptation']).parent/'knowledge.json'))
 if c['task_id']==133:good=good and artifact['protocol_sha256']==digest(artifact_settings(json.load(open(home/'python-protocol.json')))) and len(artifact['repairs'])<=1
 rows.append({**c,'status':r['execution_status'],'TF':r['TF'],'PE':r['PE'],'rounds':rounds,'artifact_status':artifact.get('status') if artifact else None,'verified':good})
checks['all_planned_accounted']=len(rows)==45 and all(r['verified'] for r in rows)
verification={'passed':all(checks.values()),'checks':checks,'outcomes':dict(collections.Counter(r['status'] for r in rows)),'rows':rows}
(home/'verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2)+'\n');assert verification['passed'],checks
for name in ['plan.json','summary.json','knowledge-freeze.json','verification.json','trajectories.csv','pilot-gate.json']:shutil.copy2(home/name,out/name)
for source,name in [('outputs/v6-revision1-tests.txt','initial-tests.txt'),('outputs/v6-revision1-tests-restored.txt','tests-restored.txt'),('outputs/v6-revision1-restored-fixtures.json','restored-fixtures.json'),('outputs/v6-r1-pilot-execution-diagnosis.md','pilot-execution-diagnosis.md'),('outputs/v6-r1-430-admission-diagnosis.md','430-admission-diagnosis.md'),('outputs/archive-v6-r1.py','archive-script.py')]:shutil.copy2(root/source,out/name)
audit=Path('/Users/q/.codex/.chatgpt-projects/g-p-6a731461688481918939646b5d12604b/outputs/worker-v6-r1-code-audit.md');shutil.copy2(audit,out/'worker-code-audit.md')
with tarfile.open(out/'runtime.tar.gz','w:gz') as t:
 for name in plan['source_files_sha256']:t.add(root/name,arcname=name,recursive=False)
members={}
with tarfile.open(out/'raw-measurements.tar.gz','w:gz') as t:
 for p in sorted(home.rglob('*')):
  if p.is_file():
   name=home.name+'/'+str(p.relative_to(home));members[name]=sha(p);t.add(p,arcname=name,recursive=False)
(out/'raw-manifest.json').write_text(json.dumps({'members':members},indent=2)+'\n')
s=json.load(open(home/'summary.json'));v=s['by_arm']['v6']
text=f'''# V6-r1 full five-task development evaluation\n\nFrozen45-cell plan:39trajectories scored,6blocked (283Middle/430Late failed update). All9math artifacts failed unchanged finite checks;30other executions delivered final answers. No run replaced or selected.\n\nScored-only TF={v['TF']:.6f}, PE={v['PE']:.6f}; not full-five-task averages. Actual total API USD{s['known_actual_usd']}.\n\nPilot gate checked protocol completeness, not good scores. This revision did not meet the all-task delivery goal. Diagnoses found nonexistent retained-rule indices and single-line non-code source strings. Follow-up repairs must be separately frozen, not replace this run.\n\nOffline audit passed.968regressions passed,23deselected after restoring33ignored fixtures and a local Node path. Initial22environment failures retained.2new driver tests passed separately.\n'''
(out/'README.md').write_text(text)
(out/'manifest.json').write_text(json.dumps({'schema':'v6-r1-development-evidence-1','old_results_overwritten':False,'files':{str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.name!='manifest.json'}},indent=2)+'\n')
print({'passed':verification['passed'],'outcomes':verification['outcomes'],'TF':v['TF'],'PE':v['PE'],'USD':s['known_actual_usd']})

"""Historical persisted project review; keep missing fields and judgments explicit."""
import hashlib
import json
import runpy
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'results/evidence/unified-reaudit-20261102/historical-products'
G=runpy.run_path(str(ROOT/'results/evidence/capability-consolidation-20261102/product_graph.py'))['graph_facts']
COHORTS=['selective-search-confirmation-r2-20261031','selective-search-confirmation-r3-20261031','selective-search-v2.1-development-20261031']
DELIVERY={
 ('selective-search-confirmation-r2-20261031','task283-late-selective_patch-r0'):'Claims scheduling/freshness was also split to a second level, but saved scheduling task is a leaf. Claims6milestones report6–7; analyzer includes8.48total correct; saved hierarchy does not support all narrative claims.',
 ('selective-search-v2.1-development-20261031','task283-late-selective_patch-r0'):'Claims38executable tasks, but43total minus5milestones minus advanced-components container leaves37. Analyzer simple38 includes that parent; it is not a leaf count.',
 ('selective-search-v2.1-development-20261031','task283-middle-sufficiency_feedback-r0'):'29tasks/5milestones/24leaves and analyzer4.1 agree, but all-leaves3–5 assertion fails: CI/CD pipeline & deployment complexity is absent. Do not silently treat an absent field as zero or proof of bounded scope.'}


def main():
 count=0
 for co in COHORTS:
  for f in sorted((P/co).glob('task283-*.json')):
   d=json.loads(f.read_text());props=dict.fromkeys(['coverage','structure_and_scope','delivery_truth','scope_preserved'],'unknown');evidence={};facts=None;mutations=[]
   if d['artifacts']:
    artifact=d['artifacts'][0];raw=ROOT/d['cohort']/'cells'/d['cell_id']/'run/workspace'/artifact['path'];assert hashlib.sha256(raw.read_bytes()).hexdigest()==artifact['sha256'];s=json.loads(raw.read_text());facts=G(s);parents={t.get('parentId') for t in s['tasks']};by={t['id']:t for t in s['tasks']}
    assert all(t['id'] and any(x['id']==t['projectId'] for x in s['projects']) for t in s['tasks'])
    assert not any(facts[k] for k in ['duplicate_ids','dangling_parents','dangling_dependencies','parent_cycle'])
    props.update(coverage='pass',structure_and_scope='pass',scope_preserved='pass')
    evidence.update(coverage='Saved tasks cover CSV processing, log analysis and visualization; domain names and concrete work descriptions reviewed.',structure_and_scope='Unique linked records and valid parent graph; substantive executable decomposition distinguished from milestone containers. No arbitrary numeric effort cutoff.',scope_preserved='Required work retained; parent estimates after real child decomposition are not treated as scope hiding.')
    for c in d['calls']:
     if c['tool'].startswith(('update_task','delete_task')):
      a=json.loads(c['arguments']);a.pop('workingDirectory',None)
      if set(a)<= {'id','dependsOn'}:continue
      entry={'tool':c['tool'],'args':a,'has_children':a['id'] in parents}
      created=[x for x in d['calls'] if x['tool'].startswith('create_task') and a['id'] in json.dumps(x['result'])]
      if created:entry['initial_arguments']=json.loads(created[0]['arguments']);entry['initial_arguments'].pop('workingDirectory',None)
      mutations.append(entry)
    if facts['dependency_field_missing']:
     props['structure_and_scope']='unknown';evidence['structure_and_scope']='Early persisted leaf records omit dependsOn; do not infer no dependencies or certify complete graph from absent fields. Parent graph is valid and domains decomposed.'
    if co=='selective-search-confirmation-r3-20261031' and 'early' in f.stem:
     props['coverage']='fail';props['structure_and_scope']='fail';evidence['coverage']='Only4major milestone records saved; no concrete child tasks.';evidence['structure_and_scope']='Four milestone leaves still each describe entire pipelines/components/integration; requested decomposition is unfinished.'
    if (co,f.stem) in [('selective-search-confirmation-r2-20261031','task283-late-selective_patch-r0'),('selective-search-v2.1-development-20261031','task283-middle-selective_patch-r0')]:
     props['scope_preserved']='unknown';evidence['scope_preserved']='Several leaf names shortened and declared complexity5→4 without details or child decomposition. This is not evidence of reduced actual complexity. Material content generally remains; intent/actual scope difficulty is unestablished, so do not invent a causal gaming conclusion.'
   else:evidence['artifact']='No persisted task artifact available after failed execution; required properties unknown.'
   if d['answer']:
    assert (co,f.stem) in DELIVERY;props['delivery_truth']='fail';evidence['delivery_truth']=DELIVERY[(co,f.stem)]
   else:evidence['delivery_truth']='No final answer; persisted partial work cannot establish completed delivery.'
   r={'cell_id':f.stem,'task_id':283,'input_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'trace_sha256':d['trace_sha256'],'properties':props,'core_pass':all(v=='pass' for v in props.values()),'evidence':evidence,'graph_facts':facts,'scope_relevant_mutations':mutations,'review_phase':'supplemental_posthoc_scores_exposed','review_source':'scripts/review_reaudit_gap_projects.py','limitations':['Same coordinator; prior scores exposed, not independent validation.','Qualitative scope is not measured implementation effort.','Analyzer heuristics and stored complexity fields are different quantities.','Missing dependency fields remain unknown, not zero.']}
   (f.parent/'reviews'/f.name).write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');count+=1
 print(count,'supplemental project reviews')


if __name__=='__main__':main()

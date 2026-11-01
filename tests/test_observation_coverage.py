"""Knowledge-only observation coverage; no actor runtime or scoring changes."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from pe6203.observation_coverage import compile_knowledge, projection_gap
from pe6203.selective import adapt_result

def inputs(stage='late'):
 cats=json.loads(Path('tests/fixtures/dependency-cut-catalogs.json').read_text())
 fb=json.loads(Path('experiments/observation-coverage-feedback-v1.json').read_text())['observations']
 return cats['early'],cats[stage],fb
@pytest.mark.parametrize('stage',['middle','late'])
def test_only_actual_changed_producer_is_enriched(stage):
 old,target,fb=inputs(stage);pristine=deepcopy((old,target,fb));base=adapt_result(old,target)
 result,edits=compile_knowledge(base,target,fb);restored=deepcopy(result)
 a=next(x for x in restored['tools'] if x['name']=='create_project');b=next(x for x in base['knowledge']['tools'] if x['name']=='create_project')
 assert 'OBSERVATION CONTRACT' in a['description'] and 'Unobservable by get_task:' in a['description']
 assert 'After a later write' in a['description'] and 'Not set' in a['description']
 a['description']=b['description'];assert restored==base['knowledge'] and len(edits)==1 and (old,target,fb)==pristine
@pytest.mark.parametrize('mutation',['facts','source','stage','consumer','missing'])
def test_uncertified_changes_rejected(mutation):
 old,target,fb=inputs();cert=fb[1]['result']
 if mutation=='facts':cert['operators'][3]['exact'].append('task.dependsOn')
 elif mutation=='source':cert['source_native_result_sha256']='not-native'
 elif mutation=='stage':cert['stage']='middle'
 elif mutation=='consumer':next(t for t in target['tools'] if t['name']=='get_task')['description']+='new semantics'
 else:fb=[]
 with pytest.raises(ValueError):compile_knowledge(adapt_result(old,target),target,fb)
def test_read_projection_cannot_certify_dependency_or_exact_priority():
 _,_,fb=inputs();ops=fb[1]['result']['operators'];get=next(o for o in ops if o['tool']=='get_task');update=next(o for o in ops if o['tool']=='update_task')
 assert projection_gap(['task.details','task.dependsOn','task.priority'],get['exact'])==['task.dependsOn','task.priority']
 assert projection_gap(['task.details','task.dependsOn','task.priority'],update['exact'])==[]
 assert projection_gap(['task.estimatedHours'],update['exact'])==['task.estimatedHours']
def test_no_change_and_other_task_families_remain_exact_sp():
 old,_,_=inputs();base=adapt_result(old,old);assert compile_knowledge(base,old,[])==(base['knowledge'],[])
 for fixture,key in [('semantic-maintenance-catalogs.json',None),('prefix-workflow-catalogs.json','235')]:
  cats=json.loads((Path('tests/fixtures')/fixture).read_text());cats=cats[key] if key else cats
  base=adapt_result(cats['early'],cats['late']);assert compile_knowledge(base,cats['late'],[])==(base['knowledge'],[])

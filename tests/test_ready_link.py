"""Certificate validation and protection of all unrelated knowledge."""
import json
from copy import deepcopy
from pathlib import Path
import pytest
from pe6203.ready_link import compile_knowledge
from pe6203.selective import adapt_result

def inputs(stage='late'):
    cats=json.loads(Path('tests/fixtures/dependency-cut-catalogs.json').read_text())
    feedback=json.loads(Path('experiments/ready-link-feedback-v1.json').read_text())['observations']
    return cats['early'],cats[stage],feedback

@pytest.mark.parametrize('stage',['middle','late'])
def test_only_changed_producer_description_can_change(stage):
    old,target,feedback=inputs(stage); pristine=deepcopy((old,target,feedback)); base=adapt_result(old,target)
    actual,changes=compile_knowledge(base,target,feedback); restored=deepcopy(actual)
    host=next(t for t in restored['tools'] if t['name']=='create_project')
    original=next(t for t in base['knowledge']['tools'] if t['name']=='create_project')
    assert host['description']!=original['description']
    host['description']=original['description']
    assert restored==base['knowledge'] and len(changes)==1
    assert (old,target,feedback)==pristine

@pytest.mark.parametrize('mutation',['text','stage','source','creator','linker','missing','duplicate'])
def test_uncertified_rule_or_changed_contract_is_rejected(mutation):
    old,target,fb=inputs(); row=next(x for x in fb if x['stage']=='late'); cert=row['result']
    if mutation=='text': cert['description_suffix']+=' Invent a missing ID.'
    elif mutation=='stage': cert['stage']='middle'
    elif mutation=='source': cert['native_result_sha256']='wrong'
    elif mutation=='creator': next(t for t in target['tools'] if t['name']=='create_task')['parameters']['required'].append('new')
    elif mutation=='linker': next(t for t in target['tools'] if t['name']=='update_task')['description']+=' altered'
    elif mutation=='duplicate': fb.append(deepcopy(row))
    else: fb=[]
    with pytest.raises(ValueError): compile_knowledge(adapt_result(old,target),target,fb)

def test_unchanged_catalog_and_other_task_families_equal_sp():
    old,_,_=inputs(); base=adapt_result(old,old)
    assert compile_knowledge(base,old,[])==(base['knowledge'],[])
    for path,key in [('tests/fixtures/semantic-maintenance-catalogs.json',None),('tests/fixtures/prefix-workflow-catalogs.json','235')]:
        cats=json.loads(Path(path).read_text())
        if key: cats=cats[key]
        base=adapt_result(cats['early'],cats['late'])
        assert compile_knowledge(base,cats['late'],[])==(base['knowledge'],[])

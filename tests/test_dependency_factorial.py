"""The diagnostic must vary only its two declared factors and retain exact acceptance."""
import copy
import importlib.util
from pathlib import Path

PATH=Path(__file__).parents[1]/'experiments/extensions/dependency-factorial-v1/generate.py'

def module():
    spec=importlib.util.spec_from_file_location('factorial_generate',PATH)
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj

def strip(case,field):
    rows=copy.deepcopy(case['nodes'])
    for r in rows:r.pop(field)
    return rows

def test_topology_only_changes_dependencies():
    m=module();cases=m.cases()
    for size in ('short','long'):
        a=next(c for c in cases if c['topology']=='shallow' and c['payload']==size)
        b=next(c for c in cases if c['topology']=='chain' and c['payload']==size)
        assert strip(a,'dependsOn')==strip(b,'dependsOn')
        assert sum(map(lambda n:len(n['dependsOn']),a['nodes']))==0
        assert sum(map(lambda n:len(n['dependsOn']),b['nodes']))==7

def test_payload_only_changes_details_and_is_source_valid():
    cases=module().cases()
    for topology in ('shallow','chain'):
        a=next(c for c in cases if c['topology']==topology and c['payload']=='short')
        b=next(c for c in cases if c['topology']==topology and c['payload']=='long')
        assert strip(a,'details')==strip(b,'details')
        for u,v in zip(a['nodes'],b['nodes']):
            assert len(u['details'])==128 and len(v['details'])==1920
            assert u['details']==u['details'].strip() and v['details']==v['details'].strip()
            assert len(v['details'])<=2000 and len(v['name'])<=100

def test_exact_store_oracle_and_negative_controls():
    from pe6203.project_episode_projection import audit_store
    m=module()
    for c in m.cases():
        o=m.oracle(c);s=m.fixture_store(c)
        assert audit_store(o,s)=={'records':'pass','fields':'pass','structure':'pass'}
        t=copy.deepcopy(s);t['tasks'][0]['details']=t['tasks'][0]['details'][:-1]
        assert audit_store(o,t)['fields']=='fail'
        t=copy.deepcopy(s);t['tasks'][-1]['parentId']=None
        assert audit_store(o,t)['structure']=='fail'
        if c['topology']=='chain':
            t=copy.deepcopy(s);t['tasks'][-1]['dependsOn']=[]
            assert audit_store(o,t)['structure']=='fail'

def test_fixed_cases_and_no_original_inputs():
    m=module();cs=m.cases();assert cs==m.cases()
    assert {c['task_id'] for c in cs}=={901001,901002,901003,901004}
    assert {(c['topology'],c['payload']) for c in cs}=={(t,p) for t in ('shallow','chain') for p in ('short','long')}
    assert all(len(c['nodes'])==8 and c['project_name']=='Pollen record ledger' for c in cs)
    assert all(sum(n['parent'] is None for n in c['nodes'])==2 for c in cs)

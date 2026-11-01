"""Freeze a separate16-cell diagnostic using exact, previously frozen knowledge."""
import copy
import shutil
from datetime import UTC,datetime
from pathlib import Path
from pe6203.benchmark import load_task,read_json,source,write_json
from pe6203.experiment import configure_runtime,freeze_files,model_config,sha
from pe6203.runner import credentials

BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2]
OUT=ROOT/'results/raw/extensions/observation-selection-v1'
E=ROOT/'results/evidence/observation-selection-20261101'
PRIOR=ROOT/'results/raw/observation-coverage-pilot-20261101'

def main():
    spec=read_json(BASE/'protocol.json');tasks=[c['task_id'] for c in spec['cases']]
    for p,h in read_json(BASE/'data-manifest.json').items():assert sha(BASE/p)==h
    prior_lock=read_json(PRIOR/'knowledge-lock.json')
    for p,h in prior_lock['files'].items():assert sha(PRIOR/p)==h
    assert not (OUT/'plan.json').exists() and not (OUT/'experiment.json').exists() and not (OUT/'spend-ledger.json').exists()
    OUT.mkdir(parents=True,exist_ok=True);configure_runtime(ROOT);lock,upstream=source(ROOT)
    config=model_config(ROOT,spec['model_config']);config.pop('fixture_dir',None);config.pop('task_context',None)
    config['extension_tasks']={str(t):str(BASE.relative_to(ROOT)/f'task-{t}.json') for t in tasks}
    config['task_fixture_dirs']={str(t):str(BASE.relative_to(ROOT)/'fixtures'/str(t)) for t in tasks}
    updater=copy.deepcopy(read_json(ROOT/spec['updater_config']))
    endpoints={role:credentials(c)[1] for role,c in {'agent':config['agent'],'judge':config['judge'],'updater':updater}.items()}
    adaptations={};equalities=[]
    for t in tasks:
        for stage in ('early','late'):
            dest=OUT/'catalogs'/str(t)/f'{stage}.json';dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(PRIOR/'catalogs/283'/f'{stage}.json',dest)
        for arm in ('selective_patch','observation_coverage'):
            orig=PRIOR/'adaptations'/f'283-late-{arm}';dest=OUT/'adaptations'/f'{t}-late-{arm}';shutil.copytree(orig,dest,dirs_exist_ok=True)
            assert read_json(dest/'adaptation.json')['status']=='validated'
            assert sha(orig/'knowledge.json')==sha(dest/'knowledge.json')
            adaptations[f'{t}-late-{arm}']=str((dest/'adaptation.json').relative_to(OUT))
            equalities.append({'task':t,'arm':arm,'prior_knowledge':str((orig/'knowledge.json').relative_to(ROOT)),'knowledge_sha256':sha(dest/'knowledge.json')})
    paths=list((ROOT/'src/pe6203').rglob('*.py'))+list((ROOT/'integration').rglob('*.py'))
    paths += [p for p in BASE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    paths += [ROOT/p for p in (spec['model_config'],spec['updater_config'],'configs/benchmark.lock.json','configs/server-profiles.json','uv.lock','pyproject.toml','tests/test_observation_coverage.py','tests/fixtures/capability-withdrawal-catalogs.json')]
    paths+=list((OUT/'catalogs').rglob('*.json'))+list(E.glob('*.py'))+[E/'research-decision.json']
    paths+=[ROOT/'.cache/node-runtime/node_modules/node/bin/node']
    paths+=list((ROOT/'.cache/mcpevol/iter5/node_modules/@pimzino/agentic-tools-mcp/dist').rglob('*.js'))
    paths+=[ROOT/'results/evidence/observation-coverage-20261101'/n for n in ('research-decision.json','decision.json','interpretation.json')]
    paths += [PRIOR/'knowledge-lock.json']+[PRIOR/'adaptations'/f'283-late-{a}'/'knowledge.json' for a in ('selective_patch','observation_coverage')]
    plan={'schema_version':'experiment-1','kind':'controlled_extension_mechanism_diagnostic','variant':'released_servers_controlled_synthetic_input','created_at':datetime.now(UTC).isoformat(),
       'benchmark_commit':lock['commit'],'dataset_revision':lock['dataset_revision'],'cells':spec['schedule'],
       'tasks':[load_task(upstream,t,BASE/f'task-{t}.json') for t in tasks],'config':config,'updater':updater,'judge_runs':5,
       'files':freeze_files(ROOT,paths),'endpoints':endpoints,'formal_evaluation':False,'coverage':{},
       'limitations':spec['limits'],'shared_adaptations':adaptations,'availability_preflight':True,'max_preflight_calls':2,'stop_after_infrastructure_failures':2,'diagnostic_spec':spec}
    write_json(OUT/'plan.json',plan);(OUT/'plan.sha256').write_text(sha(OUT/'plan.json')+'\n')
    write_json(OUT/'knowledge-lock.json',{'plan_sha256':sha(OUT/'plan.json'),'files':freeze_files(OUT,list((OUT/'adaptations').rglob('*.json')))})
    write_json(OUT/'knowledge-review.json',{'accepted':True,'lock_sha256':sha(OUT/'knowledge-lock.json'),'note':'Exact unchanged prior original283Late SP/observation_coverage knowledge; only independent diagnostic input factors vary. No new candidate or validation. No updater calls.','equalities':equalities})
    dest=E/'preexecution';dest.mkdir(exist_ok=False)
    for n in ('plan.json','plan.sha256','knowledge-lock.json','knowledge-review.json'):shutil.copyfile(OUT/n,dest/n)
    print({'cells':len(plan['cells']),'source_files':len(plan['files']),'knowledge_sha256':sha(OUT/'knowledge-lock.json'),'model_calls':0})

if __name__=='__main__':main()

"""Once-only execution of all first proposals after frozen reference decoding."""
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import run_generation as generation
from pe6203.active_contract_probing import validate_probes, compile_decisions
from pe6203.experiment import configure_runtime, verify_files

HERE=Path(__file__).resolve().parent
PARENT=HERE.parent
ROOT=PARENT.parents[2]


async def main():
    frozen=json.loads((HERE/'pre-model-freeze.json').read_text())
    verify_files(ROOT,frozen['files'])
    assert not (HERE/'preexecution.json').exists(), 'Recovery already attempted'
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip()
    os.environ['AGENT_API_KEY']=os.environ['OPENROUTER_API_KEY_BACKUP']
    configure_runtime(ROOT)
    generation.HERE=HERE
    save=generation.save
    settings=json.loads((ROOT/'configs/active-contract-probing-recovery-updater-v1.json').read_text())
    settings['allow_metadata_api']=True
    inputs=json.loads((PARENT/'updater-inputs.json').read_text())
    plans=json.loads((HERE/'decoded-first-plans.json').read_text())
    save(HERE/'preexecution.json',{'freeze_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),'reuses_all_first_plans':True,'new_probe_plan_model_calls':0})
    reports=[]
    for job in inputs['jobs']:
        data=job['data'];probes=validate_probes(data,plans[job['id']])
        observations=[]
        for probe in probes:observations.append(await generation.native_probe(job,probe,inputs['fixture'],inputs['bindings']))
        save(HERE/f"{job['id']}-observations.json",observations)
        evidence={r['id'] for r in observations}
        payload,compiled=generation.model_request(job['id'],'decisions',generation.REWRITE_PROMPT,{'metadata':data,'observations':observations},settings,lambda x:compile_decisions(data['old'],data['target'],data,x,evidence))
        if payload is None:
            reports.append({'job':job['id'],'status':'decisions_structural_failure','native_calls':len(probes)})
        else:
            knowledge,edits=compiled
            save(HERE/f"{job['id']}-candidate.json",{'knowledge':knowledge,'edits':edits})
            reports.append({'job':job['id'],'status':'requires_semantic_and_predecessor_review','native_calls':len(probes),'edits':len(edits)})
        save(HERE/'generation-status.json',{'jobs':reports,'benchmark_actor_calls':0,'judge_calls':0,'admitted':False})
        print(json.dumps(reports[-1]),flush=True)
    verify_files(ROOT,frozen['files'])
    save(HERE/'generation-status.json',{'jobs':reports,'benchmark_actor_calls':0,'judge_calls':0,'admitted':False,'all_jobs_finished':True})


if __name__=='__main__':asyncio.run(main())

"""Freeze a transparent interface recovery; no new model-selected proposals."""
import json
import sys
import tarfile
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from decode_references import decode_references
from pe6203.active_contract_probing import validate_probes
from pe6203.benchmark import write_json
from pe6203.experiment import sha,freeze_files,verify_files

HERE=Path(__file__).resolve().parent;PARENT=HERE.parent;ROOT=PARENT.parents[2]


def main():
    assert not (HERE/'preexecution.json').exists()
    original=json.loads((PARENT/'pre-model-freeze.json').read_text())
    verify_files(ROOT,original['files'])
    inputs=json.loads((PARENT/'updater-inputs.json').read_text())
    plans={};provenance=[]
    for job in inputs['jobs']:
        source=PARENT/f"{job['id']}-plan-audit.json"
        first=json.loads(source.read_text())['attempts'][0]['response']
        before=json.loads(first['choices'][0]['message']['content'])
        after=decode_references(job['data'],before)
        validate_probes(job['data'],after)
        for a,b in zip(before['probes'],after['probes'],strict=True):
            assert {k:v for k,v in a.items() if k!='basis'}=={k:v for k,v in b.items() if k!='basis'}
        plans[job['id']]=after
        provenance.append({'job':job['id'],'source':str(source.relative_to(ROOT)),'sha256':sha(source),'first_response_id':first['id'],'probe_count':len(after['probes'])})
    write_json(HERE/'decoded-first-plans.json',plans)
    write_json(HERE/'plan-provenance.json',provenance)
    cfg=json.loads((ROOT/'configs/active-contract-probing-updater-v1.json').read_text())
    cfg['spend_guard']['ledger']='results/raw/active-contract-probing-recovery-20261101/spend-ledger.json'
    write_json(ROOT/'configs/active-contract-probing-recovery-updater-v1.json',cfg)
    spec=json.loads((ROOT/'experiments/active-contract-probing-v1.json').read_text())
    spec['id']='active-contract-probing-reference-recovery-v1.1'
    spec['status']='frozen recovery of unexecuted first proposals; original strict v1 closed nonadmitted'
    spec['updater_config']='configs/active-contract-probing-recovery-updater-v1.json'
    spec['generation'].update({
        'plan_source':'ALL4 first responses from v1, selected by attempt index0 before any native result. No new probe-plan model request. Keep every probe and exactly its ID/tool/arguments/question/order. Decode basis references by frozen deterministic rules; ambiguous/unsupported references fail closed.',
        'llm_calls':'Exactly one decisions call per job, at most one existing structural repair. Normal4/max8 logical calls, existing transport retry unchanged. No further recovery/repeated sampling in this version.',
        'native_calls':'Exactly14 model-selected behavioral calls (3,3,4,4) and14 catalogs, each once in a fresh fixture; parent4 setup calls not repeated.',
        'admission':'Same whole-bundle semantic and predecessor checks as parent. No manual semantic rewrite or favorable subset. The sole registered structural change is basis decoding before native execution. Every claim decision still passes original compiler. At least one legal nonduplicate update required.',
        'recovery_reason':'All four first plans had valid route/arguments after unique basis-reference decoding. Original generic error/placeholder interface prevented mechanism execution. This is a recorded engineering correction, not a new research mechanism or evidence of efficacy.'})
    spec['recovery_fairness']='No actor or judge data have been observed for this candidate. Recovery is development provenance, never independent validation. All original9 failed/abstained generation requests and cost retained; count both ledgers. Exact final knowledge still frozen before original actor calls.'
    write_json(ROOT/'experiments/active-contract-probing-recovery-v1.json',spec)
    originals=[*PARENT.glob('*-audit.json'),*PARENT.glob('*-plan.json'),*PARENT.glob('*-decisions.json'),*PARENT.glob('*-candidate.json'),*PARENT.glob('*-observations.json')]
    originals += [PARENT/n for n in ['generation-preexecution.json','generation-status.json','reference-decoding-diagnostic.json','balance-after-generation.json','generation-decision.json']]
    originals += [ROOT/f'results/raw/active-contract-probing-generation-20261101/{n}' for n in ['spend-ledger.json','generation.stdout','generation.stderr']]
    original_hashes=freeze_files(ROOT,originals)
    archive=PARENT/'generation-raw.tar.gz'
    with tarfile.open(archive,'w:gz') as tf:
        for name in original_hashes:tf.add(ROOT/name,arcname=name,recursive=False)
    write_json(PARENT/'generation-raw-manifest.json',{'archive':archive.name,'archive_sha256':sha(archive),'files':original_hashes})
    extras=[p for p in HERE.iterdir() if p.is_file() and p.name not in ['pre-model-freeze.json','recovery-source.tar.gz']]
    extras += [ROOT/'tests/test_active_probe_reference.py',ROOT/'configs/active-contract-probing-recovery-updater-v1.json',ROOT/'experiments/active-contract-probing-recovery-v1.json',PARENT/'generation-raw-manifest.json',PARENT/'pre-model-freeze.json']
    extra_hashes={**original_hashes,**freeze_files(ROOT,extras)}
    archive=HERE/'recovery-source.tar.gz'
    with tarfile.open(archive,'w:gz') as tf:
        for name in extra_hashes:tf.add(ROOT/name,arcname=name,recursive=False)
    write_json(HERE/'pre-model-freeze.json',{'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'parent_freeze_commit':'54626f3','files':{**original['files'],**extra_hashes},'archive':archive.name,'archive_sha256':sha(archive),'parent_source_archive':str((PARENT/'generation-source.tar.gz').relative_to(ROOT)),'parent_source_sha256':original['archive_sha256'],'new_native_calls_at_freeze':0,'new_model_calls_at_freeze':0,'tests':'21 reference/provenance/compiler tests passed; original45 focused tests passed.'})
    print(json.dumps({'reused_first_proposals':len(plans),'native_calls_planned':sum(len(p['probes']) for p in plans.values()),'new_probe_plan_calls':0,'model_calls':0}))


if __name__=='__main__':main()

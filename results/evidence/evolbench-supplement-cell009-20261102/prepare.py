"""Freeze a single supplemental official evaluation, without model calls."""
import copy
import hashlib
import json
import subprocess
from pathlib import Path

E=Path(__file__).resolve().parent
ROOT=E.parents[2]
source=ROOT/'results/raw/relation-witness-basis-pilot-20261102/cells/cell-009/run'
cp=json.loads((source/'execution-checkpoint.json').read_text())
cfg=cp['result']['config']
out=Path('results/raw/evolbench-supplement-cell009-20261102')
assert not (ROOT/out).exists()
assert not (E/'freeze.json').exists()
config={k:copy.deepcopy(cfg[k]) for k in ['judge','judge_recovery','request_retry','request_timeout_seconds','spend_guard']}
config['spend_guard']['ledger']=str(out/'spend-ledger.json')
files=[p for p in source.rglob('*') if p.is_file()]
files += [ROOT/'results/raw/relation-witness-basis-dev-costs-20261102/spend-ledger.json',ROOT/'results/raw/relation-witness-basis-pilot-20261102/plan.json',E/'authorization.json',E/'run_supplement.py',Path(__file__).resolve(),E/'tests.txt',E/'preparation-errors.json']
files += sorted((ROOT/'src/pe6203').glob('*.py'))
files += [ROOT/'.cache/mcpevol/upstream'/n for n in ['src/custom/prompt/eval_error_prompt.py','src/custom/analysis/answer/evaluation.py','src/custom/utils/test_utils.py']]
plan={'id':'evolbench-supplement-cell009-20261102',
 'classification':'user_requested_supplemental_judge_only_not_primary_experiment_or_independent_validation',
 'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
 'source_run':str(source.relative_to(ROOT)),
 'source_cell':{'id':'cell-009','task_id':283,'version':'middle','strategy':'selective_patch','seed':0},
 'output':str(out),'endpoint':cp['result']['model_endpoints']['judge'],'config':config,
 'execution_order':'Saved slots1through5;firstvalid per slot;max2logicalattempts plus existing1transportretry;stop on anynewunknown/provider mismatch',
 'inclusion':'The only existing latest69 trajectory without complete five-slot official scores, selected by missingness, not score. No newactor/fixture/tool run.',
 'exclusion':'All68fullyscored trajectories and unrun cell010; original377missinginputexcluded.',
 'data':'Exact existing checkpoint and five prepared officialrubric+concise-counts-v1 prompts; no promptrewording or newshuffle.',
 'acceptance':'Five valid originalTF/grounding/PE integer ratings; exact frozenmodel/provider. Null ifincomplete. No scorethreshold for retry.',
 'decision':'Report supplementary score only. Original fatal EVAL and missingprimaryscore remain unchanged; no developmentpromotion or independentvalidation. Existingproductjudgment retained independently.',
 'fees':'Independent uncappedledger. Oldunknown unchanged; thisexplicituserrequest authorizesonlythisone supplementalbatch. Anynewunknown stops. No preflightmodelrequests; credentials checkedlocally.',
 'files':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
(E/'freeze.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
(E/'freeze.sha256').write_text(hashlib.sha256((E/'freeze.json').read_bytes()).hexdigest()+'\n')
print('Frozen',len(plan['files']),'input/code files, five slots, one existing trajectory, modelcalls0')

"""Verify interrupted cohort without filling missing ratings or relaxing promotion."""
import hashlib,json,tarfile
from decimal import Decimal
from pathlib import Path
from raw_cell_verifier import inspect_cell,sha
HERE=Path(__file__).resolve().parent

def main():
    m=json.loads((HERE/'raw-at-stop-manifest.json').read_text());arc=HERE/m['archive'];assert sha(arc.read_bytes())==m['archive_sha256']
    with tarfile.open(arc) as t:files={x.name:t.extractfile(x).read() for x in t if x.isfile()}
    assert {n:sha(v) for n,v in files.items()}==m['files'];prefix=m['prefix']+'/'
    def read(n):return json.loads(files[prefix+n])
    plan,state=read('plan.json'),read('experiment.json');assert sha(files[prefix+'plan.json'])==files[prefix+'plan.sha256'].decode().strip()
    src=json.loads((HERE/'prefreeze-manifest.json').read_text());assert sha((HERE/src['archive']).read_bytes())==src['archive_sha256']
    with tarfile.open(HERE/src['archive']) as t:source={x.name:t.extractfile(x).read() for x in t if x.isfile()}
    assert all(sha(source[n])==h for n,h in plan['files'].items())
    lock=read('knowledge-lock.json');assert lock['plan_sha256']==sha(files[prefix+'plan.json'])
    assert all(sha(files[prefix+n])==h for n,h in lock['files'].items())
    for item in state['cells'].values():assert all(sha(files[prefix+n])==h for n,h in item['files'].items())
    freeze=json.loads((HERE/'partial-review-freeze.json').read_text());assert freeze['reviews']==9 and freeze['all_available_actor_reviews_before_scores']
    assert all(sha((HERE/n).read_bytes())==h for n,h in freeze['files'].items())
    mapping=json.loads((HERE/'blind-map.json').read_text());reverse={v:k for k,v in mapping.items()};rows=[];ids=[];slots=0
    for cell in plan['cells']:
        status=state['cells'].get(cell['id'],{}).get('status','not_started');base=f"cells/{cell['id']}/run/"
        if status=='evaluated':
            row,receiptids=inspect_cell(files,prefix,cell,'original_benchmark_development');ids.extend(receiptids);slots+=5
        elif status=='judge_incomplete':
            r,t=read(base+'result.json'),read(base+'raw_trace.json');responses=[e['response'] for e in t['events'] if e['type']=='agent_response'];assert r['TF'] is None and r['PE'] is None and r['judge_status']=='incomplete';assert r['execution_status']=='max_rounds' and len(responses)==12 and not t['stop'] and t['exceeded'];assert r['config']['agent']==plan['config']['agent'];assert t['question']==next(q['question'] for q in plan['tasks'] if q['idx']==cell['task_id']);assert read(base+'knowledge.json')==read(f"adaptations/{cell['task_id']}-{cell['version']}-{cell['strategy']}/knowledge.json")
            assert all(v['provider']=='DigitalOcean' and v['model']==plan['config']['agent']['model'] for v in responses);ids.extend(v['id'] for v in responses);cost=sum(Decimal(str(v['usage']['cost'])) for v in responses);assert abs(cost-Decimal(str(r['cost']['agent']['usd'])))<Decimal('1e-12')
            packed=read(base+f"EVAL/{cell['task_id']}.json")['eval_result']; assert packed['aggregate']['successful_runs']==0 and len(packed['runs'])==5 and all('result' not in s for s in packed['runs'])
            calls=[e for e in t['events'] if e['type']=='tool_result'];row={'cell_id':cell['id'],'task_id':cell['task_id'],'stage':cell['version'],'strategy':cell['strategy'],'execution_status':r['execution_status'],'TF':None,'PE':None,'tool_calls':len(calls),'tool_errors':sum(bool(e['result'].get('isError')) for e in calls),'cost_usd':{'agent':str(cost),'judge':None},'judge_slots':0}
        else:
            assert status=='not_started';row={'cell_id':cell['id'],'task_id':cell['task_id'],'stage':cell['version'],'strategy':cell['strategy'],'execution_status':'not_started','TF':None,'PE':None,'core_pass':None,'properties':None,'judge_slots':0};rows.append(row);continue
        rid=reverse[cell['id']];review=json.loads((HERE/f'blind-reviews/{rid}.json').read_text());packet=HERE/f'blind-inputs/{rid}.json';assert sha(packet.read_bytes())==review['input_sha256'];assert review['core_pass']==all(v=='pass' for v in review['properties'].values())
        for a in json.loads(packet.read_text())['artifacts']:assert sha(files[prefix+base+'workspace/'+a['path']])==a['sha256']
        row.update(review_id=rid,core_pass=review['core_pass'],properties=review['properties'],cohort_status=status);rows.append(row)
    ledger=json.loads(files[plan['config']['spend_guard']['ledger']]);settled=[r for r in ledger['requests'] if r['status']=='settled'];unknown=[r for r in ledger['requests'] if r['status']=='unknown_charge'];assert len(settled)==104 and len(unknown)==1 and len(ledger['requests'])==105;assert ledger['blocked'] and unknown[0]['actual_usd'] is None and 'response_id' not in unknown[0];pre=[r for r in settled if r['max_completion_tokens']==32];assert len(pre)==2;assert len(ids)==len(set(ids));assert set(ids)=={r['response_id'] for r in settled if r not in pre};known=sum(Decimal(r['actual_usd']) for r in settled);assert known==Decimal(ledger['known_usd']);assert slots==40
    out={'integrity_verified':True,'scope':'at interruption, not completed development','candidate':'relation_witness_basis','planned_cells':10,'actors_executed':9,'fully_scored_cells':8,'judge_slots':40,'unstarted_cells':['cell-010'],'judge_incomplete_cells':['cell-009'],'rows':rows,'known_usd':str(known),'settled_requests':104,'unknown_requests':1,'unknown_reservation_usd':ledger['unknown_reserved_usd'],'reservation_is_actual_charge':False,'source_files_verified':len(plan['files']),'raw_files_verified':len(files),'development_complete':False,'development_pass':False,'validation_started':False,'goal_complete':False,'gate_bound':'Treated133 candidate completion at most1/2 after remainingcell,SPalready1/2; strict gain impossible.235candidate core0/1<SP1/1 also fails frozenretention. This does not establish full-cohortTF or unrunartifactquality.','attribution':'283and235knowledge byteidenticalSP; theirdifferences are not evidence of interventioneffect. Timeout transport rootcause unknown; no responseID or billreceipt.'}
    print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

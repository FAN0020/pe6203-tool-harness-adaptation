"""Build artifact-review packets without reading scores or model reasoning."""
import hashlib
import json
import shutil
from pathlib import Path
from pe6203.project_episode_projection import audit_store

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
RAW=ROOT/'results/raw/extensions/project-episode-training-v1'
BASE=ROOT/'experiments/extensions/project-episode-training-v1'

def main():
    plan=json.loads((RAW/'plan.json').read_text())
    state=json.loads((RAW/'experiment.json').read_text())
    for i,cell in enumerate(plan['cells'],1):
        episode=f'P{i:02d}';dest=HERE/'review-inputs'/f'{episode}.json'
        if dest.exists() or state['cells'].get(cell['id'],{}).get('status')!='evaluated':continue
        directory=RAW/'cells'/cell['id']/'run'
        trace=json.loads((directory/'raw_trace.json').read_text())
        result=json.loads((directory/'result.json').read_text())
        oracle=json.loads((BASE/'evaluation'/f'oracle-{cell["task_id"]}.json').read_text())
        files=list((directory/'workspace').rglob('tasks.json'))
        assert len(files)<=1, 'Unexpected multiple stores require explicit review'
        store=json.loads(files[0].read_text()) if files else None
        copied=None
        if files:
            copied=HERE/'review-artifacts'/episode/'tasks.json'
            copied.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(files[0],copied)
        packet={'episode':episode,'task_id':cell['task_id'],'execution_status':result['execution_status'],
            'answer':trace.get('answer'), 'properties':audit_store(oracle,store),
            'expected_counts':{k:oracle[k] for k in ('total_records','root_records','non_root_records')},
            'project':store.get('projects',[]) if store else [],
            'store_path':str(copied.relative_to(HERE)) if copied else None,
            'store_sha256':hashlib.sha256(files[0].read_bytes()).hexdigest() if files else None,
            'trace_sha256':hashlib.sha256((directory/'raw_trace.json').read_bytes()).hexdigest(),
            'calls':[{'native_tool':result['model_tool_routes'].get(e['call']['function']['name'],{}).get('tool_name'),
                      'isError':bool(e['result'].get('isError'))}
                     for e in trace['events'] if e['type']=='tool_result']}
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(json.dumps(packet,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'packets':len(list((HERE/'review-inputs').glob('*.json'))),'scores_exposed':False}))

if __name__=='__main__':main()

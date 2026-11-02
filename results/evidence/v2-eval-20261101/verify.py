"""Verify archived QI-V2 results without APIs or model calls."""
import hashlib
import json
import statistics
import tarfile
from pathlib import Path

HERE=Path(__file__).resolve().parent

def sha(data):return hashlib.sha256(data).hexdigest()

def main():
    manifest=json.loads((HERE/'manifest.json').read_text())
    arc=HERE/manifest['archive']
    assert sha(arc.read_bytes())==manifest['archive_sha256']
    with tarfile.open(arc) as t:
        files={m.name.removeprefix(manifest['archive_prefix']):t.extractfile(m).read() for m in t if m.isfile()}
    assert {n:sha(b) for n,b in files.items()}==manifest['source_files']
    assert all(sha((HERE/n).read_bytes())==h==sha(files[n]) for n,h in manifest['published_result_copies'].items())
    summary=json.loads(files['summary.json'])
    assert len(summary['rows'])==summary['planned']==27
    assert summary['scored']==25 and summary['completed_execution']==19
    slots=0;failed=[]
    for row in summary['rows']:
        if row['TF'] is None:
            assert row['status']=='adaptation_failed' and row['execution_status']=='not_started'
            failed.append(row['id']);continue
        data=json.loads(files[f"cells/{row['id']}/run/EVAL/{row['task_id']}.json"])['eval_result']
        assert len(data['runs'])==5 and data['aggregate']['successful_runs']==5
        for k,name in [('TF','task_fulfillment'),('PE','planning_and_efficiency')]:
            values=[r['result'][name] for r in data['runs']]
            assert all(type(v) is int and 1<=v<=10 for v in values)
            assert abs(statistics.mean(values)-row[k])<1e-10
            assert abs(statistics.mean(values)-data['aggregate'][name+'_mean'])<1e-10
        slots+=5
    assert len(failed)==2 and slots==125
    out={'verified':True,'archive_sha256':manifest['archive_sha256'],'source_files':len(files),
         'published_result_copies':len(manifest['published_result_copies']),
         'planned':27,'scored':25,'official_valid_slots':slots,'normally_completed':19,
         'adaptation_failed_cells':failed,'new_model_calls':0,
         'limits':'Integrity and recorded-score recomputation; no new model calls or manual artifact correctness certification.'}
    print(json.dumps(out,ensure_ascii=False,indent=2))

if __name__=='__main__':main()

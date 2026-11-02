"""Offline recheck of every native operation and final state, with no tool execution."""
import json
from pathlib import Path
from run_native import prior,sha
E=Path(__file__).resolve().parent
ROOT=E.parents[2]
plan=json.loads((ROOT/'experiments/ready-link-native-v1.json').read_text())
assert sha(ROOT/'experiments/ready-link-native-v1.json')==json.loads((E/'native-preexecution.json').read_text())['plan_sha256']
count=negative=0
for stage,case_id,route in plan['schedule']:
    dest=E/f'native/{stage}-{case_id}-{route}'
    case=next(c for c in plan['cases'] if c['id']==case_id)
    rows=json.loads((dest/'observations.json').read_text())
    assert all(json.loads((dest/f'{i:02d}-response.json').read_text())==row for i,row in enumerate(rows,1))
    pid=prior.new_id(rows[0]['response'])
    ids=prior.listed_ids(rows[-1]['response'],case['nodes'])
    state=json.loads((dest/f'{len(rows):02d}-state.json').read_text())
    normal,expected=prior.audit_state(state,case,pid,ids)
    assert normal==expected
    saved=json.loads((dest/'result.json').read_text())
    assert saved['normalized_state']==normal and saved['expected_state']==expected and saved['state_matches']
    for row in rows:
        if row['negative_control']:
            n=row['index'];assert (dest/f'{n:02d}-state.json').read_bytes()==(dest/f'{n-1:02d}-state.json').read_bytes()
            assert row['response'].get('isError') or prior.content(row['response']).startswith('Error:')
            negative+=1
    count+=len(rows)
assert count==232 and negative==6
from pe6203.ready_link import CERTIFICATES,digest
for row in json.loads((ROOT/'experiments/ready-link-feedback-v1.json').read_text())['observations']:
    cert=row['result'];assert digest(cert)==CERTIFICATES[row['stage']]
    assert cert['native_spec_sha256']==sha(ROOT/'experiments/ready-link-native-v1.json')
    assert cert['native_result_sha256']==sha(E/'native-results.json')
print(json.dumps(dict(verified=True,paths=18,native_calls=count,negative_controls=negative,model_calls=0)))

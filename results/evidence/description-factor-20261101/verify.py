"""Offline, read-only verification of the closed generation feasibility study."""
import ast
import hashlib
import json
import tarfile
from decimal import Decimal
from pathlib import Path

HERE=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text())
freeze=read(HERE/'pre-model-freeze.json')
manifest=read(HERE/'archive-manifest.json')
packs={}
for label in ('source','raw'):
    path=HERE/f'{label}.tar.gz'
    assert hashlib.sha256(path.read_bytes()).hexdigest()==manifest[label]['sha256']
    with tarfile.open(path) as archive:
        data={m.name:archive.extractfile(m).read() for m in archive.getmembers() if m.isfile()}
    assert set(data)==set(manifest[label]['files'])
    assert all(hashlib.sha256(b).hexdigest()==manifest[label]['files'][n] for n,b in data.items())
    packs[label]=data
source,raw=packs['source'],packs['raw']
assert set(source)==set(freeze['files'])
assert all(hashlib.sha256(source[p]).hexdigest()==h for p,h in freeze['files'].items())
inputs=json.loads(source['results/evidence/description-factor-20261101/updater-inputs.json'])
tree=ast.parse(source['results/evidence/description-factor-20261101/generate.py'])
prompt=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PROMPT' for t in n.targets))
ledger=json.loads(raw['updater-ledger.json'])
assert len(ledger['requests'])==2 and not ledger['blocked'] and Decimal(ledger['unknown_reserved_usd'])==0
cost=Decimal('0');ids=[];stages=[]
for stage in ('middle','late'):
    audit=json.loads(raw[f'{stage}-updater-audit.json'])
    assert len(audit['attempts'])==1 and not audit.get('transport_retries')
    record=audit['attempts'][0];response=record['response'];ids.append(response['id'])
    assert record['request']==[{'role':'system','content':prompt},{'role':'user','content':json.dumps(inputs[stage],ensure_ascii=False)}]
    assert response['provider']=='DigitalOcean' and response['choices'][0]['finish_reason']=='stop'
    assert json.loads(response['choices'][0]['message']['content'])=={'deletions':[]}
    assert json.loads(raw[f'{stage}-proposal.json'])=={'deletions':[]}
    assert json.loads(raw[f'{stage}-deletion-log.json'])==[]
    assert json.loads(raw[f'{stage}-candidate-knowledge.json'])==json.loads(raw[f'{stage}-SP-knowledge.json'])
    cost+=Decimal(str(response['usage']['cost']))
    stages.append({'stage':stage,'deletions':0,'characters_removed':0,'candidate_equals_SP':True})
assert set(ids)=={r['response_id'] for r in ledger['requests']}
assert all(r['status']=='settled' and r['actual_provider']=='DigitalOcean' for r in ledger['requests'])
assert cost==Decimal(ledger['known_usd'])==Decimal(read(HERE/'decision.json')['known_usd'])
assert read(HERE/'decision.json')['actor_calls']==0
print(json.dumps({'verified':True,'source_files':len(source),'raw_files':len(raw),'updater_requests':2,'known_usd':str(cost),'unknown_cost_items':0,'stage_results':stages,'decision':'reject_generation_v1_no_actor_trial','goal_complete':False}))

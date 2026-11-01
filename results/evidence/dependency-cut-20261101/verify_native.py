"""Offline native evidence replay. Keep failed v1 distinct from corrected v2."""
import hashlib
import json
import tarfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]

def sha(data):return hashlib.sha256(data).hexdigest()

def main():
    m=json.loads((HERE/'native-manifest.json').read_text());a=HERE/m['archive'];assert sha(a.read_bytes())==m['sha256']
    with tarfile.open(a) as tf:files={x.name:tf.extractfile(x).read() for x in tf if x.isfile()}
    assert {k:sha(v) for k,v in files.items()}==m['files']
    prefix=str(HERE.relative_to(ROOT))+'/'
    def read(name):return json.loads(files[name])
    counts=[]
    for version,sub,runner in [('v1','', 'run_native.py'),('v2','native-v2/','run_native_v2.py')]:
        planpath=f'experiments/dependency-cut-native-{version}.json';p=read(planpath)
        pre=read(prefix+sub+'native-preexecution.json');assert pre['plan_sha256']==sha(files[planpath]);assert pre['runner_sha256']==sha(files[prefix+runner])
        for x in p['sources']:assert sha(files[x['path']])==x['sha256']
        expected_by_key={n['key']:n for n in p['case']['nodes']};levels={};count=0;states=[];negative=0
        for stage,method in p['schedule']:
            base=prefix+sub+f'native-{stage}-{method}/';obs=read(base+'observations.json');r=read(base+'result.json')
            assert len(obs)==r['native_calls'];count+=len(obs)
            state=read(base+f'{len(obs):02d}-state.json');assert len(state['projects'])==1 and len(state['tasks'])==8 and not state.get('subtasks')
            actual={t['name']:t for t in state['tasks']};ids={t['id']:t['name'] for t in state['tasks']};assert len(actual)==len(ids)==8
            diff=[];normalized=[]
            for key,n in expected_by_key.items():
                t=actual[n['name']];levels[key]=0 if n['parent'] is None else levels[n['parent']]+1
                assert t['projectId']==state['projects'][0]['id'] and t.get('level',0)==levels[key] and t['completed'] is False
                assert (ids[t['parentId']] if t.get('parentId') else None)==(expected_by_key[n['parent']]['name'] if n['parent'] else None)
                assert [ids[x] for x in t.get('dependsOn',[])]==[expected_by_key[k]['name'] for k in n['dependsOn']]
                for f in ('name','details','priority','complexity','estimatedHours','status','tags'):
                    if t.get(f)!=n[f]:diff.append((key,f))
                if version=='v1':assert t['details']==n['details'].strip()
                else:assert t['details']==n['details']
                normalized.append({k:v for k,v in t.items() if k not in ('id','projectId','parentId','dependsOn','createdAt','updatedAt')})
            if version=='v1':assert diff==[(k,'details') for k in expected_by_key] and not r['state_matches']
            else:assert not diff and r['state_matches']
            for i,o in enumerate(obs,1):
                assert read(base+f'{i:02d}-response.json')==o
                text='\n'.join(c.get('text','') for c in o['response'].get('content',[]))
                error=bool(o['response'].get('isError')) or text.startswith('Error:')
                assert error==o['negative_control']
                if error:
                    negative+=1;assert files[base+f'{i:02d}-state.json']==files[base+f'{i-1:02d}-state.json']
            states.append(normalized)
        assert all(s==states[0] for s in states) and count==52 and negative==2
        decision=read(prefix+sub+'native-decision.json');assert decision['admitted']==(version=='v2') and decision['model_calls']==0
        counts.append({'version':version,'native_calls':count,'negative_controls':negative,'admitted':decision['admitted']})
    print(json.dumps({'verified':True,'files':len(files),'versions':counts,'native_calls_total':104,'model_calls':0,'usd':'0','benchmark_success':False},indent=2))

if __name__=='__main__':main()

"""Targeted field/reference diagnostics only; never repair artifacts or replace the frozen audit."""
import hashlib,json
from pathlib import Path
E=Path(__file__).resolve().parent;ROOT=E.parents[2];B=ROOT/'experiments/extensions/dependency-factorial-v1'
def main():
    for p in sorted((E/'review-inputs').glob('*.json')):
        x=json.loads(p.read_text());out=E/'review-analysis'/f'{p.stem}-diff.json'
        if out.exists():continue
        o=json.loads((B/'evaluation'/f'oracle-{x["task_id"]}.json').read_text());s=json.loads((E/x['store_path']).read_text()) if x['store_path'] else {'tasks':[],'projects':[]}
        by={t.get('name'):t for t in s['tasks']};keys={n['key']:by[n['name']]['id'] for n in o['nodes'] if n['name'] in by};diffs=[]
        for n in o['nodes']:
            if n['name'] not in by:diffs.append({'key':n['key'],'missing_record':True});continue
            t=by[n['name']];expected={k:n[k] for k in ['details','priority','complexity','estimatedHours','tags','status']}
            expected.update(parentId=keys.get(n['parent']),dependsOn=[keys.get(k,'MISSING:'+k) for k in n['dependsOn']],level=0 if n['parent'] is None else 1,completed=False)
            for k,v in expected.items():
                actual=t.get(k)
                if k=='parentId':actual=actual or None
                elif k in ['tags','dependsOn']:v=sorted(v);actual=sorted(actual) if isinstance(actual,list) else actual
                if actual==v:continue
                if k=='details':v={'length':len(v),'sha256':hashlib.sha256(v.encode()).hexdigest()};actual={'length':len(actual or ''),'sha256':hashlib.sha256((actual or '').encode()).hexdigest()}
                diffs.append({'key':n['key'],'field':k,'expected':v,'actual':actual})
        out.parent.mkdir(exist_ok=True);out.write_text(json.dumps({'review_id':p.stem,'differences':diffs,'note':'Missing/extra/duplicate project/records are governed by frozen audit_store; this narrow diagnostic does not replace it.'},indent=2)+'\n')
        print(json.dumps({'id':p.stem,'differences':len(diffs)}))
if __name__=='__main__':main()

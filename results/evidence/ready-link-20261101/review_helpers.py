"""Record explicit coordinator property judgments; audit data, never score via keywords."""
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path
E=Path(__file__).resolve().parent
def save_review(rid,properties,rationale):
    p=E/'blind-inputs'/f'{rid}.json'
    dest=E/'blind-reviews'/f'{rid}.json';dest.parent.mkdir(exist_ok=True)
    assert not dest.exists()
    obj=dict(review_id=rid,input_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),reviewed_at=datetime.now(timezone.utc).isoformat(),properties=properties,core_pass=all(v=='pass' for v in properties.values()),rationale=rationale,official_scores_seen_before_review=False,reviewer='Same coordinator,not independent human or strict methodblind;frozen rubric,direct visible call/state/final inspection.')
    dest.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')

def state_audit(rid):
    path=E/'blind-artifacts'/rid/'.agentic-tools-mcp/tasks/tasks.json'
    state=json.loads(path.read_text());tasks=state['tasks'];byid={x['id']:x for x in tasks}
    assert len(byid)==len(tasks) and all(byid)
    refs={t['id']:([t['parentId']] if t.get('parentId') else [])+t.get('dependsOn',[]) for t in tasks}
    missing=[(k,v) for k,values in refs.items() for v in values if v not in byid]
    def visit(k,stack):
        if k in stack:return False
        return all(visit(v,stack|{k}) for v in refs[k] if v in byid)
    acyclic=all(visit(k,set()) for k in byid)
    parents={t['parentId'] for t in tasks if t.get('parentId')}
    counts=dict(records=len(tasks),parents=len(parents),leaves=len(tasks)-len(parents),missing=missing,acyclic=acyclic,legacy_subtasks=len(state.get('subtasks',[])))
    dest=E/'review-analysis';dest.mkdir(exist_ok=True)
    (dest/f'{rid}-state.json').write_text(json.dumps(dict(counts=counts,state_sha256=hashlib.sha256(path.read_bytes()).hexdigest()),indent=2)+'\n')
    return counts

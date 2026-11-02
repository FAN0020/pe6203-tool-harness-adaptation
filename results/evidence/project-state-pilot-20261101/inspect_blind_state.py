"""Read current blinded persisted state and mutation arguments; no method/score fields."""
import json
import sys
from collections import Counter
from pathlib import Path

FOLDER = Path(__file__).resolve().parent

def main():
    name = sys.argv[1]
    packet = json.loads((FOLDER/'blind-inputs'/f'{name}.json').read_text())
    artifacts = [a for a in packet['artifacts'] if a['path'].endswith('/tasks/tasks.json')]
    assert len(artifacts) == 1
    store = json.loads((FOLDER/'blind-artifacts'/name/artifacts[0]['path']).read_text())
    tasks = store['tasks']; counts = Counter(t.get('id') for t in tasks)
    ids = {t['id'] for t in tasks if t.get('id')}
    parents = {t['id']: t.get('parentId') for t in tasks if t.get('id')}
    aliases = {t['id']: f'R{i:02}' for i,t in enumerate(tasks,1) if t.get('id')}
    bad_refs = []
    edges = {}
    for t in tasks:
        refs = ([t['parentId']] if t.get('parentId') else []) + t.get('dependsOn',[])
        for ref in refs:
            if ref not in ids: bad_refs.append({'task':t.get('id'),'missing':ref})
        edges[t.get('id')] = refs
    def cycle(graph):
        visiting,done=set(),set()
        def visit(key):
            if key in visiting:return True
            if key in done:return False
            visiting.add(key)
            if any(visit(ref) for ref in graph.get(key,[]) if ref in graph):return True
            visiting.remove(key);done.add(key);return False
        return any(visit(key) for key in graph if key not in done)
    mutations = []
    for i,c in enumerate(packet['calls'],1):
        if c['tool'].split('__')[0] in ('create_task','update_task','delete_task','create_subtask','update_subtask','delete_subtask','analyze_task_complexity'):
            args=json.loads(c['arguments']);args.pop('workingDirectory',None)
            mutations.append({'call':i,'tool':c['tool'],'arguments':args,'result':c['result']})
    projected=[]
    for i,t in enumerate(tasks,1):
        row={k:v for k,v in t.items() if k not in ('id','projectId','createdAt','updatedAt')}
        row['record']=f'R{i:02}';row['parent']=aliases.get(t.get('parentId'));row['dependencies']=[aliases.get(x,x) for x in t.get('dependsOn',[])];row['children']=[aliases.get(c['id']) for c in tasks if c.get('parentId')==t.get('id')]
        row.pop('parentId',None);row.pop('dependsOn',None);projected.append(row)
    out={'review_id':name,'projects':store['projects'],'records':len(tasks),'unique_nonempty_ids':len(ids),'empty_ids':sum(not t.get('id') for t in tasks),'duplicate_ids':{str(k):v for k,v in counts.items() if v>1},'missing_references':bad_refs,'parent_cycle':cycle({k:[v] for k,v in parents.items() if v}),'dependency_cycle':cycle({t['id']:t.get('dependsOn',[]) for t in tasks}),'legacy_subtasks':len(store.get('subtasks',[])),'tasks':projected,'mutations':mutations,'limits':'Mechanical graph audit and output projection, not automatic task-quality judgment.'}
    dest=FOLDER/'review-assist';dest.mkdir(exist_ok=True);(dest/f'{name}.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ('mutations','tasks')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()

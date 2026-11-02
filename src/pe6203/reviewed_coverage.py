"""Exact source-reviewed redundant-line policy; no new model or runtime action."""
from copy import deepcopy
import hashlib
from .selective import canonical

SERVER='@modelcontextprotocol/server-sequential-thinking'
HOSTS={SERVER+'::'+n for n in ('sequentialthinking','parallel-thinking','convergent-synthesis')}
POLICIES={'middle':'e3caf7da8e37ab3919fe2f080fd591d7992b93df017b9fbfccd402fb75e5a07f',
          'late':'9d07479ed0b91c2363243765d2c321716e189747d06b7d1063de91ea84194f30'}
def digest(x):return hashlib.sha256(canonical(x).encode()).hexdigest()

def compile_knowledge(base,target,feedback):
    knowledge=deepcopy(base['knowledge'])
    changed={r['tool_id'] for r in base['diff']['changed']+base['diff']['added']}
    if base['status']=='no_change' or not changed.intersection(HOSTS):return knowledge,[]
    stage=target['version']
    rows=[r for r in feedback if r.get('stage')==stage and r.get('server')==SERVER and r.get('tool')=='__reviewed_document_coverage__']
    if stage not in POLICIES or len(rows)!=1 or digest(rows[0]['result'])!=POLICIES[stage]:
        raise ValueError('Exact reviewed coverage policy required')
    cert=rows[0]['result'];native={t['tool_id']:t for t in target['tools']}
    for tid,expected in cert['contracts'].items():
        if tid not in changed or tid not in native or digest(native[tid])!=expected:
            raise ValueError('Reviewed contract is absent, unchanged or differs from the reviewed source')
    removed={};changes=[]
    for edit in cert['deletions']:
        tid=edit['tool_id'];line=edit['line'];lines=native[tid]['description'].splitlines()
        if tid not in cert['contracts'] or lines[line]!=edit['text'] or line in removed.setdefault(tid,set()):
            raise ValueError('Invalid deletion target')
        removed[tid].add(line)
    for edit in cert['deletions']:
        tid=edit['tool_id'];tool=native[tid];evidence=edit['evidence']
        if evidence['kind']=='property':
            if tool['parameters']['properties'][evidence['parameter']]!=evidence['schema']:
                raise ValueError('Property witness differs')
            if 'context_property' in evidence:
                context=evidence['context_property']
                if tool['parameters']['properties'][context['parameter']]!=context['schema']:
                    raise ValueError('Context witness differs')
        elif evidence['kind']=='description':
            if evidence['line'] in removed[tid] or tool['description'].splitlines()[evidence['line']]!=evidence['text']:
                raise ValueError('Description witness changed or deleted')
        else:raise ValueError('Unknown coverage witness')
        changes.append({'operation':'delete_source_reviewed_redundancy','tool_id':tid,'line':edit['line'],'field':'description','evidence':POLICIES[stage]})
    for tool in knowledge['tools']:
        if tool['tool_id'] in removed:
            tool['description']=''.join(line for n,line in enumerate(tool['description'].splitlines(keepends=True)) if n not in removed[tool['tool_id']])
            if not tool['description'].strip():raise ValueError('Empty description')
    return knowledge,changes

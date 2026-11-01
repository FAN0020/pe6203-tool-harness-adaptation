"""Deletion-only cross-field factoring; semantic coverage requires separate review."""
from copy import deepcopy
from .selective import adapt_result

def inventory(old, target):
    base=adapt_result(old,target)
    changed={t['tool_id'] for t in base['diff']['changed']+base['diff']['added']}
    return [dict(tool_id=t['tool_id'],description_lines=t['description'].splitlines(),
                 parameters=deepcopy(t['parameters']),output_schema=deepcopy(t['output_schema']))
            for t in target['tools'] if t['tool_id'] in changed]

def indices(value, lines):
    if not isinstance(value,list) or not value or any(type(n) is not int or not 0<=n<len(lines) for n in value) or len(set(value))!=len(value):
        raise ValueError('Invalid or duplicate line index')
    return set(value)

def compile_factor(old,target,proposal):
    base=adapt_result(old,target)
    knowledge=deepcopy(base['knowledge'])
    inv={r['tool_id']:r for r in inventory(old,target)}
    if not isinstance(proposal,dict) or set(proposal)!={'deletions'} or not isinstance(proposal['deletions'],list):
        raise ValueError('Expected deletions only')
    removed={};log=[]
    for row in proposal['deletions']:
        if not isinstance(row,dict) or set(row)!={'tool_id','lines','coverage','reason'} or row['tool_id'] not in inv:
            raise ValueError('Unknown changed tool or invalid deletion fields')
        identity=row['tool_id']; lines=inv[identity]['description_lines']
        selected=indices(row['lines'],lines)
        if removed.setdefault(identity,set()) & selected:
            raise ValueError('Overlapping deletion')
        removed[identity]|=selected
        if not isinstance(row['reason'],str) or not row['reason'].strip() or not isinstance(row['coverage'],list) or not row['coverage']:
            raise ValueError('Missing coverage or reason')
    for row in proposal['deletions']:
        identity=row['tool_id']; record=inv[identity]; lines=record['description_lines']
        for evidence in row['coverage']:
            if not isinstance(evidence,dict):raise ValueError('Invalid coverage')
            kind=evidence.get('kind')
            if kind=='description' and set(evidence)=={'kind','lines','quote'}:
                cited=indices(evidence['lines'],lines)
                if cited & removed[identity]:raise ValueError('Coverage is itself deleted')
                text='\n'.join(lines[n] for n in sorted(cited))
            elif kind in ('parameters','output_schema') and set(evidence)=={'kind','path','quote'}:
                path=evidence['path']; text=record[kind]
                if not isinstance(path,list) or not path or any(not isinstance(x,str) for x in path):raise ValueError('Invalid schema path')
                try:
                    for part in path:text=text[part]
                except (KeyError,TypeError):raise ValueError('Unknown schema coverage path') from None
            else:raise ValueError('Unsupported coverage kind')
            if not isinstance(text,str) or not evidence['quote'] or evidence['quote']!=text:
                raise ValueError('Coverage quote is not exact text at declared location')
        log.append({**deepcopy(row),'deleted_text':'\n'.join(lines[n] for n in sorted(row['lines']))})
    for tool in knowledge['tools']:
        if tool['tool_id'] in removed:
            # Keep every surviving character and order; no replacement prose is permitted.
            chunks=tool['description'].splitlines(keepends=True)
            tool['description']=''.join(line for n,line in enumerate(chunks) if n not in removed[tool['tool_id']])
            if not tool['description'].strip():raise ValueError('Empty remaining description')
    return knowledge,log

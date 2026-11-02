"""Decode only the frozen first proposals' changed-root references; never calls."""
from copy import deepcopy


def decode_references(data, payload):
    result=deepcopy(payload)
    roots=data['changed_ids']
    for row in result['probes']:
        value=row['basis']
        if value in roots:continue
        mentions=[root for root in roots if root in value]
        if len(mentions)==1 and value.startswith('exact changed tool_id '):
            row['basis']=mentions[0]
        elif value=='exact changed tool_id' and row['tool_id'] in roots:
            row['basis']=row['tool_id']
        elif value=='exact changed tool_id' and len(roots)==1:
            row['basis']=roots[0]
        else:
            raise ValueError('Changed-root reference cannot be uniquely decoded')
    return result

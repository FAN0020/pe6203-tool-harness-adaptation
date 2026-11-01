"""Source-certified native multi-record route attached only to its changed producer."""
import hashlib
from copy import deepcopy

from .selective import canonical

CERTIFICATE = '21d9e7b31d16f20b6a5e93ba17d67a951ba8ff261c963c04450d41d42269c775'
PRODUCER = '@pimzino/agentic-tools-mcp::create_project'


def compile_knowledge(base, target, feedback):
    knowledge=deepcopy(base['knowledge'])
    changed={x['tool_id'] for x in base['diff']['changed']+base['diff']['added']}
    if base['status']=='no_change' or PRODUCER not in changed or target['version']!='late':
        return knowledge,[]
    rows=[x for x in feedback if x.get('stage')=='late'
          and x.get('server')=='@pimzino/agentic-tools-mcp' and x.get('tool')=='create_project']
    if len(rows)!=1:raise ValueError('Missing unique native batch certificate')
    cert=rows[0]['result']
    if hashlib.sha256(canonical(cert).encode()).hexdigest()!=CERTIFICATE:
        raise ValueError('Unreviewed native batch certificate')
    native={t['tool_id']:t for t in target['tools']}
    for identity,expected in [(cert['changed_record'],cert['record_sha256']),
                              (cert['parser_record'],cert['parser_record_sha256'])]:
        if identity not in native or hashlib.sha256(canonical(native[identity]).encode()).hexdigest()!=expected:
            raise ValueError('Unknown producer or native parser contract')
    tool=next(t for t in knowledge['tools'] if t['tool_id']==PRODUCER)
    tool['usage_rules'].extend(cert['rules'])
    return knowledge,[{'operation':'add_certified_native_batch_route','tool_id':PRODUCER,
                       'rule':rule,'evidence':CERTIFICATE} for rule in cert['rules']]

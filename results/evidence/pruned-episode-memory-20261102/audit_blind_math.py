"""AST-only extraction of visible delivered code; never compile/evaluate/execute it."""
import ast
import hashlib
import json
import re
from pathlib import Path

HERE=Path(__file__).resolve().parent


def inspect(rid):
    p=HERE/'blind-inputs'/f'{rid}.json'
    answer=json.loads(p.read_text())['answer']
    out={'review_id':rid,'input_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'blocks':[],'executed_generated_code':False}
    for i,code in enumerate(re.findall(r'```python\n(.*?)```',answer,re.S)):
        row={'block':i,'code_sha256':hashlib.sha256(code.encode()).hexdigest()}
        try:tree=ast.parse(code)
        except SyntaxError as e:row['syntax_error']={'line':e.lineno,'message':e.msg}
        else:
            row['functions']={n.name:sorted({ast.unparse(c.func) for c in ast.walk(n) if isinstance(c,ast.Call)}) for n in tree.body if isinstance(n,ast.FunctionDef)}
            row['operator_maps']={t.id: {ast.unparse(k):ast.unparse(v) for k,v in zip(n.value.keys,n.value.values)} for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.value,ast.Dict) for t in n.targets if isinstance(t,ast.Name) and any(isinstance(k,ast.Attribute) and k.attr in {'Pow','FloorDiv','Mod'} for k in n.value.keys)}
        out['blocks'].append(row)
    return out


if __name__=='__main__':
    out=[inspect(rid) for rid in ['R06','R04']]
    (HERE/'static-code-evidence.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

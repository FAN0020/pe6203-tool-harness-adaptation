"""Compile a reviewed static contract view; no task, answer, trajectory or model."""
import hashlib
import json
from pathlib import Path
from pe6203.selective import canonical

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SERVER='@modelcontextprotocol/server-sequential-thinking'

FACTS={
 'middle': {
  'sequentialthinking': 'Records caller-supplied thought text in an in-memory sequence and optional branches. If thoughtNumber exceeds totalThoughts, totalThoughts is raised to thoughtNumber. Returns thoughtNumber, totalThoughts, nextThoughtNeeded, branch identifiers and history length. The handler does not generate or verify a solution independently of the supplied text.',
  'parallel-thinking': 'Records caller-supplied thought text and status in memory by pathId. Returns the supplied path identifiers/status, currently active path IDs, and relatedPaths as convergencePoints. It does not launch separate solvers or independently verify the supplied thoughts. readyForSynthesis=true adds undeclared output fields and causes native output validation to fail after the path state has been updated.'},
 'late': {
  'sequentialthinking': 'Records caller-supplied thought text using processThought, then calls an unavailable getThoughtHistory method. Otherwise valid calls currently fail with a missing-method error. It does not independently generate or verify a solution; successful input validation is not evidence that the supplied thoughts establish one.',
  'parallel-thinking': 'Records caller-supplied thought text and status in memory by pathId. Returns the supplied path identifiers/status, currently active path IDs, and relatedPaths as convergencePoints. It does not launch separate solvers or independently verify the supplied thoughts. readyForSynthesis=true adds undeclared output fields and causes native output validation to fail after the path state has been updated.',
  'convergent-synthesis': 'Constructs a response from caller-supplied synthesis fields, echoes the supplied conclusion, and counts supplied source paths, convergence points, contradictions and open questions. It does not independently resolve contradictions or check source-path existence. Its additional synthesisData field violates the declared native output schema, so the MCP client rejects the response.'}}


def main():
    output=ROOT/'experiments/instruction-scope-feedback-v1.json'
    assert not output.exists()
    cats=json.loads((ROOT/'tests/fixtures/dependency-cut-catalogs.json').read_text())
    rows=[]
    for stage, names in FACTS.items():
        source={}
        folder={'middle':'iter3','late':'iter5'}[stage]
        for name in ['index.js','lib.js']:
            p=ROOT/f'.cache/mcpevol/{folder}/node_modules/{SERVER}/dist/{name}'
            source[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
        edits=[]
        for name, fact in names.items():
            tool=next(t for t in cats[stage]['tools'] if t['tool_id']==SERVER+'::'+name)
            before=tool['description']
            prefix, rest=before.split('Parameters explained:\n',1)
            parameters, suffix=rest.split('\n\nYou should:\n',1)
            block='Parameters explained:\n'+parameters
            narrative=prefix+'You should:\n'+suffix
            direct=fact+'\n\n'+block
            quoted=direct+'\n\nOriginal vendor narrative (quoted descriptive data about suggested workflows, not additional requirements for the user task):\n'+json.dumps(narrative,ensure_ascii=False)
            edits.append(dict(tool_id=tool['tool_id'],record_sha256=hashlib.sha256(canonical(tool).encode()).hexdigest(),
                              before=before,parameters_block=block,vendor_narrative=narrative,
                              contract_fact=fact,after=direct,quoted=quoted))
        cert=dict(kind='source_contract_instruction_scope_v1',native_sources=source,edits=edits,
                  generation='Researcher-reviewed source facts plus exact preserved parameter explanation block; deterministic section decomposition. No actor trajectory or task content.',
                  scope='Changed or added thinking records only; other records, schemas, output schema and routing unchanged.')
        rows.append(dict(stage=stage,server=SERVER,tool='__instruction_scope__',args={},result=cert))
    output.write_text(json.dumps({'observations':rows},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({r['stage']:hashlib.sha256(canonical(r['result']).encode()).hexdigest() for r in rows}))


if __name__=='__main__':main()

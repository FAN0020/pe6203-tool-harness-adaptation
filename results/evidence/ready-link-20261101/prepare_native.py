"""Freeze task-free native cases before execution; no benchmark content."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def main():
    dest = ROOT / 'experiments/ready-link-native-v1.json'
    assert not dest.exists()
    prior = json.loads((ROOT / 'experiments/dependency-cut-native-v2.json').read_text())
    parents = dict(A=None, B=None, C='A', D='A', E='C', F='E', G='B', H='B')
    profiles = {
        'ancestor_ready': dict(A=[], B=[], C=['A'], D=['A'], E=['C'], F=['E'], G=['B'], H=['B']),
        'cross_chain': dict(A=[], B=['A'], C=['B'], D=['C'], E=['D'], F=['E'], G=['F'], H=['G']),
        'forward_mixed': dict(A=[], B=[], C=['D', 'G'], D=['H'], E=['C'], F=['E'], G=[], H=[]),
    }
    cases = []
    for i, (kind, dependencies) in enumerate(profiles.items(), 1):
        nodes = []
        for j, key in enumerate('ABCDEFGH'):
            nodes.append(dict(key=key, name=f'Probe {key} 保存',
                details=f'Generic Unicode preservation {key}: αβ 数据. All supplied fields must survive.',
                priority=1+j, complexity=1+j%5, estimatedHours=j+1,
                tags=['probe', key], status='pending', parent=parents[key], dependsOn=dependencies[key]))
        cases.append(dict(id=903000+i, kind=kind, nodes=nodes))
    sources = prior['sources'] + [dict(path=p, sha256=sha(ROOT/p)) for p in [
        'results/evidence/ready-link-20261101/run_native.py',
        'results/evidence/ready-link-20261101/prepare_native.py',
        'results/evidence/dependency-cut-20261101/sources/llmcompiler/src/llm_compiler/task_fetching_unit.py',
    ]]
    schedule = []
    routes = ['direct', 'global_defer', 'ready_link']
    for stage in ['middle', 'late']:
        for i, case in enumerate(cases):
            order = routes[i:] + routes[:i]
            if stage == 'late': order = list(reversed(order))
            schedule += [[stage, case['id'], route] for route in order]
    save(dest, dict(id='ready-link-native-v1', cases=cases, schedule=schedule, sources=sources,
        server='@pimzino/agentic-tools-mcp', model_calls=0, usd='0',
        rules='Actual receipt IDs only. Each wave sees only IDs returned before that wave. Native calls serial; waves are a static dependency bound, not observed actor performance. Direct waits for parent+all dependencies; global_defer creates by parent then rewrites every nonempty dependency list; ready_link creates when parent ready, includes the complete dependency list only when all refs ready, and links each pending record as soon as its own+all ref IDs ready, alongside later creation. Never partial dependencies or modified scalar fields.',
        negative_control='One invalid missing-ID update after each ready_link path; must error and preserve all store bytes.',
        acceptance='All18 final stores exactly match all fields, hierarchy, levels and dependency arrays, all6 negative controls preserve state. No graph/outcome selection. Failure blocks original dev. Fewer calls than global_defer on all three profiles is expected, but no claim of dominance over direct, saved actor rounds, or original success.',
        boundaries='Synthetic native-only state equivalence. Not benchmark or training episodes. No benchmark question/answer/scoredtrace enters cases or knowledge. No actor scheduler change.',
        literature=dict(paper='https://arxiv.org/html/2312.04511v3', repo='https://github.com/SqueezeAILab/LLMCompiler', sha='a00c9d35507507da70e8c637eee64efc8c1857ae',
            locations=['src/llm_compiler/task_fetching_unit.py:100-133'],
            borrow='Ready-prerequisite release rather than global barriers. Conditional inline writes are our adaptation to this native API, not claimed as the authors algorithm.',
            excluded='No planner prompts, symbolic argument runtime, parallel executor, replanning, benchmark traces or examples. Static tool knowledge only.')))
    print(json.dumps({'cases':len(cases),'paths':len(schedule),'model_calls':0,'plan_sha256':sha(dest)}))

if __name__ == '__main__': main()

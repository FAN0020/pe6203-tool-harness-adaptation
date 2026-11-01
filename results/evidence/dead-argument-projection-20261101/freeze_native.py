"""Build a finite, task-free native equivalence schedule before any probe call."""
import hashlib
import itertools
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PLAN = ROOT / 'experiments/dead-argument-native-v1.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def variants(fields):
    return [dict((name, value) for name, value in zip(fields, values) if value is not None)
            for values in itertools.product(*fields.values())]


def main():
    assert not PLAN.exists()
    runs = []
    for stage, folder in [('middle', 'iter3'), ('late', 'iter5')]:
        fields = {'detailed': [None, False, True]}
        if stage == 'middle':
            fields['allow_variables'] = [None, False, True]
        else:
            fields.update(show_ast=[None, False, True], check_balanced=[None, False, True], max_depth=[None, 1, 100])
        calls = []
        for expression in ['8-3', '8+', 'q+(2*7)']:
            for i, flags in enumerate(variants(fields)):
                args = dict(expression=expression, **flags)
                if stage == 'late':
                    args['allow_variables'] = False
                calls.append(dict(tool='validate_syntax', arguments=args, group=expression, variant=i, expect='equivalent'))
        controls = [{'expression': 17}]
        if stage == 'late':
            controls = [{'expression': '8-3'}, {'expression': '8-3', 'allow_variables': False, 'detailed': 'invalid'},
                        *[{'expression': '8-3', 'allow_variables': False, 'max_depth': x} for x in [0, 101]]]
        for args in controls:
            calls.append(dict(tool='validate_syntax', arguments=args, expect='error'))
        runs.append(dict(id=f'{stage}-math', stage=stage, server='math-mcp', calls=calls))
        for i, flags in enumerate(variants({'convergenceDetected': [None, False, True], 'needsNewPath': [None, False, True]})):
            calls = []
            for step, (status, ready) in enumerate([('active', False), ('completed', False), ('completed', True)], 1):
                args = dict(pathId='synthetic_alpha', thought=f'Fixture event {step}', pathNumber=1, totalPaths=1,
                            thoughtInPath=step, pathStatus=status, readyForSynthesis=ready, **flags)
                calls.append(dict(tool='parallel-thinking', arguments=args, group=f'parallel-{step}', variant=i, expect='equivalent'))
            runs.append(dict(id=f'{stage}-parallel-{i:02d}', stage=stage, server='@modelcontextprotocol/server-sequential-thinking', calls=calls))
        base = dict(pathId='synthetic_alpha', thought='Fixture event 1', pathNumber=1, totalPaths=1,
                    thoughtInPath=1, pathStatus='active', readyForSynthesis=False)
        runs.append(dict(id=f'{stage}-parallel-controls', stage=stage, server='@modelcontextprotocol/server-sequential-thinking', calls=[
            dict(tool='parallel-thinking', arguments=dict(base, relatedPaths=['synthetic_beta']), expect='related_paths_change'),
            dict(tool='parallel-thinking', arguments=dict(base, convergenceDetected='invalid'), expect='error')]))
    sources = [ROOT / p for p in ['configs/server-profiles.json', 'configs/benchmark-source.json', 'src/pe6203/transport.py', 'src/pe6203/experiment.py'] if (ROOT / p).exists()]
    for folder in ['iter3', 'iter5']:
        sources += sorted((ROOT / f'.cache/mcpevol/{folder}/node_modules/math-mcp/dist').rglob('*.js'))
        sources += [ROOT / f'.cache/mcpevol/{folder}/node_modules/@modelcontextprotocol/server-sequential-thinking/dist/index.js']
    sources += [HERE / 'freeze_native.py', HERE / 'run_native.py']
    sources += sorted(p for p in (HERE / 'sources').iterdir() if p.is_file())
    save(PLAN, dict(id='dead-argument-native-v1', purpose='Task-free behavioral-equivalence admission diagnostic; not benchmark development or validation.',
        source=[dict(path=str(p.relative_to(ROOT)), sha256=sha(p)) for p in sources], runs=runs,
        tool_calls=sum(len(r['calls']) for r in runs), catalog_calls=len(runs), model_calls=0, cost_usd=0,
        invariants=['Exact full native result equality within each math expression and each parallel sequence step across all scheduled valid optional-value combinations.',
                    'Parallel active/completed follow-up and readyForSynthesis behavior compared across fresh identical sessions; no timing fields stripped.',
                    'Valid versus invalid expression outputs differ; relatedPaths changes convergencePoints; scheduled invalid inputs return errors.',
                    'Native implementation bytes unchanged before and after. A manual source certificate is required in addition to finite probes.'],
        limits=['Finite max_depth boundary checks do not prove all 1..100 values; source argument-use proof supplies generalization.',
                'Domain is valid advertised optional values. Invalid-argument diagnostic semantics are not claimed equivalent to omission.',
                'State timestamps are not claimed byte-identical across processes; unused flags cannot influence stored fields according to source review.'],
        order='Listed order, no retries/resampling. Preserve every result before checking. Any failed invariant closes admission pending a separately frozen explanation/test.',
        outcome_rule='Only if all invariants pass may a source-pinned static knowledge projection be considered. This does not establish a model benefit.',
        information_boundary='Synthetic tool inputs only; no benchmark question, answer or scored trajectory.',
        exclusions=['Required late allow_variables', 'Effective relatedPaths/pathStatus/readyForSynthesis', 'State-stored sequentialthinking arguments', 'Persistent project metadata', 'Unchanged safety/hygiene tools']))
    print(json.dumps(dict(plan=str(PLAN.relative_to(ROOT)), calls=sum(len(r['calls']) for r in runs), sessions=len(runs), model_calls=0)))


if __name__ == '__main__':
    main()

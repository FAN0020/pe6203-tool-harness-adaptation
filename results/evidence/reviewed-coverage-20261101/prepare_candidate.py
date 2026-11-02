"""Researcher-reviewed source coverage policy; no task data or model call."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from pe6203.parameter_coverage import parameter_pairs
from pe6203.selective import canonical

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
load = lambda p: json.loads((ROOT / p).read_text())
def save(p, x): (ROOT / p).write_text(json.dumps(x, ensure_ascii=False, indent=2) + '\n')
def digest(x): return hashlib.sha256(canonical(x).encode()).hexdigest()

REASONS = {
    'isRevision': 'Boolean type and whether previous thinking is revised are explicit in the same property schema.',
    'thought': 'The property description repeats the current thinking step within this path.',
    'totalPaths': 'The property description repeats the total number of paths being explored.',
    'thoughtInPath': 'Which thought number and thought number denote the same value within the specific path; no extra qualifier is removed.',
    'pathStatus': 'The property description and exact enum preserve the status and all four listed values.',
    'convergenceDetected': 'The boolean describes convergence with other paths. The same tool pathId property identifies the current reasoning path, preserving the omitted grammatical subject this path.',
    'needsNewPath': 'Whether to create a new parallel path and whether a new parallel path should be created express the same creation decision; the object and modality are preserved.',
    'synthesisId': 'The property description repeats the unique synthesis-session identifier.',
    'contradictions': 'Conflict or disagreement denotes the same conflict relation here; the schema explicitly retains conflict points and the conflicting path IDs.',
    'synthesizedConclusion': 'The property description repeats the unified final answer or conclusion.',
    'confidenceLevel': 'The same-property description and exact high/moderate/low enum preserve the whole line.',
    'traceability': 'Both descriptions map conclusion elements to source paths; back describes that same direction, not an extra inverse mapping.',
    'openQuestions': 'Remaining uncertainties or areas needing exploration preserves the need for further exploration; remaining already establishes that it is outstanding.'}

# Equivalent permission / ownership statements, with witnesses kept verbatim.
DESCRIPTION_PAIRS = [
    ('sequentialthinking', '- You can question or revise previous thoughts',
     '2. Feel free to question or revise previous thoughts',
     'Both explicitly permit questioning or revising previous thoughts; the later permission survives.'),
    ('parallel-thinking', '- Each path can have its own chain of thoughts',
     '2. Develop each path independently with its own reasoning chain',
     'The surviving instruction explicitly gives each path its own independent reasoning chain, preserving the per-path chain information.')]

def main():
    assert not (ROOT / 'experiments/reviewed-coverage-feedback-v1.json').exists()
    cats = load('tests/fixtures/dependency-cut-catalogs.json')
    observations, reviews, hashes = [], [], {}
    for stage in ('middle', 'late'):
        native = {t['tool_id']: t for t in cats[stage]['tools']}
        edits, retained = [], []
        for pair in parameter_pairs(cats['early'], cats[stage]):
            if pair['parameter'] not in REASONS:
                retained.append({'tool_id': pair['tool_id'], 'line': pair['line'], 'parameter': pair['parameter'], 'decision': 'retain', 'reason': 'No approved complete-coverage rule; preserve conditions/examples or unresolved meaning.'})
                continue
            evidence = {'kind': 'property', 'parameter': pair['parameter'], 'schema': pair['schema']}
            if pair['parameter'] == 'convergenceDetected':
                evidence['context_property'] = {'parameter': 'pathId', 'schema': native[pair['tool_id']]['parameters']['properties']['pathId']}
            edits.append({'tool_id': pair['tool_id'], 'line': pair['line'], 'text': pair['claim'], 'evidence': evidence, 'reason': REASONS[pair['parameter']]})
        for name, claim, witness, reason in DESCRIPTION_PAIRS:
            tool = next(t for t in cats[stage]['tools'] if t['name'] == name)
            lines = tool['description'].splitlines()
            assert lines.count(claim) == lines.count(witness) == 1
            edits.append({'tool_id': tool['tool_id'], 'line': lines.index(claim), 'text': claim,
                          'evidence': {'kind': 'description', 'line': lines.index(witness), 'text': witness}, 'reason': reason})
        host_ids = sorted({e['tool_id'] for e in edits})
        result = {'kind': 'reviewed_coverage_v1', 'stage': stage,
                  'contracts': {i: digest(native[i]) for i in host_ids}, 'deletions': edits,
                  'authority': 'Predeclared researcher-authored source coverage, not a generated model edit or a universal entailment proof. Exact contract hashes are mandatory; all other knowledge is preserved.'}
        hashes[stage] = digest(result)
        observations.append({'stage': stage, 'server': '@modelcontextprotocol/server-sequential-thinking', 'tool': '__reviewed_document_coverage__', 'result': result})
        reviews.append({'stage': stage, 'deleted_lines': len(edits), 'characters_removed': sum(len(e['text']) + 1 for e in edits), 'review': edits, 'retained_parameter_lines': retained,
                        'semantic_review': 'Every listed deletion reviewed against its complete cited source by the main coordinator; not independent-human or blind. No benchmark question, solution, product or score used.', 'admitted': True})
    save('experiments/reviewed-coverage-feedback-v1.json', {'observations': observations})
    save('results/evidence/reviewed-coverage-20261101/source-review.json', reviews)
    save('results/evidence/reviewed-coverage-20261101/policy-hashes.json', hashes)
    for suffix in ('dev', 'updater', 'validation-1', 'validation-2'):
        text = (ROOT / f'configs/parameter-coverage-{suffix}-v1.json').read_text().replace('parameter-coverage', 'reviewed-coverage')
        save(f'configs/reviewed-coverage-{suffix}-v1.json', json.loads(text))
    text = (ROOT / 'experiments/parameter-coverage-v1.json').read_text().replace('parameter-coverage', 'reviewed-coverage').replace('parameter_coverage', 'reviewed_coverage')
    spec = json.loads(text)
    spec['generation'] = {'mechanism': 'Deterministic source-reviewed coverage table, protected by full contract and policy hashes; delete certified redundant description lines only. Property schemas and cited description witnesses survive.',
                          'input': 'Original changed tool metadata only. The coverage policy is researcher-authored before new actor calls; no task questions, answers, scored trajectories or checker-generated annotations are passed as adaptation input.',
                          'scope_limit': 'Specific reviewed contracts only; this is not an automated general semantic verifier or transfer result. Unrelated tasks stay exactly SP; any changed certified contract rejects the adapter.',
                          'review': 'source-review.json lists every deletion and every retained matched parameter line. No post-actor policy edits. Deterministic compiler must reproduce reviewed bytes and preserve every other field.',
                          'manipulation_gate': 'At least 500 Unicode characters removed per stage and a strict model-visible serialized-size decrease; unchanged from the previous series.',
                          'updater_calls': 0,
                          'next': 'After exact policy/source review and tests, freeze 10 original development cells, then run only the unchanged conditional validation protocol if strict development passes.'}
    spec['execution_order'] = 'Freeze deterministic candidate, exact knowledge and ten original development cells before any model call. Use the existing development order; then only on all development gates, both independent 30-cell validation blocks with no candidate changes.'
    spec['literature'] = {'record': 'results/evidence/reviewed-coverage-20261101/research-decision.json', 'prior_fixed_pins': 'results/evidence/verified-coverage-20261101/source-pins.json'}
    spec['cost'] = 'Updater API cost zero; authoring/review disclosed as researcher effort. Separate dev/validation ledgers. Development estimate USD 0.10–0.40, not a cap; all failures and costs retained.'
    spec['status'] = 'candidate_prepared_requires_test_and_exact_knowledge_freeze'
    save('experiments/reviewed-coverage-v1.json', spec)
    print(json.dumps({'policy_hashes': hashes, 'stages': [{k: r[k] for k in ('stage', 'deleted_lines', 'characters_removed')} for r in reviews], 'model_calls': 0}))

if __name__ == '__main__': main()

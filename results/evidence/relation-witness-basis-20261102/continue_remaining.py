"""Proposed A3: carry one unresolved charge, retain incomplete judge, run only untouched cells.

Dry-run is read-only. --run requires explicit authorization for this manifest.
No original policy/source/knowledge/outcome is rewritten. No actor is resumed.
"""
import argparse
import hashlib
import json
import os
from contextlib import contextmanager
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def accounting_spec(path, data):
    unknown = [i for i, r in enumerate(data['requests']) if r['status'] != 'settled']
    if len(unknown) != 1 or data['requests'][unknown[0]]['status'] != 'unknown_charge':
        raise ValueError('Expected exactly one unresolved charge')
    return {'ledger': str(Path(path).resolve()), 'ledger_policy': data['policy'],
            'prefix_count': len(data['requests']), 'prefix_sha256': digest(data['requests']),
            'unknown_index': unknown[0]}


def allowed(data, spec):
    rows = data.get('requests', [])
    return (data.get('policy') == spec['ledger_policy']
            and data['policy'].get('limit_usd') is None
            and data.get('blocked') is True and data.get('stop_reason') == 'unknown_charge'
            and len(rows) >= spec['prefix_count']
            and digest(rows[:spec['prefix_count']]) == spec['prefix_sha256']
            and [i for i, r in enumerate(rows) if r['status'] != 'settled']
            == [spec['unknown_index']])


@contextmanager
def accounting_overlay(spec):
    from pe6203 import experiment, spend_guard
    original_ledger, original_stop = spend_guard.ledger, experiment.spend_stopped
    target = Path(spec['ledger']).resolve()

    @contextmanager
    def scoped_ledger(policy):
        with original_ledger(policy) as data:
            waived = Path(policy['ledger']).resolve() == target and allowed(data, spec)
            if waived:
                data['blocked'] = False
            try:
                yield data
            finally:
                if waived:
                    data['blocked'] = True

    def scoped_stop(policy):
        stop = original_stop(policy)
        if not stop or not policy or Path(policy['ledger']).resolve() != target:
            return stop
        return not allowed(json.loads(target.read_text()), spec)

    spend_guard.ledger, experiment.spend_stopped = scoped_ledger, scoped_stop
    try:
        yield
    finally:
        spend_guard.ledger, experiment.spend_stopped = original_ledger, original_stop


def remaining(plan, state):
    if any(c.get('status') == 'running' for c in state['cells'].values()):
        raise ValueError('Unfinished actor cannot be restarted')
    return [c['id'] for c in plan['cells'] if c['id'] not in state['cells']]


def require_authorization(here, manifest_hash):
    p = here / 'continuation-authorization.json'
    if not p.exists():
        raise ValueError('Explicit A3 authorization is missing')
    a = json.loads(p.read_text())
    if a.get('approved') is not True or a.get('manifest_sha256') != manifest_hash:
        raise ValueError('Explicit A3 authorization does not match this manifest')


def verify_preflight(plan, output, spec):
    if sha(output / 'plan.json') != spec['plan_sha256']:
        raise ValueError('Frozen plan changed')
    names = {str(p.relative_to(output)) for p in (output / 'preflight').glob('*.json')}
    if names != set(spec['preflight_files']):
        raise ValueError('Preflight inventory changed')
    records = []
    for name, expected in spec['preflight_files'].items():
        if sha(output / name) != expected:
            raise ValueError('Preflight receipt changed')
        records.extend(json.loads((output / name).read_text()))
    settled = {r.get('response_id') for r in json.loads(Path(spec['ledger']).read_text())['requests']
               if r['status'] == 'settled'}
    if plan.get('max_preflight_calls') != 2 or len(records) != 2 or {r['role'] for r in records} != {'agent', 'judge'}:
        raise ValueError('Two original preflight roles are required')
    for r in records:
        model = plan['config'][r['role']]['model']
        if (r['status'] != 'reachable' or r['model'] != model or r['actual_model'] != model
                or r['actual_provider'] != 'DigitalOcean' or r['response_id'] not in settled):
            raise ValueError('Preflight is not a matching settled success')
    return [r['response_id'] for r in records]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    here = Path(__file__).resolve().parent; root = here.parents[2]
    os.chdir(root)
    manifest = here / 'continuation-a3.json'
    if sha(manifest) != (here / 'continuation-a3.sha256').read_text().strip():
        raise ValueError('Continuation manifest changed')
    spec = json.loads(manifest.read_text()); output = root / spec['output']
    for name, expected in spec['frozen_files'].items():
        if sha(root / name) != expected:
            raise ValueError(f'Continuation input changed: {name}')
    plan = json.loads((output / 'plan.json').read_text())
    state = json.loads((output / 'experiment.json').read_text())
    if remaining(plan, state) != spec['remaining_cells']:
        raise ValueError('Only the single original unstarted cell are authorized')
    if not allowed(json.loads(Path(spec['ledger']).read_text()), spec):
        raise ValueError('Accounting stop exceeds proposed exception')
    key = os.environ.get('OPENROUTER_API_KEY_BACKUP')
    if not key:
        raise ValueError('Configured backup credential is required')
    os.environ['AGENT_API_KEY'] = os.environ['JUDGE_API_KEY'] = key
    from pe6203 import experiment, strategy_search
    experiment.check_plan(root, output, plan)
    strategy_search.check_knowledge(output)
    verify_preflight(plan, output, spec)
    if any(experiment.pending_judging(output / "cells" / c["id"] / "run", plan["config"]) for c in plan["cells"] if c["id"] not in spec["remaining_cells"]):
        raise ValueError("Existing judge recovery is outside this continuation")
    print(json.dumps({'read_only_checks': 'pass', 'remaining_cells': spec['remaining_cells'],
                      'unknown_charge_settled': False, 'model_calls': 0}), flush=True)
    if not args.run:
        return
    require_authorization(here, sha(manifest))
    original_preflight = experiment.availability_preflight

    def reuse(p, target):
        if Path(target).resolve() != output.resolve() or p != plan:
            raise ValueError('Preflight reuse is restricted to the frozen original plan')
        verify_preflight(p, target, spec)

    experiment.availability_preflight = reuse
    try:
        with accounting_overlay(spec):
            import contextlib
            with (here / "continuation-run.log").open("w") as log:
                with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                    result = experiment.run_experiment(root, output, resume=True)
    finally:
        experiment.availability_preflight = original_preflight
    print(json.dumps({'cell_count': len(result['cells']), 'stop_reason': result.get('stop_reason'),
                      'promotion_permitted': False}), flush=True)


if __name__ == '__main__':
    main()

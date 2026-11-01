"""Save explicit coordinator judgments; never infer semantic passes from a score."""
import datetime
import hashlib
import json
from pathlib import Path
E = Path(__file__).resolve().parent
ROOT = E.parents[2]
B = ROOT / 'experiments/extensions/observation-selection-v1'


def save_review(rid, properties, rationale, witness_tools):
    p = E / 'blind-inputs' / f'{rid}.json'
    packet = json.loads(p.read_text())
    fresh = 'no changes to this task' in packet['question']
    field = 'name' if 'current name' in packet['question'] else 'priority'
    tid = (902001 if field == 'name' else 902002) + (0 if fresh else 2)
    oracle = json.loads((B / 'evaluation' / f'oracle-{tid}.json').read_text())
    assert len(packet['artifacts']) == 1
    store_hash = packet['artifacts'][0]['sha256']
    calls = [c['tool'].split('__')[0] for c in packet['calls']]
    mutate = [n for n in calls if n.startswith(('create_', 'update_', 'delete_', 'move_', 'migrate_')) or n == 'parse_prd']
    assert set(properties) == {'state_preserved', 'current_value', 'evidence', 'claims'}
    if properties['state_preserved'] == 'pass':
        assert store_hash == oracle['initial_store_sha256'] and not mutate
    reads = [n for n in calls if n not in ('sequentialthinking', 'convergent-synthesis', 'parallel-thinking') and n not in mutate]
    non_witness = sum(n not in witness_tools for n in reads)
    out = {'review_id': rid, 'input_sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
           'reviewed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'properties': properties, 'core_pass': all(v == 'pass' for v in properties.values()),
           'rationale': rationale, 'official_scores_seen_before_review': False,
           'evidence_measurements': {'field': field, 'fresh': fresh, 'read_tools': reads,
               'witness_tools_reviewed_from_actual_returns': witness_tools,
               'non_witness_read_calls': non_witness, 'fresh_read_calls': len(reads) if fresh else 0,
               'mutating_calls': mutate, 'store_bytes_unchanged': store_hash == oracle['initial_store_sha256']},
           'reviewer': 'Same coordinator, not independent human or strict method-blind; cell paths visible. Actual answer and native results checked before scores.'}
    dest = E / 'blind-reviews' / f'{rid}.json'
    dest.parent.mkdir(exist_ok=True)
    assert not dest.exists()
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
    print(rid, out['core_pass'], out['evidence_measurements'])

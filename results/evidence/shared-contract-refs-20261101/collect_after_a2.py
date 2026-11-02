"""Collect normal opaque outputs and attach the already-reviewed interrupted cell.

The latter is explicitly unblinded and incomplete; it is never relabeled evaluated.
"""
import hashlib
import json
import shutil
from pathlib import Path
import collect_blind

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RAW = ROOT / 'results/raw/shared-contract-refs-pilot-20261101'


def main():
    collect_blind.main()
    mapping = json.loads((HERE / 'blind-map.json').read_text())
    rid = next(k for k, v in mapping.items() if v == 'cell-006')
    run = RAW / 'cells/cell-006/run'
    state = json.loads((RAW / 'experiment.json').read_text())
    assert state['cells']['cell-006']['status'] == 'blocked'
    trace = json.loads((run / 'raw_trace.json').read_text())
    calls = [{'arguments': e['call']['function']['arguments'],
              'tool': e['call']['function']['name'], 'result': e['result']}
             for e in trace['events'] if e['type'] == 'tool_result']
    artifacts = []
    for p in (run / 'workspace').rglob('tasks.json'):
        relative = p.relative_to(run / 'workspace')
        dest = HERE / 'blind-artifacts' / rid / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            assert dest.read_bytes() == p.read_bytes()
        else:
            shutil.copyfile(p, dest)
        artifacts.append({'path': str(relative), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
    packet = {'review_id': rid, 'question': trace['question'], 'answer': trace.get('answer'),
              'calls': calls, 'artifacts': artifacts}
    target = HERE / 'blind-inputs' / (rid + '.json')
    if target.exists():
        assert json.loads(target.read_text()) == packet
    else:
        target.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + '\n')
    old = json.loads((HERE / 'interrupted-cell006-review.json').read_text())
    review = {'review_id': rid, 'input_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
              'properties': old['properties'], 'core_pass': old['core_pass'],
              'evidence': old['review_evidence'], 'official_scores_seen_before_review': False,
              'method_map_seen_before_review': True,
              'blinding_limitation': 'Method/task of interrupted cell were exposed during infrastructure diagnosis; prior locked unblinded review reused without changing judgments. No official scores exist for this cell.',
              'reviewer': 'sole coordinator; incomplete actor output; no independent blinded-review claim',
              'source_review': 'interrupted-cell006-review.json'}
    target = HERE / 'blind-reviews' / (rid + '.json')
    if target.exists():
        assert json.loads(target.read_text()) == review
    else:
        target.write_text(json.dumps(review, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'interrupted_review_attached': rid, 'scores_read': False}))


if __name__ == '__main__':
    main()

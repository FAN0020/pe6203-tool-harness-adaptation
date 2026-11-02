"""Copy completed current-trial evidence into stable review packets; never print labels/scores."""
import hashlib
import json
from pathlib import Path

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[2]
RAW = ROOT / 'results/raw/observed-contract-validation-20261031'


def main():
    mapping = json.loads((FOLDER / 'blind-map.json').read_text())
    state = json.loads((RAW / 'experiment.json').read_text())
    dest = FOLDER / 'blind-inputs'
    dest.mkdir(exist_ok=True)
    created = []
    for review_id, cell_id in mapping.items():
        path = dest / (review_id + '.json')
        if state['cells'].get(cell_id, {}).get('status') != 'evaluated':
            continue
        trace = json.loads((RAW / f'cells/{cell_id}/run/raw_trace.json').read_text())
        calls = [
            {'arguments': event['call']['function']['arguments'],
             'tool': event['call']['function']['name'], 'result': event['result']}
            for event in trace['events'] if event['type'] == 'tool_result'
        ]
        packet = {'review_id': review_id, 'question': trace['question'],
                  'answer': trace.get('answer'), 'calls': calls}
        if path.exists():
            assert json.loads(path.read_text()) == packet
        else:
            path.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + '\n')
            created.append(review_id)
    ready = sorted(p.stem for p in dest.glob('*.json'))
    reviewed = {p.stem for p in (FOLDER / 'blind-reviews').glob('*.json')}
    print(json.dumps({'new_packets': created, 'ready': len(ready),
                      'reviewed': len(reviewed), 'pending': [r for r in ready if r not in reviewed]}))


if __name__ == '__main__':
    main()

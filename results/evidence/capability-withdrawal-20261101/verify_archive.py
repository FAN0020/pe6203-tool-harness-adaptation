"""Offline audit: no cache, SDK, API, extraction or credential access required."""
import hashlib
import json
import sys
import tarfile
from decimal import Decimal
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from pe6203.evaluation import judge_scores


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def main():
    raw = read(HERE / 'raw-manifest.json')
    source = read(HERE / 'runtime-source-manifest.json')
    for manifest in (raw, source):
        archive = HERE / manifest['archive']
        assert digest(archive.read_bytes()) == manifest.get('archive_sha256', manifest.get('sha256'))
        with tarfile.open(archive, 'r:gz') as tf:
            assert len([m for m in tf.getmembers() if m.isfile()]) == len(manifest['files'])
            for item in manifest['files']:
                assert digest(tf.extractfile(item['path']).read()) == item['sha256']
    for name, expected in read(HERE/'review-freeze.json')['files'].items():
        assert digest((ROOT/name).read_bytes()) == expected
    decision = read(HERE/'decision.json')
    base = 'results/raw/capability-withdrawal-pilot-20261101'
    with tarfile.open(HERE/raw['archive'], 'r:gz') as tf:
        def archived(name):return json.loads(tf.extractfile(name).read())
        for row in decision['rows']:
            stem = f"{base}/cells/{row['id']}/run"
            result = archived(stem+'/result.json')
            values, error = judge_scores(archived(stem+f"/EVAL/{row['task_id']}.json"))
            assert error is None and values['TF'] == row['TF'] and values['PE'] == row['PE']
            assert result['execution_status'] == row['execution_status']
            review = read(HERE/'blind-reviews'/(row['review_id']+'.json'))
            assert row['core_pass'] == review['core_pass'] == all(v=='pass' for v in review['properties'].values())
        ids = []; total = Decimal(0)
        for ledger in decision['ledgers'].values():
            data = archived(ledger['path'])
            known = sum(Decimal(x.get('actual_usd') or '0') for x in data['requests'])
            assert known == Decimal(ledger['known_usd']) == Decimal(data['known_usd'])
            assert data['unknown_reserved_usd'] == '0'
            total += known
            ids += [x['response_id'] for x in data['requests']]
        assert len(ids) == len(set(ids)) == sum(x['requests'] for x in decision['ledgers'].values())
        assert total == Decimal(decision['round_total_usd'])
    for strategy, groups in decision['metrics'].items():
        for group, expected in groups.items():
            task = 283 if group == 'changed' else 235
            rows = [r for r in decision['rows'] if r['task_id']==task and r['strategy']==strategy]
            actual = {'n':len(rows),'completed':sum(r['execution_status']=='completed' for r in rows),
                      'core_pass':sum(r['core_pass'] for r in rows),'TF':mean(r['TF'] for r in rows),'PE':mean(r['PE'] for r in rows)}
            assert actual == expected
    print(json.dumps({'verified':True,'raw_files':len(raw['files']),'source_files':len(source['files']),
                      'executions':6,'judge_slots':30,'unique_api_requests':len(ids),'usd':str(total),
                      'decision':decision['decision'],'goal_complete':False},indent=2))

if __name__=='__main__':main()

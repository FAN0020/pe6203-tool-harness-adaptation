"""Preserve recovery receipts, all costs, reviews and specific predecessor evidence."""
import json
import tarfile
from pathlib import Path
from pe6203.benchmark import write_json
from pe6203.experiment import freeze_files,sha

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]


def main():
    recovery=HERE/'recovery'
    inputs=json.loads((recovery/'pre-model-freeze.json').read_text())['files']
    files=[p for p in recovery.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.gz' and str(p.relative_to(ROOT)) not in inputs]
    files += [ROOT/f'results/raw/active-contract-probing-recovery-20261101/{n}' for n in ['spend-ledger.json','generation.stdout','generation.stderr']]
    files += [ROOT/p for p in ['experiments/observation-coverage-feedback-v1.json','experiments/semantic-claim-repair-feedback-v2.json','experiments/capability-withdrawal-feedback-v1.json','experiments/feedback-probes-v1.json']]
    hashes=freeze_files(ROOT,files)
    archive=HERE/'recovery-raw.tar.gz'
    with tarfile.open(archive,'w:gz') as tf:
        for name in hashes:tf.add(ROOT/name,arcname=name,recursive=False)
    write_json(HERE/'recovery-raw-manifest.json',{'archive':archive.name,'archive_sha256':sha(archive),'files':hashes})
    print(json.dumps({'recovery_files':len(hashes),'archive_bytes':archive.stat().st_size}))


if __name__=='__main__':main()

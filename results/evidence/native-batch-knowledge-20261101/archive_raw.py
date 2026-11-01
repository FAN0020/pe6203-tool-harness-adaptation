"""Preserve all completed trial files and its dedicated ledger, without filtering failures."""
import hashlib
import json
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RAW = ROOT / 'results/raw/native-record-batch-pilot-20261101'
LEDGER = ROOT / 'results/raw/native-record-batch-costs-20261101'

if __name__ == '__main__':
    state = json.loads((RAW/'experiment.json').read_text())
    assert len(state['cells']) == 4 and all(x['status']=='evaluated' for x in state['cells'].values())
    files = [p for folder in [RAW, LEDGER, HERE/'workspace'] for p in folder.rglob('*') if p.is_file()]
    files += [HERE/'runner.log', HERE/'mcp.stderr.log']
    probe = json.loads((ROOT/'experiments/native-batch-probes-v1.json').read_text())
    for item in probe['sources']:
        p = ROOT/item['path']
        assert hashlib.sha256(p.read_bytes()).hexdigest() == item['sha256']
        files.append(p)
    files = sorted(set(files))
    archive = HERE/'raw-trial.tar.gz'
    assert not archive.exists(), 'Do not silently replace an evidence archive'
    with tarfile.open(archive,'w:gz') as tf:
        for p in files: tf.add(p,arcname=str(p.relative_to(ROOT)),recursive=False)
    manifest={'archive':archive.name,'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
              'files':[{'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
    (HERE/'raw-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'raw_files':len(files),'bytes':archive.stat().st_size}))

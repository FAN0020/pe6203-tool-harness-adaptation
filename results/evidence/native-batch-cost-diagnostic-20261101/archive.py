"""Preserve all native outputs, workspaces and frozen code/input sources."""
import hashlib
import json
import tarfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PLAN=ROOT/'experiments/native-batch-cost-diagnostic-v1.json'
plan=json.loads(PLAN.read_text())
files=[PLAN,HERE/'run_diagnostic.py',HERE/'research-decision.json',HERE/'preexecution.json',HERE/'runner.log',
       HERE/'native-ledger.json',HERE/'results.json',HERE/'decision.json']
for case_id,method in plan['schedule']:
    files += [p for p in (HERE/f'{case_id}-{method}').rglob('*') if p.is_file()]
files += [ROOT/s['path'] for s in plan['sources']]
files += [ROOT/p for p in ['src/pe6203/transport.py','src/pe6203/experiment.py','pyproject.toml','uv.lock']]
files=sorted(set(files))
archive=HERE/'raw-native.tar.gz'
assert not archive.exists(), 'Never silently replace an evidence archive'
with tarfile.open(archive,'w:gz') as tf:
    for p in files:tf.add(p,arcname=str(p.relative_to(ROOT)),recursive=False)
manifest={'archive':archive.name,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
          'files':[{'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
(HERE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'files':len(files),'bytes':archive.stat().st_size}))

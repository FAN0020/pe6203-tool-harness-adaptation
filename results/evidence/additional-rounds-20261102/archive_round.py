"""Archive completed raw trial and independent ledger without exposing traces."""
import argparse,hashlib,json,tarfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('slug');args=p.parse_args()
root=Path(__file__).resolve().parents[3]; e=root/f'results/evidence/{args.slug}-20261102';raw=root/f'results/raw/{args.slug}-pilot-20261102'
state=json.loads((raw/'experiment.json').read_text()); assert len(state['cells'])==10 and all(v['status']=='evaluated' for v in state['cells'].values())
plan=json.loads((raw/'plan.json').read_text()); ledger=root/plan['config']['spend_guard']['ledger']; l=json.loads(ledger.read_text()); assert all(r['status']=='settled' for r in l['requests']) and not l['blocked']
files=sorted([f for f in raw.rglob('*') if f.is_file()]+[ledger]); archive=e/'raw-trial.tar.gz';assert not archive.exists()
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
with tarfile.open(archive,'w:gz') as t:
 for f in files:t.add(f,arcname=str(f.relative_to(root)),recursive=False)
manifest={'prefix':str(raw.relative_to(root)),'archive':archive.name,'archive_sha256':sha(archive),'files':{str(f.relative_to(root)):sha(f) for f in files}}
(e/'raw-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({'files':len(files),'settled':len(l['requests']),'known_usd':l['known_usd']}))

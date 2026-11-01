"""Preserve raw outputs and exact frozen source bytes; never discard originals."""
import hashlib
import json
import sys
import tarfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
RAW=ROOT/'results/raw/extensions/observation-selection-v1'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    if sys.argv[1]=='source':
        plan=json.loads((RAW/'plan.json').read_text())
        output=HERE/'source-prefreeze.tar.gz';manifest=HERE/'prefreeze-manifest.json'
        assert not output.exists() and not manifest.exists()
        with tarfile.open(output,'w:gz') as tf:
            for name,digest in plan['files'].items():
                assert sha(ROOT/name)==digest
                tf.add(ROOT/name,arcname=name,recursive=False)
        manifest.write_text(json.dumps({'archive':output.name,'archive_sha256':sha(output),'files':plan['files']},indent=2)+'\n')
        print(json.dumps({'source_files':len(plan['files']),'compressed_bytes':output.stat().st_size}))
    elif sys.argv[1]=='raw':
        output=HERE/'raw-trial.tar.gz';manifest=HERE/'raw-manifest.json'
        assert not output.exists() and not manifest.exists()
        files=sorted(p for p in RAW.rglob('*') if p.is_file() and p.name!='.writer.lock')
        entries=[]
        with tarfile.open(output,'w:gz') as tf:
            for p in files:
                name=str(p.relative_to(ROOT));entries.append({'path':name,'sha256':sha(p),'bytes':p.stat().st_size})
                tf.add(p,arcname=name,recursive=False)
        manifest.write_text(json.dumps({'archive':output.name,'archive_sha256':sha(output),'prefix':str(RAW.relative_to(ROOT)),'files':{x['path']:x['sha256'] for x in entries}},indent=2)+'\n')
        print(json.dumps({'raw_files':len(files),'compressed_bytes':output.stat().st_size}))
    else:raise ValueError('source or raw only')

if __name__=='__main__':main()

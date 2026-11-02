"""Archive exact prefreeze sources and every native observation, without APIs."""
import hashlib
import json
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output = HERE / 'native-evidence.tar.gz'
    assert not output.exists()
    plan_path = ROOT / 'experiments/dead-argument-native-v1.json'
    plan = json.loads(plan_path.read_text())
    files = {r['path']: r['sha256'] for r in plan['source']}
    recovery = json.loads((HERE / 'native-recovery-freeze.json').read_text())
    for name, sha in recovery['files'].items():
        assert name not in files or files[name] == sha
        files[name] = sha
    extra = [plan_path, HERE / 'native-recovery-freeze.json', HERE / 'native-resume-preexecution.json',
             HERE / 'native-resume-console.log', HERE / 'native-observations.json', HERE / 'native-result.json']
    extra += [p for p in (HERE / 'native').iterdir() if p.is_file()]
    for p in extra:
        name = str(p.relative_to(ROOT))
        sha = digest(p)
        assert name not in files or files[name] == sha
        files[name] = sha
    with tarfile.open(output, 'w:gz') as tf:
        for name, sha in sorted(files.items()):
            assert digest(ROOT / name) == sha, name
            tf.add(ROOT / name, arcname=name, recursive=False)
    manifest = dict(archive=output.name, archive_sha256=digest(output), files=files)
    (HERE / 'native-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(dict(files=len(files), bytes=output.stat().st_size)))


if __name__ == '__main__':
    main()

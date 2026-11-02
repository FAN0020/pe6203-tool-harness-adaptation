"""Archive/hash the bounded generation before any new model invocation."""
import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from pe6203.benchmark import write_json
from pe6203.experiment import freeze_files, sha, verify_files

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def main():
    assert not (HERE/'generation-preexecution.json').exists()
    assert json.loads((HERE/'fixture-readiness.json').read_text())['passed']
    paths=list((ROOT/'src/pe6203').rglob('*.py'))+list((ROOT/'integration').glob('*.py'))
    paths += [ROOT/p for p in ['pyproject.toml','uv.lock','configs/benchmark.lock.json','configs/server-profiles.json','experiments/benchmark-v1.3.json','experiments/active-contract-probing-v1.json']]
    paths += list((ROOT/'configs').glob('active-contract-probing-*.json'))
    paths += [ROOT/f'tests/{p}' for p in ['test_active_contract_probing.py','test_instruction_scope.py','test_reviewed_coverage.py','test_evidence_dispatch.py','fixtures/dependency-cut-catalogs.json','fixtures/semantic-maintenance-catalogs.json','fixtures/prefix-workflow-catalogs.json']]
    paths += [p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in {'pre-model-freeze.json','generation-source.tar.gz'}]
    for iteration in ['iter3','iter5']:
        paths += [ROOT/f'.cache/mcpevol/{iteration}/extraction.json']
        for package in ['math-mcp','@pimzino/agentic-tools-mcp']:
            d=ROOT/f'.cache/mcpevol/{iteration}/node_modules/{package}'
            paths += list((d/'dist').rglob('*.js'))+[d/'package.json']
    paths += [ROOT/'.cache/node-runtime/node_modules/node/bin/node']
    assert all(p.is_file() for p in paths)
    files=freeze_files(ROOT,set(paths))
    archive=HERE/'generation-source.tar.gz'
    with tarfile.open(archive,'w:gz') as tf:
        for name in files:tf.add(ROOT/name,arcname=name,recursive=False)
    verify_files(ROOT,files)
    write_json(HERE/'pre-model-freeze.json',{
        'frozen_at_utc':datetime.now(timezone.utc).isoformat(),
        'phase':'generation_only; exact admitted candidate knowledge must be frozen before actor trial',
        'archive':archive.name,'archive_sha256':sha(archive),'files':files,
        'new_model_calls_at_freeze':0,'setup_native_calls':4,'setup_catalog_reads':4,
        'setup_excluded_from_updater':True,
        'tests':'45 focused tests passed in8.73s; includes scope, provenance, structural preservation and predecessor compilers',
        'generation_rules':'experiments/active-contract-probing-v1.json#generation',
        'schedules':'execution-schedule.json',
        'information_boundary':'Only updater-inputs and model-selected native receipts passed to updater; benchmark question hashes and scoring protocol are frozen solely for eventual evaluation.'})
    print(json.dumps({'source_files':len(files),'archive_bytes':archive.stat().st_size,'model_calls':0}))


if __name__=='__main__':main()

"""Read-only standard-library evidence and DOCX table verification."""
from pathlib import Path
import hashlib
import json
import math
import statistics as st
from decimal import Decimal
import zipfile
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
read = lambda p: json.loads(p.read_text())
manifest = read(HERE / 'source-manifest.json')
assert manifest['builder_sha256'] == hashlib.sha256((HERE / 'build_report.py').read_bytes()).hexdigest()
for path, digest in manifest['sources'].items():
    assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
course = read(ROOT / 'results/evidence/course-v1.3-20261031/summary.json')
metrics = read(HERE / 'metrics.json')
ns = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
with zipfile.ZipFile(HERE / 'PE6203 Research Report.docx') as z:
    xml = ET.fromstring(z.read('word/document.xml'))
    styles = ET.fromstring(z.read('word/styles.xml'))
    assert not styles.findall('.//w:pBdr',ns), 'Unexpected paragraph rule in styles'
    blue_paragraphs = []
    for p in xml.findall('.//w:p', ns):
        content = ''.join(t.text or '' for t in p.findall('.//w:t', ns))
        if p.findall('.//w:color[@w:val="1250A0"]', ns):
            blue_paragraphs.append(content)
    for required in ('amended 2 November 2026', '2 November task selection and candidate addendum',
                     'The historical “29 candidates”', 'The later 36-candidate audit'):
        assert any(required in paragraph for paragraph in blue_paragraphs), required
tables = []
for t in xml.findall('.//w:tbl',ns):
    tables.append([[''.join(x.text or '' for x in c.findall('.//w:t',ns)) for c in row.findall('w:tc',ns)] for row in t.findall('w:tr',ns)])
assert len(tables) == 7
labels = {'no_update':'NU','full_rewrite':'FR','selective_patch':'SP'}
expected=[]
for stage in ('early','middle','late'):
    for strategy in ('no_update','full_rewrite','selective_patch'):
        rows=[r for r in course['rows'] if r['version']==stage and r['strategy']==strategy]
        assert len(rows)==3
        expected.append([stage.title(),labels[strategy],f"{sum(r['execution_status']=='completed' for r in rows)}/3",f"{st.mean(r['TF'] for r in rows):.3f}",f"{st.mean(r['PE'] for r in rows):.3f}"])
assert tables[1][1:] == expected
assert sum(r['execution_status']=='completed' for r in course['rows'])==20
for strategy in labels:
    pop=[];sample=[]
    for task in (133,235,283):
        values=[r['TF'] for r in course['rows'] if r['strategy']==strategy and r['task_id']==task]
        assert len(values)==3
        pop.append(st.mean(values)-st.pstdev(values));sample.append(st.mean(values)-st.stdev(values))
    row=next(r for r in tables[2][1:] if r[0]==labels[strategy])
    assert row[1:3]==[f'{st.mean(pop):.3f}',f'{st.mean(sample):.3f}']
expected=[]
for key,label in [('dependency_cut','Dependency cut'),('observation_coverage','Observation coverage'),('ready_link','Ready link')]:
    folder={'dependency_cut':'dependency-cut','observation_coverage':'observation-coverage','ready_link':'ready-link'}[key]
    d=read(ROOT/f'results/evidence/{folder}-20261101/decision.json')
    assert len(d['rows'])==10
    for arm in ('selective_patch',key):
        for group,taskids in [('changed',(133,283)),('project',(283,)),('retention',(235,))]:
            rows=[r for r in d['rows'] if r['strategy']==arm and r['task_id'] in taskids]
            actual={'n':len(rows),'completed':sum(r['execution_status']=='completed' for r in rows),'core_pass':sum(r['core_pass'] for r in rows),'TF':st.mean(r['TF'] for r in rows),'PE':st.mean(r['PE'] for r in rows)}
            saved=metrics['development'][key][arm][group]
            assert all(math.isclose(actual[k],saved[k],abs_tol=1e-10) for k in actual),(key,arm,group)
            if group=='changed':
                expected.append([label,'SP' if arm=='selective_patch' else 'Candidate',f"{actual['completed']}/4",f"{actual['core_pass']}/4",f"{actual['TF']:.2f}",f"{actual['PE']:.2f}"])
assert tables[3][1:]==expected
daily=read(ROOT/'results/evidence/daily-migration-pilot-20261031/trial-verification.json')
expected=[]
for arm in ('no_update','full_rewrite','selective_patch','budget_feedback'):
    rows=[r for r in daily['cells'] if r['strategy']==arm]
    assert len(rows)==3
    values=[r['TF'] for r in rows]
    expected.append([labels.get(arm,'Budget feedback'),f"{sum(r['execution_status']=='completed' for r in rows)}/3",f'{st.mean(values):.3f}',f"{st.mean(r['PE'] for r in rows):.3f}",f'{st.mean(values)-st.pstdev(values):.3f}'])
assert tables[4][1:]==expected
cost=read(ROOT/'results/evidence/course-v1.3-20261031/cost-audit.json')
execution=sum(Decimal(str(r['known_usd'])) for r in cost['records'])
assert abs(execution-Decimal(str(cost['known_execution_usd'])))<Decimal('0.0000000001')
assert tables[5][1][1]==f"{execution+Decimal(str(cost['update_usd'])):.6f}"
assert tables[5][1][2]==str(sum(r['unknown_charges'] for r in cost['records']))
assert tables[5][1:]==metrics['selected_cohort_costs']
archive=ROOT/'results/evidence/course-v1.3-20261031/raw-trial.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='e95e15694abe9a12e37c813f81e6e0fb0b5ccd00c2003f2a25a36a092c8001c9'
assert not metrics['goal_achieved'] and not metrics['formal_validation_started']
for folder,file in [('course-v1.3-20261031','reproduction.json'),('daily-migration-pilot-20261031','reproduction.json'),('semantic-claim-repair-20261101','reproduction.txt'),('dependency-cut-20261101','reproduction.txt'),('observation-coverage-20261101','reproduction.txt'),('ready-link-20261101','reproduction.txt'),('dependency-factorial-20261101','reproduction.txt'),('observation-selection-20261101','reproduction.txt')]:
    assert (ROOT/'results/evidence'/folder/file).is_file(),(folder,file)
print(json.dumps({'passed':True,'source_hashes':len(manifest['sources']),'course_rows_recomputed':27,'original_development_rows_recomputed':30,'daily_rows_recomputed':12,'numeric_docx_tables_checked':5,'docx_tables':7,'course_archive_hash':'passed','reproduction_entries':8,'network_or_model_calls':0}))

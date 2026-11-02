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
    paragraphs = []
    for p in xml.findall('.//w:p', ns):
        content = ''.join(t.text or '' for t in p.findall('.//w:t', ns))
        paragraphs.append(content)
        if p.findall('.//w:color[@w:val="1250A0"]', ns):
            blue_paragraphs.append(content)
    for required in ('amended 2 November 2026', 'Separate QI-V2 comparison on the same original task IDs',
                     'The historical “29 candidates”', 'The offline 36-candidate audit'):
        assert any(required in paragraph for paragraph in blue_paragraphs), required
    assert not any('task selection and candidate addendum' in paragraph for paragraph in blue_paragraphs)
    assert not any('Evidence and references continued' in p for p in paragraphs)
    for number,title in (
        (17,'An LLM Compiler for Parallel Function Calling'),
        (18,'LLM+P: Empowering Large Language Models with Optimal Planning Proficiency'),
        (19,'Agentic Context Engineering: Evolving Contexts for Self-Improving Language Models'),
        (20,'A-MEM: Agentic Memory for LLM Agents'),
        (21,'Reflexion: Language Agents with Verbal Reinforcement Learning'),
        (22,'ExpeL: LLM Agents Are Experiential Learners'),
        (23,'Voyager: An Open-Ended Embodied Agent with Large Language Models'),
    ):
        assert any(f'[{number}]' in p and title in p for p in paragraphs), (number,title)
tables = []
for t in xml.findall('.//w:tbl',ns):
    tables.append([[''.join(x.text or '' for x in c.findall('.//w:t',ns)) for c in row.findall('w:tc',ns)] for row in t.findall('w:tr',ns)])
assert len(tables) == 9
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
assert tables[4][1:]==expected
v2=read(ROOT/'results/evidence/v2-eval-20261101/v2-eval/summary.json')
matched={r['strategy']:r for r in v2['matched_results']}
expected=[]
for arm in v2['strategies']:
    label='QI-V2 SP' if arm['strategy']=='selective_patch' else labels[arm['strategy']]
    mm=matched[arm['strategy']]
    expected.append([label,f"{arm['normally_completed']}/9",f"{arm['scored']}/9",f"{mm['TF']:.3f}",f"{mm['PE']:.3f}",'Not reviewed'])
assert tables[3][1:]==expected
assert (v2['planned_executions'],v2['scored_executions'],v2['matched_three_method_cells'])==(27,25,7)
v2_check=read(ROOT/'results/evidence/v2-eval-20261101/verification.json')
assert v2_check['verified'] and v2_check['official_valid_slots']==125
assert hashlib.sha256((ROOT/'results/evidence/v2-eval-20261101/raw-results.tar.gz').read_bytes()).hexdigest()==v2_check['archive_sha256']
suff=read(ROOT/'results/evidence/selective-search-20261031/confirmation-r1-review.json')['summary']['arms']
observed=read(ROOT/'results/evidence/observed-contract-validation-20261031/validation-verification.json')
budget=read(ROOT/'results/evidence/matched-existing-20261031/trial-verification.json')['summary']
oc={arm:{key:sum(block['arms'][arm]['changed'][key] for block in observed['blocks'].values()) for key in ('completed','core_pass')}
    for arm in ('selective_patch','observed_contract')}
assert oc['selective_patch']['core_pass']==oc['observed_contract']['core_pass']==0
assert tables[5][1:]==[
 ['Sufficiency feedback confirmation, all stages',f"{suff['selective_patch']['completed_execution']}/27",f"{suff['sufficiency_feedback']['completed_execution']}/27",'Not established','Rejected'],
 ['Observed contract, changed tasks, two batches',f"{oc['selective_patch']['completed']}/12",f"{oc['observed_contract']['completed']}/12",'0/12 each','Validation failed'],
 ['Budget feedback, mixed local six',f"{budget['selective_patch']['completed']}/6",f"{budget['budget_feedback']['completed']}/6",'Code/numeric defects','Lead only'],
]
daily=read(ROOT/'results/evidence/daily-migration-pilot-20261031/trial-verification.json')
expected=[]
for arm in ('no_update','full_rewrite','selective_patch','budget_feedback'):
    rows=[r for r in daily['cells'] if r['strategy']==arm]
    assert len(rows)==3
    values=[r['TF'] for r in rows]
    expected.append([labels.get(arm,'Budget feedback'),f"{sum(r['execution_status']=='completed' for r in rows)}/3",f'{st.mean(values):.3f}',f"{st.mean(r['PE'] for r in rows):.3f}",f'{st.mean(values)-st.pstdev(values):.3f}'])
assert tables[6][1:]==expected
cost=read(ROOT/'results/evidence/course-v1.3-20261031/cost-audit.json')
execution=sum(Decimal(str(r['known_usd'])) for r in cost['records'])
assert abs(execution-Decimal(str(cost['known_execution_usd'])))<Decimal('0.0000000001')
assert tables[7][1][1]==f"{execution+Decimal(str(cost['update_usd'])):.6f}"
assert tables[7][1][2]==str(sum(r['unknown_charges'] for r in cost['records']))
assert tables[7][1:]==metrics['selected_cohort_costs']
archive=ROOT/'results/evidence/course-v1.3-20261031/raw-trial.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='e95e15694abe9a12e37c813f81e6e0fb0b5ccd00c2003f2a25a36a092c8001c9'
assert observed['verified'] and not observed['success'] and len(observed['blocks'])==2
assert not metrics['goal_achieved'] and metrics['formal_validation_started'] and not metrics['formal_validation_passed']
assert metrics['validation_cohort']=='observed_contract'
for folder,file in [('course-v1.3-20261031','reproduction.json'),('daily-migration-pilot-20261031','reproduction.json'),('semantic-claim-repair-20261101','reproduction.txt'),('dependency-cut-20261101','reproduction.txt'),('observation-coverage-20261101','reproduction.txt'),('ready-link-20261101','reproduction.txt'),('dependency-factorial-20261101','reproduction.txt'),('observation-selection-20261101','reproduction.txt')]:
    assert (ROOT/'results/evidence'/folder/file).is_file(),(folder,file)
print(json.dumps({'passed':True,'source_hashes':len(manifest['sources']),'course_rows_recomputed':27,'original_development_rows_recomputed':30,'daily_rows_recomputed':12,'v2_scored_rows':25,'v2_archive_hash':'passed','recorded_validation_batches':2,'numeric_docx_tables_checked':7,'docx_tables':9,'course_archive_hash':'passed','reproduction_entries':8,'network_or_model_calls':0}))

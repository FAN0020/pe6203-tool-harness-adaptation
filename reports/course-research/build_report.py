"""Build the evidence synthesis only; never execute an actor, updater or judge."""
from pathlib import Path
import hashlib
import json
import statistics
from decimal import Decimal
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SOURCES = {
    'course': 'results/evidence/course-v1.3-20261031/summary.json',
    'course_interpretation': 'results/evidence/course-v1.3-20261031/interpretation.json',
    'course_cost': 'results/evidence/course-v1.3-20261031/cost-audit.json',
    'course_plan': 'results/evidence/course-v1.3-20261031/plan.json',
    'course_reproduction': 'results/evidence/course-v1.3-20261031/reproduction.json',
    'daily': 'results/evidence/daily-migration-pilot-20261031/trial-verification.json',
    'daily_quality': 'results/evidence/daily-migration-pilot-20261031/quality-review.json',
    'dependency_cut': 'results/evidence/dependency-cut-20261101/decision.json',
    'observation_coverage': 'results/evidence/observation-coverage-20261101/decision.json',
    'ready_link': 'results/evidence/ready-link-20261101/decision.json',
    'ready_interpretation': 'results/evidence/ready-link-20261101/interpretation.json',
    'ready_research': 'results/evidence/ready-link-20261101/research-decision.json',
    'ready_protocol': 'experiments/ready-link-v1.json',
    'semantic_repair': 'results/evidence/semantic-claim-repair-20261101/decision.json',
    'factorial': 'results/evidence/dependency-factorial-20261101/decision.json',
    'observation_diagnostic': 'results/evidence/observation-selection-20261101/decision.json',
    'literature': 'results/evidence/method-learning-20261101/method-review.json',
}
D = {key: json.loads((ROOT / path).read_text()) for key, path in SOURCES.items()}
assert len(D['course']['rows']) == 27
assert sum(r['execution_status'] == 'completed' for r in D['course']['rows']) == 20
assert not D['ready_link']['development_pass'] and not D['ready_link']['validation_started']
for row in D['course']['main_results']:
    selected = [r for r in D['course']['rows'] if r['version'] == row['stage'] and r['strategy'] == row['strategy']]
    assert len(selected) == 3
    for metric in ('TF', 'PE'):
        assert abs(statistics.mean(r[metric] for r in selected) - row[metric]) < 1e-10
for key in ('dependency_cut', 'observation_coverage', 'ready_link'):
    for arm in D[key]['metrics'].values():
        assert arm['changed']['n'] == 4 and arm['retention']['n'] == 1

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.5), Inches(11)
sec.top_margin = sec.bottom_margin = Inches(.72)
sec.left_margin = sec.right_margin = Inches(.8)
for name in ('Normal', 'Title', 'Subtitle', 'Heading 1', 'Heading 2', 'Caption'):
    st = doc.styles[name]
    st.font.name = 'Calibri'
    st.font.color.rgb = RGBColor(0, 0, 0)
    st.font.size = Pt(11 if name == 'Normal' else 24 if name == 'Title' else 17 if name == 'Heading 1' else 12)
    st.paragraph_format.space_after = Pt(7)
doc.styles['Normal'].paragraph_format.line_spacing = 1.08
doc.styles['Heading 1'].paragraph_format.space_before = Pt(0)
doc.styles['Heading 2'].paragraph_format.space_before = Pt(8)
for element in doc.styles.element.xpath('.//w:pBdr'):
    element.getparent().remove(element)
doc.core_properties.title = 'Selective Tool Knowledge Adaptation under Environment Change'
doc.core_properties.subject = 'PE6203 Group Project 4 research evidence as of 1 November 2026'
doc.core_properties.author = ''
footer = sec.footer.paragraphs[0]
footer.alignment = 2
field = OxmlElement('w:fldSimple'); field.set(qn('w:instr'), 'PAGE')
footer._p.append(field)
md = []

def para(text, style=None):
    doc.add_paragraph(text, style)
    md.extend([text, ''])

def heading(text, level=1, newpage=False):
    if newpage:
        doc.add_page_break()
    doc.add_heading(text, level)
    md.extend(['#' * (level + 1) + ' ' + text, ''])

def table(headers, rows, widths):
    t = doc.add_table(rows=1, cols=len(headers))
    t.autofit = False
    for column, width in zip(t.columns, widths):
        column.width = Inches(width)
    for c, label, width in zip(t.rows[0].cells, headers, widths):
        c.text = label; c.width = Inches(width)
        shade = OxmlElement('w:shd'); shade.set(qn('w:fill'), 'E7E6E6'); c._tc.get_or_add_tcPr().append(shade)
    repeat = OxmlElement('w:tblHeader'); t.rows[0]._tr.get_or_add_trPr().append(repeat)
    for row in rows:
        cells = t.add_row().cells
        for c, text, width in zip(cells, row, widths):
            c.text = str(text); c.width = Inches(width)
    for i, row in enumerate(t.rows):
        keep = OxmlElement('w:cantSplit'); row._tr.get_or_add_trPr().append(keep)
        for c in row.cells:
            for p in c.paragraphs:
                p.paragraph_format.space_after = Pt(5)
                p.paragraph_format.space_before = Pt(4)
                p.paragraph_format.line_spacing = 1
                for run in p.runs:
                    run.font.size = Pt(10.5); run.bold = i == 0
    md.extend(['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join('---' for _ in headers) + ' |'])
    md.extend('| ' + ' | '.join(map(str, row)) + ' |' for row in rows)
    md.append('')
    doc.add_paragraph().paragraph_format.space_after = Pt(0)

doc.add_paragraph('Selective Tool Knowledge Adaptation under Environment Change', 'Title')
md.extend(['# Selective Tool Knowledge Adaptation under Environment Change', ''])
para('PE6203 Group Project 4   |   Research report   |   1 November 2026', 'Subtitle')
heading('Research conclusion')
para('The implementation can recover specific tool capabilities after an environment change, but no tested candidate has yet demonstrated the required joint improvement over the original Selective Patch on the frozen original benchmark subset. The latest ready_link development study tied normal completion at 1 of 4 changed conditions and reduced mean official task fulfillment from 9.8 to 7.4. Its apparent product-quality gain occurred on task 133, where the two arms used identical knowledge. The candidate was closed without formal validation. [3]')
para('This report separates the completed 27-run course comparison, additional exposed development cohorts, and controlled synthetic diagnostics. Their scores are not pooled. No Update and Full Rewrite remain course baselines; new candidate studies use a fresh, contemporaneous original Selective Patch control. Five judge ratings per trajectory are measurement repeats, not five independent agent runs.')
heading('Method and contribution', 2)
para('The original Selective Patch is a deterministic metadata and reference-based updater. It compares tool identity, parameters, descriptions, output schemas and routing; expands the affected set through explicit one-hop usage-rule references; copies authoritative changed records; and validates schemas, routing and preservation of unrelated records. Tool renames without stable evidence are treated as removal plus addition. Its reference index is a lexical heuristic, not a learned dependency graph. [1, 9]')
para('No Update retains Early knowledge. Full Rewrite rebuilds structural fields from target metadata and uses the fixed model to regenerate all target descriptions. The course comparison therefore varies both update scope and generation mechanism; it is not a pure scope ablation. The later work tests source-grounded semantic repair, dependency scheduling and field-level observation knowledge while preserving the shared actor and judge. These are measured mechanism tests with negative as well as positive outcomes, not evidence of a universally superior updater.')
heading('Delivery status', 2)
para('The research objective remains unmet. Two independent validation batches have not begun because development gates failed. A causal Selective Patch under-update example and a causal over-update harm example also remain unestablished. The user reports that the presentation has ended and has removed further slide and speaker-script work from scope. No external submission or publication is claimed.')

heading('Study design and authority', newpage=True)
para('The course brief requires fixed model, decoding, tasks and judge across No Update, Full Rewrite and Selective Patch; three environment stages; TOOL, PARAM and DESC coverage; TF, PE and ECS; recovery, retention and update cost; and failure trajectories. A documented fixed subset and one trajectory repeat are allowed, although three repeats are preferred. The user adds a stronger research criterion: strict gains in normal completion and actual product quality in development and separately in each of two fresh validation batches, with no TF or retention decrease. [1, 3, 10]')
table(['Cohort', 'Conditions', 'Role'], [
    ['Course baseline', '133, 235, 283 × Early, Middle, Late × NU, FR, SP; 27 runs', 'Course comparison; one run per cell'],
    ['Current original development', '133 Middle/Late and 283 Middle/Late; 235 Late retention; 10 runs per two-arm study', 'Exposed development; fresh SP control'],
    ['Daily migration', 'Task 90 × three stages × four methods; 12 runs', 'Separate exposed capability-recovery cohort'],
    ['Synthetic diagnostics', 'Predeclared generated cases in separate protocols', 'Mechanism discrimination only'],
], [1.5, 3.6, 1.8])
para('Task 133 concerns secure mathematical-expression guidance; task 283 requests a structured project plan; task 235 checks unchanged chart-tool behavior. TOOL coverage in the course subset consists of relevant optional additions, not mandatory deletion or rename. The data and tools are available for the chosen original conditions. The missing-input search route for task 377 remains closed. Task 283 shares a server family with earlier development, so the subset is not an unseen-family holdout.')
heading('Shared execution and information boundaries', 2)
para('Current development fixes deepseek/deepseek-v4.1-flash-1017 on DigitalOcean with fallback disabled, temperature 0, 4096 actor completion tokens including reasoning, 12 rounds, and request/run/tool timeouts of 120/900/30 seconds. No model seed is sent. The official rubric uses five first-valid judge slots, at most two logical attempts per slot and the frozen transport-retry policy. Judge tool observations are limited to 1000 characters. Historical course routing configuration is retained as recorded, rather than retroactively described as the current provider lock. [1, 3]')
para('Updaters may consume changed metadata, relevant source and frozen task-free native probes. They may not consume benchmark questions, answers, scored trajectories or manually distilled answer recipes. Candidate knowledge, sources and hashes, order, repetitions, acceptance, failure handling and an independent ledger are frozen before model calls. A change of actor, model, single-run budget or acceptance threshold would require a different authorized study.')

heading('Course baseline results', newpage=True)
para('TF denotes task fulfillment and PE denotes planning and efficiency, each on the official 1–10 scale. Normal counts trajectories with completed execution status, independently of their judge scores.')
course_rows = []
labels = {'no_update':'NU', 'full_rewrite':'FR', 'selective_patch':'SP'}
for r in D['course']['main_results']:
    cells = [x for x in D['course']['rows'] if x['version']==r['stage'] and x['strategy']==r['strategy']]
    course_rows.append([r['stage'].title(), labels[r['strategy']], f"{sum(x['execution_status']=='completed' for x in cells)}/3", f"{r['TF']:.3f}", f"{r['PE']:.3f}"])
table(['Stage', 'Method', 'Normal', 'TF', 'PE'], course_rows, [1.5,1.1,1.4,1.4,1.5])
para('All 27 trajectories have complete official ratings: 20 ended normally, five reached the round limit and two were output-truncated. Mean scores do not imply correct final artifacts. Every row contains only three different tasks and one execution per task. [1]')
ecsrows=[]
for e in D['course']['matched_ecs']:
    c=next(c for c in D['course']['update_cost_by_strategy'] if c['strategy']==e['strategy'])
    ecsrows.append([labels[e['strategy']],f"{e['upstream_population']:.3f}",f"{e['paper_sample']:.3f}",str(c['tokens_total']),f"{c['seconds_total']:.3f}",f"{c['usd_total']:.6f}"])
table(['Method','ECS pop','ECS sample','Update tokens','Seconds','USD'], ecsrows, [1,1.05,1.15,1.55,1,1.15])
para('ECS is calculated for each matched task as mean TF across Early, Middle and Late minus its standard deviation, then averaged over the three tasks. Both the released population and paper sample conventions are retained. SP has zero model-update tokens but does not lead ECS in this cohort. Early task 133 varied despite identical knowledge across methods, affecting ECS without an adaptation difference.')
para('For changed tasks, SP minus NU mean TF is 0.0 in Middle and +0.1 in Late; FR is −0.1 and +0.1. For unchanged task 235, all methods have TF 10 in Middle and Late, with zero change from NU Early. This establishes score retention of chart-specification behavior, not browser-rendered dashboard correctness. NU Middle also repeats the map call five times, showing that repeated calls are not unique to Full Rewrite.')

heading('Mechanisms tested beyond the baseline', newpage=True)
heading('Semantic contract repair', 2)
para('The LLM in semantic repair made content decisions rather than merely rephrasing a fixed note. The first version proposed edits and dependency scope but failed source validation. In version 2, the program fixed the admissible changed fields and supplied a claim inventory; the LLM classified claims as retained, replaced or unknown with source support. It retained four and replaced ten of fourteen claims. This is narrower than unrestricted learned impact discovery. Six original runs on 133 Middle/Late and 235 Late produced equal changed-task normal completion at 1/2 and core quality at 0/2, despite TF rising from 9.3 to 9.9 and PE from 5.9 to 7.7. The version was rejected. [4]')
heading('Dependency scheduling knowledge', 2)
para('dependency_cut separated record creation from dependency linking, eliminating the need to know dependency identifiers during initial creation. ready_link then made this conditional: include the complete dependency set when all real identifiers already exist; otherwise defer the link and release it when its own prerequisites are available. It never invents identifiers or submits partial dependency sets. The change is confined to knowledge attached to the changed create_project record; task 133 and retention-task knowledge remain byte-identical to SP. [3, 5]')
para('The borrowed principle is ready-prerequisite release in LLMCompiler, pinned to paper 2312.04511v3 and author commit a00c9d35507507da70e8c637eee64efc8c1857ae, task_fetching_unit.py lines 100–133. The original planner, symbolic argument runtime, parallel executor and replanning are not imported. Here a static tool-knowledge rule must be adopted by the unchanged actor; it does not execute the schedule itself. Native tests therefore establish legality and state equivalence, not agent completion.')
heading('Observation coverage knowledge', 2)
para('observation_coverage records which returned fields can support which claims and conservatively invalidates stale observations after mutation. Its proposed benefit was fewer unnecessary reads and better grounded final claims. All four original project trajectories made zero get_task calls, weakening the specific explanation that removing redundant get_task reads caused the observed Middle success. A later controlled diagnostic also found no reliable read saving and one false claim that a field was unavailable through all read-only tools. [6]')
heading('How prior literature was used', 2)
para('ACE contributes local playbook operations and feedback accounting; A-MEM contributes related-memory evolution; Reflexion relies on executable feedback and further attempts. Earlier delta_notes, lexical linked_notes and pre-frozen feedback_notes did not implement those complete systems. Author code and paper versions are pinned in reference 8. Full Reflexion retries would alter the current actor protocol, and answer-bearing benchmark experiences cannot be supplied to the updater. A failed implementation does not establish that an entire method family is ineffective.')

heading('Original development results and decisions', newpage=True)
devrows=[]
for key,label in [('dependency_cut','Dependency cut'),('observation_coverage','Observation coverage'),('ready_link','Ready link')]:
    for arm,metrics in D[key]['metrics'].items():
        c=metrics['changed']
        devrows.append([label, 'SP' if arm=='selective_patch' else 'Candidate', f"{c['completed']}/4",f"{c['core_pass']}/4",f"{c['TF']:.2f}",f"{c['PE']:.2f}"])
table(['Study','Arm','Normal','Core','TF','PE'],devrows,[1.9,1.1,.9,.9,1,1.1])
para('Each study independently evaluates the same four original changed conditions and one retention condition per arm. Results are displayed together for interpretation, not pooled as a larger independent sample. Core means every predeclared substantive product property passes; unknown or missing evidence is not a pass. Normal completion and core quality remain separate outcomes. [3, 5, 6]')
para('Dependency cut failed both strict-gain criteria. Observation coverage improved normal completion from 2/4 to 3/4 but tied core quality at 1/4; retention TF fell from 10 to 9.8. Ready link tied completion at 1/4 and reduced TF. Its two core passes were on task 133 with identical knowledge in both arms, so they do not establish an adaptation effect. Under a stricter intermediate-resource-bound interpretation of one answer, candidate core becomes 1/4; the rejection decision is unchanged.')
heading('Why local savings did not establish success', 2)
para('In ready_link Late, the candidate used 33 calls for 30 records, including 22 inline dependency writes; SP used 74 calls for 53 records and 18 later link updates. Both reached 12 rounds with an empty final delivery. The 41-call difference comprises 23 fewer creates and 18 fewer updates, so it cannot all be attributed to scheduling. Candidate Middle stopped after one list_projects call; the next response used its entire 4096-token allowance and ended with length. This proves truncation, not its root cause.')
para('The task-free native suite checked 18 equivalent end states, six invalid-identifier controls and 232 calls. Ready link reduced theoretical waves on two of three generic graph patterns. However, post hoc reconstruction of the three saved original project graphs gave six waves for both global deferral and ready release. That analysis assumes the whole final graph is known in advance and ignores planning and token packing. It weakens transfer of the canary advantage to these observed plans; it does not prove how the actor would behave under an executable scheduler.')
para('Decision: close these specific versions without validation or additional sampling. The open competing explanations concern planning granularity, binding time, adoption of the knowledge rule and output-budget consumption. None is resolved simply by adding another scheduling sentence.')

heading('Failure analysis and causal limits', newpage=True)
heading('Knowledge adaptation', 2)
para('Course task133-late-no_update-r0 made four initial calls without the newly required allow_variables parameter and was rejected. It then repaired the calls from runtime feedback and completed after 38 tool calls, with TF 9.8 and PE 7.2. The paired SP trajectory supplied allow_variables in three accepted validate_syntax calls, used four tool calls overall and received TF 10 and PE 7. This directly supports stale-parameter failure and successful schema adaptation, while final-score causality remains limited by one run. It is a No Update failure, not a demonstrated SP under-update. [1]')
heading('Execution and budget', 2)
para('Repeated round exhaustion with incomplete handoff is a high-impact bottleneck in task 283. Native call validity and lower call count do not guarantee final delivery. Early task 133 also truncates under identical knowledge. Finish metadata establishes the stopping condition; it cannot by itself distinguish excessive planning, response length, poor tool selection or prompt-induced behavior. These are intervention hypotheses, not established causes.')
heading('Product generation', 2)
para('Saved state and final claims require separate checking. In ready_link, a substantial saved project can coexist with an empty final answer. In the dependency-factorial diagnostic, all four SP chain cases saved correct state but exhausted rounds; the candidate completed all four yet passed all product properties in only two. One candidate omitted a dependency and another changed a project description while claiming an extra tag. Completion gains alone therefore did not establish reliable quality gains. Synthetic outcomes remain separate from original benchmark success. [7]')
heading('Environment and data', 2)
para('A missing upstream method and an agent-generated empty argument object are different failures. The course archive records review_workspace_health(includeMemories=true) failing because listMemories is absent, alongside two rejected empty create_task calls. Those observations do not demonstrate damage to unrelated knowledge. Task 235 returns chart specifications; hosted rendering was not tested. Missing original input for task 377 is excluded as unavailable, not scored as a strategy failure.')
heading('Evaluation uncertainty and over update', 2)
para('The six-run chart rollback diagnostic gave both arms TF/PE 10 and one map call per run; it did not reproduce the suspected rewrite harm. Offline review nevertheless found an incorrect annual total in one rewritten answer and an omitted map-specification unit in one rollback answer. These remain product defects, not proof of a causal over-update effect. Judge observation truncation also hides some retrieved facts in the separate daily cohort. Original scores are retained. Product reviews were performed by the same coordinator before score disclosure in recent studies, not by an independent human or under strict method blinding. [1, 2]')

heading('Additional recovery evidence and cost', newpage=True)
dailyrows=[]
for name in ('no_update','full_rewrite','selective_patch','budget_feedback'):
    a=D['daily']['summary'][name]
    dailyrows.append([labels.get(name,'Budget feedback'),f"{a['completed']}/3",f"{a['TF']:.3f}",f"{a['PE']:.3f}",f"{a['ECS_population']:.3f}"])
table(['Task 90 method','Normal','TF','PE','ECS pop'],dailyrows,[2.3,1.1,1.1,1.1,1.3])
para('In this separate 12-run exposed development cohort, No Update Late used an obsolete tool twice and failed to retrieve the current daily problem. Updated methods recovered the content through daily=true. All methods nevertheless completed all three stages, so this supports content recovery over NU, not a completion advantage over SP. Budget feedback also mislabeled setcode 221 as a card password in one answer; the actual card ID was 89631139. Core retrieval and additional unsupported assertions are distinguished. [2]')
costs=[]
course_known=Decimal(str(D['course_cost']['known_execution_usd']))+Decimal(str(D['course_cost']['update_usd']))
costs.append(['Course main 27',f'{course_known:.6f}','1','Excludes preflight and separate diagnostics'])
costs.append(['Daily migration 12',f"{Decimal(D['daily']['known_usd']):.6f}",'0','Includes recorded preflight and updater'])
for key,label in [('dependency_cut','Dependency cut 10'),('observation_coverage','Observation coverage 10'),('ready_link','Ready link 10')]:
    a=D[key];costs.append([label,f"{Decimal(a['known_usd']):.6f}",str(a['unknown_cost_items']),f"{a['api_requests']} settled model requests"])
table(['Cohort','Known USD','Unknown','Accounting scope'],costs,[1.85,1,0.8,3.25])
para('Amounts are provider-reported request charges, not an independently exported invoice. They are selected cohort totals, not the full research cost. Earlier failures, preflights and diagnostics remain in their original ledgers. The separate dependency-factorial study has one unresolved timeout without a generation ID; the user-approved A1 exception allowed its completion without treating that request as free. This is distinct from the older course connection-failure charge. [1, 7]')
para('The current-key endpoint reported usage USD 9.599346951 of a USD 10 limit at 11:25:10 UTC on 1 November 2026. That is a credential-level aggregate, not a project-total or individual-request invoice. A backup key is configured but has not been activated. This report build makes no actor, updater, judge or native-tool calls and adds no experiment model cost.')

heading('Reproduction and remaining requirements', newpage=True)
para('The companion REPRODUCE.md is the local entry point. It indexes the pinned inputs, immutable raw archives, historical commands and offline verifiers. source-manifest.json records SHA256 digests of the synthesis inputs; metrics.json contains the exact unrounded data used for the tables. Rebuilding this document does not rerun any experiment. The report deliberately preserves separate source cohorts and their original scores.')
para('MCPEvol-Bench is pinned to commit 888c779a0fe735f612ca62bdd1fdd7c9e6bf8701 and dataset revision 162e3ffbea1717ac8a20fe9b26465e29117229e4. The course raw archive hash is e95e15694abe9a12e37c813f81e6e0fb0b5ccd00c2003f2a25a36a092c8001c9. The ready_link model freeze is a95ad2d, with product reviews frozen at 89cfd3d before score disclosure. Its verifier covers 420 raw files, 188 frozen source files and 50 original judge slots. Historical replay uses its archived implementation, rather than assuming current source still matches every old freeze. [1, 3]')
table(['Requirement','Evidence status'],[
 ['NU and FR course baselines; TF, PE, ECS; cost','Present for 27 main runs; limited subset and one repeat disclosed'],
 ['Changed-task recovery and unchanged retention','Measured; limited recovery evidence, no general superiority claim'],
 ['Causal SP under-update and over-update examples','Not established; related trajectories and failed diagnostic retained'],
 ['Strict original development dual improvement','Not achieved by the reported candidates'],
 ['Two independent validation batches','Not started because development gates failed'],
 ['Report and reproducibility entry','Produced locally; no external submission claimed'],
 ['Presentation work','Ended per user; no further slides or speaker scripts requested'],
],[2.85,4.05])
para('If a future candidate passes development, the recorded validation design requires two fresh batches of 30 trajectories each: three repeats per condition and arm, empty isolated task workspaces, no shared actor memory and separate ledgers. The same knowledge must remain byte-identical across batches. Each batch separately must pass strict normal-completion and core-quality gains on the whole changed subset and the project subset, with TF and retention nondecrease. Independence means fresh executions on already exposed tasks, not unseen-task generalization or proven statistical independence of the provider.')
para('No new candidate is admitted by this synthesis. The report closes a delivery gap, not the research gap. A next experiment needs a distinct, lawful knowledge decision and a falsifiable prediction that separates the remaining explanations. A failed version may be closed without declaring the entire mechanism family ineffective; a new version need not already have proved success before a fair test.')

heading('Evidence and references', newpage=True)
refs=[
 ('1','Course baseline','results/evidence/course-v1.3-20261031','summary.json, interpretation.json, cost-audit.json, metrics-audit.json, plan.json and reproduction.json. Contains the named trajectory IDs and the separate rollback diagnostic.'),
 ('2','Daily migration','results/evidence/daily-migration-pilot-20261031','trial-verification.json, quality-review.json and reproduction.json. Twelve exposed original-task runs; live public content.'),
 ('3','Ready link','results/evidence/ready-link-20261101','decision.json, interpretation.json, research-decision.json and reproduction.txt; protocol experiments/ready-link-v1.json.'),
 ('4','Semantic claim repair','results/evidence/semantic-claim-repair-20261101','decision.json and interpretation.json; source src/pe6203/semantic_contract_maintenance.py.'),
 ('5','Dependency cut','results/evidence/dependency-cut-20261101','decision.json and interpretation.json; original development separated from the later factorial diagnostic.'),
 ('6','Observation knowledge','results/evidence/observation-coverage-20261101','decision.json; controlled follow-up in results/evidence/observation-selection-20261101.'),
 ('7','Dependency factorial','results/evidence/dependency-factorial-20261101','decision.json; synthetic mechanism diagnostic and unresolved-charge accounting.'),
 ('8','Mechanism literature','results/evidence/method-learning-20261101/method-review.json','ACE 2510.04618v1, ace-agent/ace SHA 82709de050e1db6e6ef2f07bcb0393560b94992a. A-MEM 2502.12110v1, WujiangXu/AgenticMemory SHA f9a173dec325d84fcc97e7828775c7b241c33466. Reflexion, NeurIPS 2023, noahshinn/reflexion SHA 218cf0ef1df84b05ce379dd4a8e47f17766733a0. Exact functions and implementation limits are recorded in this file.'),
 ('9','Selective updater implementation','src/pe6203/selective.py','Metadata diff, explicit reference index, impact expansion and adaptation validation. Full Rewrite implementation is in src/pe6203/baselines.py; optional updater availability is not evidence it was used.'),
 ('10','Course authority','PE6203 Group Project 4 brief','Tool Harness Adaptation under Environment Change. Supplied DOCX SHA256 6a74fda17b7a8b9280151e55ec46b46a70d1d717e4be24c5f9c38d134611af0d. User research requirements and later presentation-scope update take precedence for this work.'),
]
for number,title,path,detail in refs:
    para(f'[{number}] {title}. {path}. {detail}')
para('LLMCompiler: https://arxiv.org/html/2312.04511v3 ; https://github.com/SqueezeAILab/LLMCompiler/tree/a00c9d35507507da70e8c637eee64efc8c1857ae . Borrowed ready-prerequisite logic only; native equivalence and agent outcomes are reported separately.')

OUT.mkdir(exist_ok=True)
doc.save(OUT / 'PE6203 Research Report.docx')
(OUT / 'report.md').write_text('\n'.join(md))
metrics={'course_main':D['course']['main_results'],'course_ecs':D['course']['matched_ecs'],'course_update_cost':D['course']['update_cost_by_strategy'],'daily':D['daily']['summary'],'development':{k:D[k]['metrics'] for k in ('dependency_cut','observation_coverage','ready_link')},'selected_cohort_costs':costs,'goal_achieved':False,'formal_validation_started':False}
(OUT / 'metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+'\n')
manifest={'source_commit':'d5d8a89','purpose':'Synthesis inputs only; not a new experiment freeze','sources':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES.values()},'model_calls':0}
(OUT / 'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'docx':str(OUT/'PE6203 Research Report.docx'),'source_files':len(SOURCES),'tables':len(doc.tables),'model_calls':0}))

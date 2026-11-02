"""Source/native certificate and unchanged evaluation protocol; no model calls."""
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from pe6203.selective import canonical

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def load(p): return json.loads((ROOT/p).read_text())
def save(p,x): (ROOT/p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sha(p): return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()

SUFFIX='''Verified project construction dataflow: conditional inline dependencies and ready-link release.
Applicability: required work records, their full contents, hierarchy and intended acyclic dependencies have been planned. This is symbolic operation knowledge, not executable native arguments.
R(record): create_task requires the project ID and, for a child, its existing parent ID. Preserve all intended fields. When every intended dependency ID was returned before the current assistant response, include the COMPLETE dependsOn list directly in R. No later link rewrite is needed for that record. When some dependency ID is still unavailable, temporarily omit dependsOn and keep that record's complete intended dependency set pending. Do not serialize otherwise-ready sibling creation just for a cross-task ID.
D(pending record): as soon as this record's ID AND all its intended dependency IDs have been returned, update_task(id, dependsOn=COMPLETE intended set). Omitted fields and parent remain unchanged. A ready D can share an assistant response with other R operations whose own project/parent IDs are already known; there is no global requirement to finish all record creation before linking. Do not rewrite dependencies for records already created with their complete list.
Dataflow: P->R; parent R->child R; referenced R receipts->inline dependencies or D; every required R and pending D->verification->final delivery. Calls within one assistant response cannot use IDs returned by another call in that response. Never put symbolic labels or invented IDs in native arguments, and never treat a partial dependency list as the complete intended set.
Completion: unresolved pending links are unfinished work. Use successful mutation receipts and list_tasks to check real records and links, then provide an accurate final handoff. Preserve required scope and all fields; do not remove work or lower estimates/complexity to fit the schedule. Failed linking is not success. Native text trimming still applies.
Limits: generic native tests preserve final state, not intermediate completeness. Conditional inline writes avoid some extra updates; ready release sometimes removes a barrier, but graphs can still require a final link wave. No universal call or round saving is guaranteed. This knowledge does not change the executor or its budget.'''

def main():
    native=load('results/evidence/ready-link-20261101/native-decision.json');assert native['admitted']
    observations=[]; certificates={}
    for old in load('experiments/dependency-cut-feedback-v1.json')['observations']:
        stage=old['stage']; cert=dict(kind='ready_link_v1',stage=stage,changed_record=old['result']['changed_record'],
            contracts=old['result']['contracts'],description_suffix=SUFFIX,
            native_spec_sha256=sha('experiments/ready-link-native-v1.json'),
            native_result_sha256=sha('results/evidence/ready-link-20261101/native-results.json'),
            native_limits='3 generic eight-node graphs,2 stages,3 routes,18 exact final states,6 unchanged-state missing-ID negatives. Serial native execution; static wave counts only. No benchmark content.',
            source_sha256=sha('results/evidence/dependency-cut-20261101/sources/llmcompiler/src/llm_compiler/task_fetching_unit.py'))
        # Bind certificate contracts to the newly observed full native catalogs.
        cats=load('tests/fixtures/dependency-cut-catalogs.json')
        fresh={t['name']:t for t in load(f'results/evidence/ready-link-20261101/native/{stage}-903001-direct/catalog.json')['tools']}
        for t in cats[stage]['tools']:
            if t['tool_id'] in cert['contracts']:
                assert hashlib.sha256(canonical(t).encode()).hexdigest()==cert['contracts'][t['tool_id']]
                observed=fresh[t['name']]
                assert t['parameters']==observed['inputSchema'] and t['description']==observed['description']
                assert t.get('output_schema')==observed.get('outputSchema')
        certificates[stage]=hashlib.sha256(canonical(cert).encode()).hexdigest()
        observations.append(dict(stage=stage,server=old['server'],tool=old['tool'],result=cert))
    save('experiments/ready-link-feedback-v1.json',dict(observations=observations))
    for suffix in ['dev','updater','validation-1','validation-2']:
        p=f'configs/observation-coverage-{suffix}-v1.json'
        x=load(p);x['spend_guard']['ledger']=x['spend_guard']['ledger'].replace('observation-coverage','ready-link')
        save(p.replace('observation-coverage','ready-link'),x)
    protocol=json.loads(json.dumps(load('experiments/observation-coverage-v1.json')).replace('observation-coverage','ready-link').replace('observation_coverage','ready_link'))
    protocol['generation']=dict(rule='Original SP plus exact task-free source/native certificate compiled into actually changed create_project description only. Deterministic update,0 updater calls.',
        representation='R inline-if-all-refs-ready; otherwise pending D released when own+all dependency IDs exist. Pending D can interleave with ready R. No executor change.',
        native='232 native calls,18 catalogs,18 complete state equivalences,6 invalid updates preserving bytes.',
        limits='No actor-positive training required. Native equivalence does not prove adoption, actual saved rounds, correct planning or final summary. 133/235 byte-identical SP.')
    protocol['mechanism']='Replace universal dependency deferral and global create-then-link barrier with conditional inline dependencies and ready-release pending links. Different native write count and dependency graph; not a wording-only revision. Still static tool knowledge, no planner/executor, no runtime repair.'
    protocol['literature']=load('experiments/ready-link-native-v1.json')['literature']
    protocol['pre_model_dependencies']=['18 native equivalences and6 negativecontrols','targeted compiler and regression tests','exact sources/config/question/catalog/knowledge hashes','10opaque reviewIDs and unchanged original rubrics','dedicated null-cap ledger','133/235 exactSP;283 onlychanged producerdescription']
    protocol['cost_estimate_usd']['basis']='Priororiginal two-arm studies; estimatesnotcaps. Native232calls+18catalog/0models. Separate dev and eachvalidation ledger.'
    protocol['review_integration']='Completed independent strategy review reused; take mechanism-level novelty, source/probe semantic validation, and no universal positive-episode gate. Do not start another review loop. Details in research-decision.json.'
    protocol['mechanism_measurement']='Descriptive uptake after product review: actual dependsOn on creation, subsequent dependency updates, update waves interleaved with later creates, normal completion, all properties. Existing calls do not establish that later intended links were already planned; no hidden reasoning inspected. Low uptake leaves planner/adoption explanation open; clear uptake without gains weakens sufficient-scheduling hypothesis. Full fixed gates unchanged.'
    save('experiments/ready-link-v1.json',protocol)
    authority=load('results/evidence/semantic-contract-maintenance-20261101/review-decision.json')['constraints']
    save('results/evidence/ready-link-20261101/research-decision.json',dict(
        question='Can conditional inline links plus removal of a global create/link barrier improve full original completion and artifact correctness under the same actor budget?',
        authority_sources=authority,
        evidence=dict(facts=['Prior dependency_cut literally rewrote every dependency-bearing record after all creation. Original283 candidate23 such records each,3 supplemental-link rounds,12roundemptyfinals.','Prior factorial all4 SP chain stores correct but no finaldelivery; candidate4/4normal,2/4core.','Latest observation-selection normal8/8both, no fixed-representation support; stop that line.'],
            observations=['Prior original283 candidate4/5 records had all final dependency references available before creation; this bounds avoidable writes only, not what actor knew/planned then.','Native new route preserves all18 states and removes6/3/2 writes relativeolddefer on threegraphs. Two static wave reductions,one tie.'],
            hypotheses=['Some unnecessary link writes and barriers consume opportunities for finalhandoff.','Planning burden, self-chosen scope, packing and finalclaim correctness may dominate even with source-correct scheduling.']),
        bottlenecks_ranked=[dict(rank=1,kind='execution_and_artifact',evidence='Repeated original283 12roundemptydelivery; controlled chain correctstore/emptyfinal; high product impact; source-grounded dependency scheduling is legal intervention.'),dict(rank=2,kind='artifact_semantics',evidence='Missinglinks/unsupportedclaims occur despite normalfinish; current representation only protects intendedlinks, no evidence it repairs broader generatedcode/plan scope.')],
        five_classes=dict(knowledge='Source-correct operation graph may be unused or misapplied; cause unproven.',execution='max_rounds proves truncation only; cost/wave hypothesis now has a defined native intervention.',artifact='All required fields/links and truthful final delivery stay required; correct native state alone insufficient.',environment='Original133/283/235 inputs complete,existing native sources hashed;377closed.',evaluation='Same coordinator non-strict methodblinding,small devsample,officialhighTFnotcorrectness; strict replicationgate unchanged.'),
        candidates=[dict(id='ready_link',priority=1,selected=True,change='conditionalinline+ready-release',input='task-free source/contracts/nativegraphs',falsification='Native mismatch blocks; any original strict gate failure closes thisversion. Uptake+no gain weakens scheduling sufficiency; absentuptake leaves adoption rival.',minimum='18nativepaths then10originaldevcells; onlyifpass2fresh30cellvalidationblocks.',cost='Native$0; devestimate0.10–0.40USD,notcap.'),dict(id='global_claim_checker',priority=2,selected=False,reason='A separate actor-time validation loop violates frozen execution. Static semantic claim rules already tested in contractmaintenance/project_state/observationcoverage; no new source-grounded decision identified. Do not disguise another prompt as distinct candidate.')],
        deduplication=dict(dependency_cut='Old universal two-phase R then D for everydependency; newonlyunresolvedD andinterleaving.',budget_workflow='Earlier generic groupknowninputs advice has no conditional write selection or pendinglink release model.',project_state='Existing notes address malformedlegacyrows, inflatedhierarchycounts andcomplexitywarnings; no conditional inline/release rule.',observation_coverage='Observationprojection/freshnessmodel, no writegraph change.'),
        literature=protocol['literature'],review_integration=protocol['review_integration'],
        scope='Changedcreate_project is projectIDproducer/entrypoint; consumer contract hasheschecked, otherfields/recordsprotected. No benchmarkquestions/answers/scoredtraces used in certificate. Originaltaskfamilies exposed; validationfresh executions notunseentasks.',
        admission='Legal,mechanisticallydistinct,source-grounded,dependenciescomplete,falsifiable,fair; doesnotrequirepreexisting actor efficacy. Nativeproofnotcausal actorproof.',
        course='Finalintegratedreport/repro/presentationstillpending; native/devdo not satisfy fullGoal.',goal_complete=False))
    print(json.dumps(certificates))

if __name__=='__main__': main()

"""Synthetic updater calibration only; no original benchmark or actor execution."""
import ast
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import random
import sys
from time import perf_counter
from integration.baselines import _request_completion
from pe6203.description_factor import compile_factor, inventory
from pe6203.experiment import verify_files
from pe6203.request_retry import request_sync

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
ORIGINAL=ROOT/'results/evidence/description-factor-20261101/generate.py'
tree=ast.parse(ORIGINAL.read_text())
PROMPT=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PROMPT' for t in n.targets))
load=lambda p:json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def prepare():
    assert not (HERE/'plan.json').exists()
    text=('The body is a UTF-8 string. It is stored verbatim without trimming leading or trailing whitespace. '
          'Line breaks are preserved in their original order. Empty strings are rejected before storage. '
          'Tabs remain tabs and are not expanded to spaces. Punctuation and letter case are preserved. '
          'No Markdown rendering, template expansion, arithmetic evaluation or network request is performed on this text. '
          'A successful write records the supplied body once and returns the identifier of that new record. '
          'A write does not overwrite any earlier record. The caller must not infer that text content has been fact checked merely because it was stored successfully.')
    assert len(text)>=500
    anchor='This operation writes into the catalogue named Amber. The Amber catalogue is separate from the Indigo catalogue.'
    base={'name':'write_record','server_id':'synthetic-coverage','tool_id':'synthetic-coverage::write_record','description':'Write a record.','parameters':{'type':'object','properties':{'body':{'type':'string','description':'The record body.'}},'required':['body'],'additionalProperties':False},'output_schema':None,'usage_rules':[],'routing':{'server_id':'synthetic-coverage','tool_name':'write_record'},'version':'early'}
    cases=[];expected={};oracles={}
    definitions=[('DF-C01','exact_duplicate',[anchor,text,text],False,True),
                 ('DF-C02','unique_qualifiers',[anchor,text+' Also reject bodies containing the literal marker cedar.',text+' Also reject bodies containing the literal marker maple.'],False,False),
                 ('DF-C03','schema_duplicate',[anchor,text],True,True),
                 ('DF-C04','schema_near_miss',[anchor,text+' Also reject bodies containing the literal marker cedar.'],True,False)]
    for case_id,category,lines,in_schema,positive in definitions:
        old={'schema_version':'1.0','benchmark_commit':'synthetic-description-control-v1','version':'early','source':'synthetic metadata diagnostic; no native server','tools':[deepcopy(base)]}
        target=deepcopy(old);target['version']='late';tool=target['tools'][0];tool['version']='late';tool['description']='\n'.join(lines)
        if in_schema:tool['parameters']['properties']['body']['description']=text
        input_value={'stage':'late','tools':inventory(old,target)}
        cases.append({'id':case_id,'old':old,'target':target,'input':input_value})
        expected[case_id]={'split':'diagnostic_exploration','category':category,'positive':positive,'unique_lines':[0] if positive else list(range(len(lines))),'redundant_sets':[[1,2]] if category=='exact_duplicate' else [[1]] if positive else [],'minimum_removed_characters':500 if positive else 0,'forbidden':'Delete unique clauses, change schemas/toolset/other fields, or invent replacement text','rationale':'Known constructed identity/coverage with near-miss unique qualifiers; not native behavior or benchmark correctness','provenance':'Deterministic synthetic fixture from study.py; these clauses are stipulated documentation, not claims about a real tool.'}
        if category=='exact_duplicate':
            oracle={'deletions':[{'tool_id':tool['tool_id'],'lines':[2],'coverage':[{'kind':'description','lines':[1],'quote':text}],'reason':'Exact duplicate survives.'}]}
        elif category=='schema_duplicate':
            oracle={'deletions':[{'tool_id':tool['tool_id'],'lines':[1],'coverage':[{'kind':'parameters','path':['properties','body','description'],'quote':text}],'reason':'Exact schema description survives.'}]}
        else:oracle={'deletions':[]}
        knowledge,log=compile_factor(old,target,oracle)
        removed=len(tool['description'])-len(knowledge['tools'][0]['description'])
        assert (removed>=500 if positive else removed==0)
        oracles[case_id]={'proposal':oracle,'characters_removed':removed,'structural_pass':True}
    save(HERE/'inputs.json',cases);save(HERE/'expected.json',expected);save(HERE/'oracle-check.json',oracles)
    settings=load(ROOT/'configs/description-factor-updater-v1.json')
    settings['spend_guard']['ledger']='results/raw/description-factor-control-costs-20261101/spend-ledger.json'
    assert not (ROOT/settings['spend_guard']['ledger']).exists()
    save(HERE/'settings.json',settings)
    schedule=[{'case_id':c['id'],'repeat':r} for r in range(2) for c in cases]
    random.Random(704291).shuffle(schedule)
    for i,row in enumerate(schedule,1):row['run_id']=f'control-{i:02d}'
    plan={'id':'description-factor-control-v1','kind':'controlled_synthetic_updater_diagnostic','question':'Does the unchanged coverage-deletion updater act on unambiguous redundancies and preserve unique qualifiers?','pipeline':'Exact original PROMPT and compiler; same model/provider/decoding/updater budget; independentledger','schedule':schedule,'repeats_per_case':2,'input_boundary':'Only input object supplied to model. No labels, oracle, task questions, benchmark answers or scored trajectories. Every call has fresh messages.','evaluation':'Known identity controls: both positive conditions remove>=500chars without unique-line loss; both negative conditions delete no unique lines. Compile citations structurally and check stipulated semantic properties. Report all8 individually.','diagnostic_rule':'All4positive calls and4negative controls pass => generator can handle elementary coverage; original empty outputs do not prove universally inactive interface. Any positive abstention => record sensitivity failure; any unique deletion=>unsafe proposal. Partial successes reported without claiming reliability. No result promotes any original candidate.','failure_handling':'Existing max1 structural repair andmax1transportretry; preserveallattempts. No semanticrepair or resampling. Newunknown stops through existingledger; oldA1 exception excluded.','fairness':'No actor/native/judge change or call; originalbenchmark remainsuntestedbythisdiagnostic. Syntheticcases cannotbe originaldevelopment orvalidation.','cost':'EstimatedUSD0.005–0.05,notcap. No new totalbudget.','reviewer':'Mainonly, deterministic constructedoracle ratherthanLLMjudge; noadditionalagent.','stop':'Exactly8scheduledcases unlessinfrastructure/unknowncharge blocks. Never rerun successful/failed completedcases.'}
    save(HERE/'plan.json',plan)
    paths=['results/evidence/description-factor-control-20261101/'+x for x in ['study.py','inputs.json','expected.json','oracle-check.json','settings.json','plan.json']]+['results/evidence/description-factor-20261101/generate.py','src/pe6203/description_factor.py','src/pe6203/selective.py','src/pe6203/request_retry.py','src/pe6203/spend_guard.py','integration/baselines.py']
    save(HERE/'freeze.json',{'files':{p:sha(ROOT/p) for p in paths},'model_calls':0})
    print(json.dumps({'cases':4,'scheduled_requests':8,'oracle_checks':4,'source_files':len(paths),'model_calls':0}))

def run():
    verify_files(ROOT,load(HERE/'freeze.json')['files'])
    cases={c['id']:c for c in load(HERE/'inputs.json')}
    settings=load(HERE/'settings.json');settings['allow_metadata_api']=True
    for item in load(HERE/'plan.json')['schedule']:
        path=HERE/(item['run_id']+'.json')
        if path.exists():raise ValueError('Scheduled run already attempted; no reruns')
        case=cases[item['case_id']]
        messages=[{'role':'system','content':PROMPT},{'role':'user','content':json.dumps(case['input'],ensure_ascii=False)}]
        audit={**item,'attempts':[],'status':'started'};started=perf_counter();save(path,audit)
        try:
            for attempt in range(2):
                rec={'attempt':attempt+1,'request':deepcopy(messages)};audit['attempts'].append(rec);save(path,audit)
                def on_retry(event):audit.setdefault('transport_retries',[]).append(event);save(path,audit)
                response=request_sync(lambda:_request_completion(messages,settings),settings['request_retry'],on_retry)
                rec['response']=response;save(path,audit)
                try:
                    choice=response['choices'][0]
                    if choice['finish_reason']!='stop':raise ValueError('Incomplete generation')
                    proposal=json.loads(choice['message']['content'])
                    knowledge,log=compile_factor(case['old'],case['target'],proposal)
                except (ValueError,KeyError,TypeError,IndexError) as exc:
                    rec['validation_error']=str(exc);save(path,audit)
                    if attempt==1:audit['status']='structural_rejection';break
                    messages += [{'role':'assistant','content':response['choices'][0]['message'].get('content') or '{}'}, {'role':'user','content':'Repair structural JSON/indices/quotes only; do not broaden deletions. Error: '+str(exc)}]
                    continue
                audit.update(status='structurally_valid',proposal=proposal,knowledge=knowledge,deletion_log=log);break
        finally:audit['seconds']=perf_counter()-started;save(path,audit)
        print(json.dumps({'run_id':item['run_id'],'status':audit['status'],'attempts':len(audit['attempts'])}),flush=True)

def evaluate():
    verify_files(ROOT,load(HERE/'freeze.json')['files'])
    cases={c['id']:c for c in load(HERE/'inputs.json')};expected=load(HERE/'expected.json');rows=[];cost=Decimal('0');ids=[]
    for item in load(HERE/'plan.json')['schedule']:
        a=load(HERE/(item['run_id']+'.json'));case=cases[item['case_id']];e=expected[item['case_id']]
        assert a['attempts'][0]['request']==[{'role':'system','content':PROMPT},{'role':'user','content':json.dumps(case['input'],ensure_ascii=False)}]
        for rec in a['attempts']:
            response=rec['response'];assert response['provider']=='DigitalOcean'
            cost+=Decimal(str(response['usage']['cost']));ids.append(response['id'])
        deleted=set();removed=0;valid=a['status']=='structurally_valid'
        if valid:
            k,log=compile_factor(case['old'],case['target'],a['proposal']);assert k==a['knowledge']
            deleted={n for r in a['proposal']['deletions'] for n in r['lines']}
            removed=len(case['target']['tools'][0]['description'])-len(k['tools'][0]['description'])
        retained=valid and not (deleted & set(e['unique_lines']))
        # In exact duplicate, at least one identical occurrence must survive.
        if e['category']=='exact_duplicate':retained=retained and not {1,2}.issubset(deleted)
        success=retained and (removed>=500 if e['positive'] else removed==0)
        rows.append({**item,'category':e['category'],'positive':e['positive'],'status':a['status'],'deleted_lines':sorted(deleted),'characters_removed':removed,'unique_information_retained':retained,'control_pass':success,'attempts':len(a['attempts'])})
    ledger=load(ROOT/load(HERE/'settings.json')['spend_guard']['ledger'])
    assert len(ids)==len(set(ids))==len(ledger['requests'])
    assert set(ids)=={r['response_id'] for r in ledger['requests']}
    assert cost==Decimal(ledger['known_usd']) and Decimal(ledger['unknown_reserved_usd'])==0 and not ledger['blocked']
    positives=[r for r in rows if r['positive']];negatives=[r for r in rows if not r['positive']]
    decision={'rows':rows,'positive_passes':sum(r['control_pass'] for r in positives),'positive_n':len(positives),'negative_passes':sum(r['control_pass'] for r in negatives),'negative_n':len(negatives),'api_requests':len(ids),'known_usd':str(cost),'unknown_cost_items':0,'actor_calls':0,'native_calls':0,'judge_calls':0,'original_candidate_promoted':False,'goal_complete':False,'rule':'All4+4 required for reliable elementary-control support; partialoutcomes disclosed. No originalbenchmarkperformanceinference.'}
    save(HERE/'decision.json',decision);save(HERE/'updater-ledger.json',ledger)
    print(json.dumps({k:v for k,v in decision.items() if k!='rows'}))

if __name__=='__main__':{'prepare':prepare,'run':run,'evaluate':evaluate}[sys.argv[1]]()

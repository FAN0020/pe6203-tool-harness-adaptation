import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {Presentation,PresentationFile} from '@oai/artifact-tool';
const root=path.resolve('submission');
const skill='/Users/fanysmacpro/.codex/plugins/cache/openai-primary-runtime/presentations/26.1026.10807/skills/presentations';
const runtime='/Users/fanysmacpro/.cache/codex-runtimes/codex-primary-runtime/dependencies';
const data=JSON.parse(await fs.readFile(path.join(root,'evidence/recomputed/metrics.json'),'utf8'));
const names={no_update:'No Update',full_rewrite:'Full Rewrite',selective_patch:'Selective Patch'};
const p=Presentation.create({slideSize:{width:1280,height:720}});
const dark='#245071',ink='#172333',muted='#53677D',blue='#215F99',amber='#976317';
const durations=[55,50,65,35,55,40,60,75,35,40];
const bg=new Uint8Array(await fs.readFile(path.join(root,'.build/image4.jpg')));
const notes=[];
function text(slide,s,x,y,w,h,size=28,bold=false,color=ink){const b=slide.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});b.text=s;b.text.style={typeface:'Arial',fontSize:size,bold,color};return b;}
function slide(title,note,appendix=false){const s=p.slides.add();s.background.fill='#FFFFFF';s.images.add({blob:bg,contentType:'image/jpeg',alt:'Original team slide background',fit:'cover',position:{left:0,top:0,width:1280,height:720}});text(s,title,64,44,1152,90,44,true,dark);const i=p.slides.items.length;text(s,`PE6203 Group Project 4    ${appendix?'Q&A appendix':(i+3)+' / 13'}    Archived course-v1.3`,64,674,1150,24,16,false,muted);note=note.replace(/^\d+ seconds\./,durations[i-1]+' seconds.');s.speakerNotes.text=note+'\n\nSources: PE6203 Project4 brief §§3–4; MCPEvol-Bench arXiv:2607.14642v1 §6.1 / Appendix D.1; submission/evidence/recomputed/metrics.json; failure-cases.json. No new experiments for this deck.';notes.push({slide:i+3,title,seconds:appendix?null:durations[i-1],text:note});return s;}
function table(s,headers,rows,x=64,y=170,w=1152,h=300,widths=null,size=25){const values=[headers,...rows];const t=s.tables.add({rows:values.length,columns:headers.length,left:x,top:y,width:w,height:h,values,...(widths?{columnWidths:widths}:{})});t.borders.assign({fill:'#CAD6E2',width:1,style:'solid'});for(let r=0;r<values.length;r++){t.rows[r].height=h/values.length;for(let c=0;c<headers.length;c++){const q=t.getCell(r,c);q.fill=r===0?'#E8EFF6':'#FFFFFF';q.text.style={typeface:'Arial',fontSize:size,color:ink,bold:r===0};}}return t;}
function box(s,label,x,y,w,h){const b=s.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:h},fill:'#F0F5FA',line:{fill:'#6991B8',width:1.5}});b.text=label;b.text.style={typeface:'Arial',fontSize:25,color:dark,bold:true};return b;}
function arrow(s,a,b,from,to){s.shapes.connect(a,b,{kind:'elbow',fromSide:from,toSide:to,line:{fill:blue,width:3},tail:{type:'triangle'}}).bringToFront();}
{
const s=slide('Selective Patch architecture','80 seconds. The harness contains names, schemas, descriptions, rules, output schemas and routing. We compare Early knowledge with target metadata. A deterministic diff detects additions, removals and field changes. An explicit reference index expands affected knowledge through one-hop dependencies. The implementation copies authoritative target fields for affected records and preserves unaffected knowledge. It retains valid usage rules instead of silently erasing them. Validation checks schemas, routing and preservation. The evaluated method makes no model calls during updating. The same agent then selects tools and arguments from the frozen snapshot and interacts with real MCP servers. Raw traces and five judge ratings are stored. No Update retains K0; Full Rewrite rebuilds target records and regenerates all descriptions using the fixed model. This compares update scope and generation mechanism together, not a pure scope ablation. Early uses K0 for all methods.');
const a=box(s,'Early K0 +\ntarget metadata',64,175,280,130),b=box(s,'Metadata diff +\ndependency scope',500,175,280,130),c=box(s,'Update affected\nrecords',936,175,280,130),d=box(s,'Validate schemas,\nroutes, preservation',936,405,280,130),e=box(s,'Frozen knowledge\nSame agent + MCP',500,405,280,130),f=box(s,'Trace + 5 ratings\nIndependent audit',64,405,280,130);
arrow(s,a,b,'right','left');arrow(s,b,c,'right','left');arrow(s,c,d,'bottom','top');arrow(s,d,e,'left','right');arrow(s,e,f,'left','right');
text(s,'The model chooses tools and arguments in every strategy',64,585,1152,60,28,false,muted);
}
{
const s=slide('Experimental setup and fairness','55 seconds. Our documented subset contains task133 for mathematical syntax and security advice, task283 for project decomposition, and task235 for unchanged sales visualization. The first two represent parameter, description and relevant tool additions; the last measures retention. Three stages and three methods give27 cells, with one execution each. The brief permits one under compute constraints. Every cell receives five judge ratings, which are not five agent executions. We freeze DeepSeek v4.1 Flash through OpenRouter, temperature zero,4096 output tokens,12 rounds and the same judge rubric and recovery policy. Tool additions are optional paths; required renaming and removal are not tested. We make no full-leaderboard or unseen-task-family claim.');
table(s,['Task','Role','Coverage'],[['133','Changed tools','PARAM; relevant TOOL addition'],['283','Changed tools','TOOL + PARAM + DESC'],['235','Unchanged tools','Retention control']],64,160,1152,275,[120,330,702]);
text(s,'3 tasks × 3 stages × 3 strategies × 1 execution = 27',64,470,1140,60,30,true,blue);
text(s,'Fixed DeepSeek v4.1 Flash · temperature 0 · 4096 output tokens\n12 rounds · same tasks, judge protocol and execution budget',64,545,1140,95,26);
}
{
const s=slide('Observed trade-offs across methods','70 seconds. These values were recalculated from immutable raw judge outputs. Each strategy mean equally weights nine task-stage cells. Selective Patch leads PE at9.1111, compared with7.8667 for No Update and8.3556 for Full Rewrite. It does not lead task fulfillment or cross-version ECS. Full Rewrite has the highest TF and ECS in this sample. Normal completion is also lower for Patch: six of nine, versus seven for each baseline. All27 trajectories remain in the score analysis, including five round-exhausted and two truncated executions. Completion is reported separately because a high judge score can coexist with an unfinished agent loop. These are descriptive outcomes on a very small subset. We do not attach a statistical superiority claim or an arbitrary weighted score.');
table(s,['Strategy','TF','PE','ECS pop.','Completed'],data.strategy_means.map(x=>[names[x.method],x.TF.toFixed(4),x.PE.toFixed(4),x.ECS_population.toFixed(4),x.completion.completed+'/9']),64,180,1152,280,[290,190,190,242,240]);
text(s,'Highest PE does not imply highest TF, ECS or completion',64,510,1140,80,31,true,blue);
text(s,'All failures remain included; five ratings measure one trajectory',64,603,1140,45,24,false,muted);
}
{
const s=slide('Verifying the Selective Patch PE mean','40 seconds. The requested9.1111 is correct. For task133, the Early, Middle and Late cell scores are10,8 and7. Task235 has10 in every stage. Task283 has9,9.4 and8.6. The nine values sum to82, so dividing by nine gives9.111111. The report also shows all five raw ratings behind each cell. The independent script uses exact rational arithmetic for the means and never rewrites stored scores.');
table(s,['Task','Early','Middle','Late'],[['133','10','8','7'],['235','10','10','10'],['283','9','9.4','8.6'],['Column sum','29','27.4','25.6']],64,155,1152,340,[330,274,274,274]);
text(s,'82 ÷ 9 = 9.1111',64,545,1150,85,54,true,blue);
}
{
const s=slide('Recovery and retention','60 seconds. On changed tasks133 and283, the Selective Patch mean TF difference against same-stage No Update is zero in Middle and plus0.1 in Late. The gain is small because No Update can learn from runtime error messages and recover, and TF is near its ceiling. A direct mechanism is visible on task133 Late: No Update initially omits mandatory allow_variables and its calls are rejected, while Patch supplies it. On the unchanged chart task235, all strategies retain TF10. Patch has PE10 at every stage. No Update Middle nevertheless repeats map generation and gets PE4.8 despite unchanged knowledge. Thus unchanged knowledge does not ensure identical execution. These results support narrow observations, not broad adaptation or no-regression guarantees.');
table(s,['Measure','Middle','Late'],[['Changed-task Patch ΔTF vs No Update','0.00','+0.10'],['Unchanged-task Patch TF','10.0','10.0'],['Unchanged-task Patch ΔTF vs Early','0.00','0.00']],64,170,1152,300,[650,251,251],24);
text(s,'Call-level evidence: new required parameter is supplied\nTask-level gain is small; No Update can self-correct after errors',64,520,1140,110,28);
}
{
const s=slide('Update cost and unknown billing','45 seconds. Patch uses zero model tokens to update and about1.145 seconds of local computation. Full Rewrite uses177974 tokens,203.508 seconds and about4.9 US cents. No Update is also zero in model tokens and API cost and has no update computation. Therefore Patch is cheaper than Full Rewrite but tied with No Update in API dollars, not uniquely cheapest. The whole main experiment has about0.406919 dollars in known costs including execution, judging, updating and preflight. One failed connection request has unknown usage and charges. We retain that uncertainty rather than treating it as zero.');
table(s,['Strategy','Update tokens','Seconds','API USD'],data.strategy_means.map(x=>[names[x.method],String(x.update_tokens),x.update_seconds.toFixed(3),x.update_usd.toFixed(6)]),64,175,1152,270,[340,280,240,292]);
text(s,'Known main total: $0.406919 + one unknown request charge',64,505,1140,70,30,true,blue);
text(s,'Zero API cost is shared with No Update; local work still has a cost',64,590,1140,55,25,false,muted);
}
{
const s=slide('Under-update: what is actually confirmed?','65 seconds. The strongest stale-knowledge case is task133 Late No Update. The Early schema requires only expression. The Late schema also requires allow_variables. Four initial calls omit it and are rejected. Error feedback prompts the agent to repair its later calls. The final score is TF9.8 and PE7.2 after38 calls. This confirms a local stale-schema failure but is not a Selective Patch under-update. The corresponding Patch knowledge includes the parameter and all three validation calls supply it, with no tool errors. Our corpus screen found no missed metadata field in the original Patch records that had complete comparison data. This does not prove no semantic rule can ever be missed. The strict natural Patch under-update example remains absent.');
table(s,['Task 133 Late','No Update','Selective Patch'],[['Visible required fields','expression','expression + allow_variables'],['Initial parameter errors','4 omitted-parameter rejections','0 tool errors'],['Observed outcome','Completed; TF9.8 / PE7.2','Completed; TF10 / PE7']],64,175,1152,300,[290,431,431],24);
text(s,'Confirmed: stale No Update calls\nNot confirmed: a natural Selective Patch missed update',64,525,1140,100,31,true,amber);
}
{
const s=slide('Over-update: candidates and a negative diagnostic','80 seconds. We keep three distinct pieces of evidence. First, an older Full Rewrite chart trajectory edits all descriptions on an unchanged environment and scores TF8.8 and PE4.2. That is a suggestive regression, not proof of causality and not the main Patch method. Second, six later description rollback versus rewrite executions all score10/10 and complete. That negative result does not confirm the historical harm. Third, a linked-notes research variant appends a rule to metadata-unchanged evaluate and subsequently makes three extra evaluation calls, scoring PE5 against PE10 for original Patch. But four records differ between those arms, and evaluate is related to the changed validator. We cannot call the note unrelated or causally harmful without isolation. None of these is a confirmed natural over-update failure of the main Selective Patch.');
table(s,['Evidence','Observation','Classification'],[['Old Full Rewrite / task235','TF8.8; PE4.2; repeated maps','Suggestive, not Patch'],['6 rollback/rewrite diagnostics','All completed; TF/PE10','Inconclusive causality'],['linked_notes / task133 Middle','PE5 vs10; 6 vs3 calls','Suggestive; confounded']],64,170,1152,330,[370,470,312],24);
text(s,'No confirmed natural over-update failure of the main method',64,550,1140,85,31,true,amber);
}
{
const s=slide('Limits of the evidence','40 seconds. The subset is small, and there is one execution per cell. Provider execution can vary even at temperature zero. Five ratings cannot substitute for independent execution repeats. Our ECS disadvantage is partly driven by an Early truncation under common K0, so it is not direct evidence of harmful updating. Judge scores also have factual blind spots: three diagnostic answers say the annual sum is24.4 million, although the supplied values sum to25.4 million, and all keep their10/10 ratings. We preserve the grades and report the errors. Upstream tool defects, network failures and agent budget exhaustion are kept separate from update failures.');
text(s,'One execution per cell; three tasks; no broad generalization',64,180,1140,75,30,true);
text(s,'Early common K0 still produces different execution outcomes',64,285,1140,75,29);
text(s,'Judge blind spot: 24.4M claimed; correct total is 25.4M\nThree diagnostic answers still received TF/PE10',64,390,1140,100,29);
text(s,'Tool defects, network failures and budget exhaustion are separate',64,540,1140,80,28,false,muted);
}
{
const s=slide('Conclusions and delivery status','40 seconds. We have a fixed-model adaptation pipeline, both baselines, a complete27-cell scored benchmark and reproducible raw-evidence calculations. Patch shows a useful local parameter-update mechanism, retains the chart-task TF and has the highest PE in this cohort. It does not win TF, ECS or normal completion. The main lesson is to report quality, efficiency, stability, cost and completion separately. The remaining course gap is strict failure-case evidence, not a numerical improvement threshold. We stop open-ended optimization. Any diagnostic would need a specific hypothesis and explicit approval; no larger matrix or deployment is scheduled.');
text(s,'Runnable method + complete 27-cell measurement + raw audit',64,180,1140,80,31,true,blue);
text(s,'Observed: higher PE and cheaper updates than Full Rewrite\nAlso observed: lower TF, ECS and normal completion',64,300,1140,115,31);
text(s,'Remaining: strict failure-case evidence and team review\nStop optimization; no new runs or deployments without approval',64,490,1140,120,30,true,amber);
}
{
const s=slide('Appendix: ECS definition and sensitivity','Q&A. For each task, take the mean TF across Early, Middle and Late and subtract its standard deviation, then average across tasks. Population divides squared deviations by3; sample divides by2. Released code uses population, while the paper appendix shows sample. We report both. Patch task133 has9,10,10, which lowers its ECS; the other two tasks have10,10,10. Do not compute ECS from aggregate stage means.',true);
table(s,['Method','ECS population','ECS sample'],data.strategy_means.map(x=>[names[x.method],x.ECS_population.toFixed(4),x.ECS_sample.toFixed(4)]),64,175,1152,270,[450,351,351]);
text(s,'Per task: mean(TF across 3 stages) − standard deviation\nThen average across tasks; do not use the stage-level grand means',64,505,1140,120,29);
}
{
const s=slide('Q&A: fairness, replication and judge scores','Five-minute Q&A preparation. Q: Why only three tasks and one run? A: The brief permits a documented subset and one run under compute constraints; limitations are explicit. Q: Why not use the108-run confirmation? A: It is retained separately; original three arms already have three repeats, but separately frozen rewrites and build protocol should not be silently pooled. Q: Does temperature zero remove variance? A: No, provider execution remains variable. Q: Why not correct judge scores? A: That would change the frozen evaluation after seeing outcomes. Manual factual review is a separate evidence layer.',true);
text(s,'Why one execution?\nAllowed by the brief; uncertainty and coverage remain limited.',64,160,1140,100,28);
text(s,'Why keep the 108-run cohort separate?\nDifferent frozen artifacts; already reusable as an appendix.',64,285,1140,100,28);
text(s,'Why not correct an unfair or mistaken score?\nPreserve the frozen rubric; add transparent human findings.',64,410,1140,100,28);
text(s,'Does temperature 0 imply identical outcomes?  No.',64,565,1140,65,28,true,blue);
}
{
const s=slide('Q&A: failure cases and stopping conditions','Five-minute Q&A preparation continued. Q: Do the examples satisfy the brief? A: Not under a strict reading requiring natural original-Selective-Patch under- and over-update. We state the gaps instead of relabelling baseline or variant failures. Q: Can controlled faults prove the mechanism? A: They can test a local mechanism but are not natural failures or evidence of prevalence, and instructor acceptance is not guaranteed. Q: Is Patch the best method? A: It has the highest mean PE here, but not TF, ECS or completion. Q: Is Netlify required? A: No; it is an optional custom environment demo. Q: What is ready? A: Report, editable deck, notes, raw logs, independent scripts and frozen source, subject to team review and the open failure-case requirement.',true);
text(s,'Do these prove natural Patch under/over-update?\nNo. We keep the strict requirement gap visible.',64,160,1140,100,29);
text(s,'Would fault injection automatically satisfy the course?\nNo. It is a separate mechanism test and needs justification.',64,290,1140,100,29);
text(s,'Must Patch beat every baseline?  No.\nMust we run Netlify or another large matrix?  No.',64,425,1140,105,29);
text(s,'Stop at defensible conclusions; do not search until a result wins.',64,585,1140,60,28,true,blue);
}
if(durations.reduce((a,b)=>a+b,0)!==510)throw new Error('timing');
const dir=path.join(root,'.build/deck-render');await fs.mkdir(dir,{recursive:true});
for(let i=0;i<p.slides.items.length;i++){const s=p.slides.items[i];const blob=await p.export({slide:s,format:'png',scale:1});await fs.writeFile(path.join(dir,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await blob.arrayBuffer()));}
await (await PresentationFile.exportPptx(p)).save(path.join(root,'.build/candidate.pptx'));
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const final=path.join(root,'slides/google-additions.pptx');
const result=await finalizePresentation({workspaceDir:root,candidatePath:path.join(root,'.build/candidate.pptx'),finalPath:final,pythonExecutable:path.join(runtime,'python/bin/python3'),integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit',...[2,3,4,5,6,7,8,11].flatMap(n=>['--require-native-table-slide',String(n)])],requiredNativeTableOwnerSlides:[2,3,4,5,6,7,8,11],tableArithmeticContracts:[{slide:4,table:1,label_column:0,total_row:4,value_columns:[1,2,3],component_rows:[1,2,3]}],fontPolicy:{basis:'design',families:['Arial']},verifyArtifactToolImport:true,receiptPath:path.join(root,'.build/presentation-validation.json')});
await fs.writeFile(path.join(root,'.context/speaker-notes.json'),JSON.stringify({timed_main_seconds:600,existing_opening_seconds:[20,40,30],main_slides:13,appendix_slides:3,notes},null,2));
const escape=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
await fs.writeFile(path.join(root,'speaker-notes.html'),`<!doctype html><html lang="en"><meta charset="utf-8"><title>PE6203 timed speaker notes and Q&A</title><style>body{max-width:950px;margin:40px auto;padding:20px;font:18px/1.7 system-ui;color:#172333}h2{margin-top:36px;color:#102b46}small{color:#53677d}</style><h1>10-minute presentation + 5-minute Q&A</h1><p>13 main slides; planned timings total 600 seconds, including 90 seconds for the preserved first three team slides. Three appendix slides support Q&A. Timings require group rehearsal.</p>${notes.map(n=>`<h2>${n.slide}. ${escape(n.title).replaceAll('\n',' ')}</h2><small>${n.seconds?n.seconds+' seconds':'Q&A appendix'}</small><p>${escape(n.text)}</p>`).join('')}</html>`);
console.log(JSON.stringify({final,slides:p.slides.items.length,planned_seconds:600,validation:'passed'}));

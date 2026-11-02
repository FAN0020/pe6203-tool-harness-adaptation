"""Render the course report from independently recomputed evidence, offline."""

import html
import json
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

R = Path(__file__).resolve().parents[1]
m = json.loads((R / "evidence/recomputed/metrics.json").read_text())
f = json.loads((R / "evidence/failure-cases.json").read_text())
N = {"no_update": "No Update", "full_rewrite": "Full Rewrite", "selective_patch": "Selective Patch"}
pdfmetrics.registerFont(TTFont("Arial", "/System/Library/Fonts/Supplemental/Arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"))
pdfmetrics.registerFontFamily(
    "Arial", normal="Arial", bold="Arial-Bold", italic="Arial", boldItalic="Arial-Bold"
)
S = getSampleStyleSheet()
S.add(
    ParagraphStyle(
        name="BodyX",
        fontName="Arial",
        fontSize=10.5,
        leading=15,
        spaceAfter=8,
        textColor=colors.HexColor("#172333"),
    )
)
S.add(
    ParagraphStyle(
        name="TitleX",
        fontName="Arial-Bold",
        fontSize=23,
        leading=28,
        spaceAfter=18,
        textColor=colors.HexColor("#102b46"),
    )
)
S.add(
    ParagraphStyle(
        name="H2X", fontName="Arial-Bold", fontSize=13, leading=18, spaceBefore=10, spaceAfter=8
    )
)
S.add(ParagraphStyle(name="CellX", fontName="Arial", fontSize=9, leading=12, spaceAfter=0))
S.add(ParagraphStyle(name="CodeX", fontName="Courier", fontSize=8, leading=11, spaceAfter=8))
flow = []
sections = []
current = []


def para(s):
    s = re.sub(
        r"\b(all|for|The|comprise|and|after|with|contains|completed|original|further|fixed|supplied|is|to|versus|scores|round|task|Task|TF|PE|ECS|temperature|Node|Project)(?=\d)",
        r"\1 ",
        s,
    )
    s = re.sub(r"([,;:])(?=\d)", r"\1 ", s)
    flow.append(Paragraph(s, S["BodyX"]))
    current.append("<p>" + s + "</p>")

def blue_para(s):
    para('<font color="#1250A0">' + s + '</font>')


def heading(s, blue=False):
    flow.append(Paragraph('<font color="#1250A0">' + s + '</font>' if blue else s, S["H2X"]))
    current.append('<h3' + (' style="color:#1250A0"' if blue else '') + '>' + s + '</h3>')


def code(s):
    flow.append(Paragraph(html.escape(s).replace("\n", "<br/>"), S["CodeX"]))
    current.append("<pre>" + html.escape(s) + "</pre>")


def table(headers, rows, widths=None):
    cells = [[Paragraph(html.escape(str(x)), S["CellX"]) for x in row] for row in [headers] + rows]
    t = Table(
        cells, colWidths=widths or [491 / len(headers)] * len(headers), repeatRows=1, hAlign="LEFT"
    )
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef4")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#142539")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#ced7e2")),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 4 if len(rows) > 20 else 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4 if len(rows) > 20 else 6),
            ]
        )
    )
    flow.extend([t, Spacer(1, 10)])
    current.append(
        '<div class="scroll"><table><tr>'
        + "".join("<th>" + html.escape(str(x)) + "</th>" for x in headers)
        + "</tr>"
        + "".join(
            "<tr>" + "".join("<td>" + html.escape(str(x)) + "</td>" for x in row) + "</tr>"
            for row in rows
        )
        + "</table></div>"
    )


def page(title, blue=False):
    global current
    if current:
        sections.append("".join(current))
        flow.append(PageBreak())
    current = ['<section><h2' + (' style="color:#1250A0"' if blue else '') + '>' + title + '</h2>']
    flow.append(Paragraph('<font color="#1250A0">' + title + '</font>' if blue else title, S["TitleX"]))


def ev(s):
    para('<font color="#50647b">Evidence: ' + html.escape(s) + "</font>")


page("Tool Harness Adaptation<br/>under Environment Change")
para("<b>PE6203 Group Project 4 | Final offline audit | 31 October 2026</b>")
heading("Research questions")
para(
    "Does updating affected tool knowledge recover task performance after persistent tool-environment change? Does it preserve capabilities on tasks whose tools remain unchanged? We evaluate quality, efficiency, cross-version stability, update cost and execution status separately; no weighted score is introduced."
)
heading("Abstract")
para(
    "We implement a deterministic Selective Patch that compares tool metadata, expands the affected set through explicit dependencies, updates affected records and preserves unaffected knowledge. The same fixed DeepSeek model executes a documented three-task MCPEvol-Bench subset in Early, Middle and Late environments under No Update, Full Rewrite and Selective Patch. One execution per cell gives 27 trajectories, each with five valid judge ratings."
)
para(
    "Independent recalculation from the frozen raw archive confirms that Selective Patch has the highest observed mean Planning Effectiveness (9.1111), but lower mean Task Fulfillment (9.8889), population ECS (9.7318) and normal completion (6/9) than both baselines. It uses zero model tokens for updating, tied with No Update, and 1.145 seconds of local update time. Its changed-task TF gain relative to No Update is 0 in Middle and +0.1 in Late; unchanged-task TF is retained."
)
para(
    "The results establish a runnable, auditable course experiment. They do not establish general superiority, statistical significance or broad generalization. Early arms share identical knowledge, yet exhibit different truncation and completion outcomes. This variation materially affects ECS."
)
heading("Submission status")
para(
    "<b>The main experiment is verified. Failure-case acceptance remains unresolved.</b> The brief does not require naturally occurring failures. Four approved controlled diagnostics establish a missing-parameter rejection mechanism, while course acceptance of that injected case needs TA clarification. The over-update claim still lacks a demonstrated change to unrelated knowledge that causes damage. Negative diagnostics remain part of the evidence."
)
para(
    "This final revision performs offline verification only. It integrates the four previously approved diagnostic trajectories, kept separate from the main 27. No additional model calls, scoring, strategy development or deployment occurred. Historical scores and billing uncertainties remain unchanged. Appendix C-E document the baseline, actual change coverage and diagnostic limits."
)
ev(
    "results/evidence/course-v1.3-20261031/raw-trial.tar.gz; submission/evidence/recomputed/metrics.json; failure-cases.json; original course brief §§3-4."
)
page("1. Method and architecture")
para(
    "A harness stores tool names, input schemas, descriptions, usage rules, output schemas and routing. Persistent environment changes can make these records stale even if the base model remains fixed. Our intervention is the tool-knowledge snapshot presented to the agent, not model fine-tuning."
)
heading("Adaptation pipeline")
code(
    "Early knowledge K0 + target-stage metadata\n        -> deterministic add / remove / field diff\n        -> affected records + explicit one-hop dependencies\n        -> copy authoritative target fields for affected records\n        -> preserve unaffected records and valid usage rules\n        -> schema / routing / preservation validation\n        -> frozen knowledge Kt -> common agent -> real MCP tools\n        -> raw trajectory + five judge ratings + independent analysis"
)
para(
    "Tool identity is server_id::name. The comparison covers name, parameters, description, output_schema and routing; a rename without stable identity evidence is treated as removal plus addition. Structural changes propagate through explicit tool references in usage rules. Target metadata is authoritative for structural fields. Usage rules are preserved rather than erased by an empty metadata field; unresolved semantic dependencies are recorded. The evaluated Selective Patch performs no LLM update calls."
)
table(
    ["Method", "Knowledge policy"],
    [
        [N["no_update"], "Retain the Early snapshot K0 after environmental change."],
        [
            N["full_rewrite"],
            "Rebuild all target records and use the fixed LLM to regenerate every target description; protect schemas, routes and supplied rules.",
        ],
        [
            N["selective_patch"],
            "Update affected records by deterministic diff and dependency expansion; preserve unaffected records.",
        ],
    ],
    [105, 386],
)
para(
    "All three methods use the same execution agent to choose tools, arguments and next steps. Candidate MCP servers come from the official task. No task-specific call sequence is scripted. Early uses common K0 in every arm. This implementation compares both update scope and description-generation mechanism; it is not a pure scope-only ablation."
)
ev(
    "Frozen source src/pe6203/selective.py, baselines.py, runner.py and integration/baselines.py; per-cell adaptation/adaptation.json and knowledge.json."
)
page("2. Experimental setup and controls")
table(
    ["Task", "Role", "Represented changes"],
    [
        [
            "133",
            "Changed: mathematical syntax and security guidance",
            "Middle: optional parameters; Late: required allow_variables and relevant optional tool addition.",
        ],
        [
            "283",
            "Changed: analytics project decomposition",
            "Tool additions plus parameter and description changes in planning/project tools.",
        ],
        [
            "235",
            "Unchanged: supplied sales visualization",
            "28 chart-tool records canonically unchanged; used for retention.",
        ],
    ],
    [43, 175, 273],
)
para(
    "The fixed subset is identical across methods. TOOL coverage is limited to relevant optional additions, not mandatory renaming/removal. PARAM and DESC changes affect required tools. Metadata coverage does not mean every trajectory actually called every changed tool. Task 283 shares a service family with development task 139, so this is not an unseen-family evaluation."
)
table(
    ["Control", "Frozen value"],
    [
        [
            "Model / provider",
            "deepseek/deepseek-v4.1-flash-1017 via OpenRouter; same agent, judge and updater model",
        ],
        ["Decoding", "temperature 0; provider seed not sent"],
        ["Agent budget", "4096 output tokens; 12 rounds; 900-second run budget"],
        ["Timeouts / retry", "request 120 s; tool 30 s; at most one HTTP retry"],
        ["Updater", "16384 output tokens; 120 s timeout; one HTTP retry"],
        [
            "Judge",
            "4096 output tokens; reasoning disabled; JSON; five first-valid slots; at most two logical attempts per slot",
        ],
        [
            "Measurement",
            "Original rubric with common concise output contract and deterministic call counts appended",
        ],
        [
            "Execution",
            "3 tasks x 3 stages x 3 strategies x 1 execution = 27; 135 valid rating slots",
        ],
    ],
    [105, 386],
)
para(
    "One execution is permitted by brief §3.2 under compute constraints and is explicitly disclosed. Five judge ratings are measurements of the same trajectory, not five independent agent executions. All 135 slots in this main cohort succeeded on their first logical attempt. No benchmark labels or question text were modified."
)
para(
    "Checks from the archive confirm identical task-question hashes, model settings, budgets and static judge rubric within matched task/slot groups. Prompt evidence necessarily varies with each trajectory. Historic v1.2, v1.3 and research cohorts remain separate."
)
ev(
    "main archive plan.json, plan.sha256, saved judge prompts, judge-attempts/*/response.json; evidence/recomputed/metrics.json fairness block."
)
page("3. Main results and execution status")
table(
    ["Method", "Mean TF", "Mean PE", "ECS pop.", "ECS sample", "Completed"],
    [
        [
            N[x["method"]],
            f"{x['TF']:.4f}",
            f"{x['PE']:.4f}",
            f"{x['ECS_population']:.4f}",
            f"{x['ECS_sample']:.4f}",
            f"{x['completion'].get('completed', 0)}/9",
        ]
        for x in m["strategy_means"]
    ],
    [105, 68, 68, 84, 84, 82],
)
para(
    "Each mean equally weights nine task-stage cells; each cell score averages five stored ratings. Scored trajectories with truncation or round exhaustion remain included. Selective Patch has observed PE gains of +1.2444 against No Update and +0.7556 against Full Rewrite. These are descriptive differences on one small cohort, not tested population effects."
)
table(
    ["Method / stage", "TF", "PE"],
    [
        [N[x["method"]] + " / " + x["stage"].title(), f"{x['TF']:.4f}", f"{x['PE']:.4f}"]
        for x in m["stage_means"]
    ],
    [291, 100, 100],
)
table(
    ["Method", "Completed", "Max rounds", "Truncated"],
    [
        [
            N[x["method"]],
            x["completion"].get("completed", 0),
            x["completion"].get("max_rounds", 0),
            x["completion"].get("output_truncated", 0),
        ]
        for x in m["strategy_means"]
    ],
    [191, 100, 100, 100],
)
para(
    "Across all 27 trajectories: 20 completed, five exhausted their round budget and two were truncated. Normal completion means the agent loop ended normally with a non-empty answer, not independent proof of correctness. TF can be 10 even when the agent has not ended normally."
)
ev(
    "evidence/recomputed/cells.csv; all run/result.json, raw_trace.json and immutable EVAL outputs in main archive."
)
page("4. Exact PE check and ECS conventions")
pe = [x for x in m["cells"] if x["method"] == "selective_patch"]
table(
    ["Task", "Stage", "Five raw PE ratings", "Cell PE"],
    [
        [x["task"], x["stage"].title(), ", ".join(map(str, x["PE_ratings"])), f"{x['PE']:g}"]
        for x in pe
    ],
    [55, 80, 271, 85],
)
para(
    "<b>(10 + 8 + 7 + 10 + 10 + 10 + 9 + 9.4 + 8.6) / 9 = 82 / 9 = 9.111111...</b> The reported 9.1111 is correct. The independent script uses exact rational arithmetic for score means; it never edits stored ratings."
)
heading("Cross-version ECS")
para(
    "For each task, first compute the mean of its three TF values, then subtract their standard deviation. ECS is the average of these task-level quantities. It is not computed by subtracting the spread of three overall stage means."
)
code(
    "mu_t = (TF_early + TF_middle + TF_late) / 3\nsigma_population = sqrt(sum((TF_i - mu_t)^2) / 3)\nsigma_sample     = sqrt(sum((TF_i - mu_t)^2) / 2)\nECS = mean_over_tasks(mu_t - sigma_t)"
)
para(
    "The released implementation uses population standard deviation; the paper appendix specifies the sample convention. Both are reported, with population as the primary implementation-compatible result. For Selective Patch, task133 TF=[9,10,10] gives task ECS 9.1953 (population) or 9.0893 (sample); tasks235 and283 each give10. Therefore overall ECS is9.7318 or9.6964."
)
para(
    "The low Early TF on task133 occurred with common K0 and output truncation. It reduces the Patch ECS, but cannot be attributed to a patch that was not yet applied. Conversely, higher subsequent TF is not automatically a pure update effect."
)
ev(
    "evidence/recomputed/metrics.json: selective_PE and ecs_by_task; MCPEvol-Bench §6.1, Appendix D.1; upstream evaluation code in frozen source provenance."
)
page("5. Recovery and retention")
heading("Changed tasks: 133 and 283")
table(
    ["Method", "Stage", "Mean TF", "Delta vs same-stage No Update", "Delta vs own Early"],
    [
        [
            N[x["method"]],
            x["stage"].title(),
            f"{x['TF']:.2f}",
            f"{x['delta_TF_vs_no_update']:+.2f}",
            f"{x['delta_TF_vs_own_early']:+.2f}",
        ]
        for x in m["recovery"]
    ],
    [120, 65, 65, 125, 116],
)
para(
    "Selective Patch matches No Update in Middle and is +0.1 TF higher in Late on the two changed tasks. Its own Early-to-Late increase is partly sensitive to the Early truncation. The more direct local mechanism is task133 Late: four initial No Update calls omit a newly mandatory parameter and are rejected; Patch provides that parameter and has no tool errors in its corresponding run. No Update later repairs its calls using error feedback, reducing the final TF gap."
)
heading("Unchanged task: 235")
table(
    ["Method", "Stage", "TF", "PE", "Delta PE vs own Early"],
    [
        [
            N[x["method"]],
            x["stage"].title(),
            f"{x['TF']:.1f}",
            f"{x['PE']:.1f}",
            f"{x['delta_PE_vs_own_early']:+.1f}",
        ]
        for x in m["retention"]
    ],
    [140, 75, 60, 60, 156],
)
para(
    "Every task235 TF is10, so all TF retention deltas are zero. Patch retains its three chart-tool calls and PE10. No Update Middle has five map calls and PE4.8 despite unchanged knowledge, showing that redundant actions need not come from rewriting. Tool output consists of chart specifications: browser rendering and a hosted dashboard were not validated."
)
ev(
    "Recomputed recovery and retention arrays; tasks133/283 labelled changed and235 unaffected before scoring in the frozen suite."
)
page("6. Update and execution costs")
table(
    ["Method", "Update tokens", "Update seconds", "Update API USD"],
    [
        [N[x["method"]], x["update_tokens"], f"{x['update_seconds']:.6f}", f"{x['update_usd']:.9f}"]
        for x in m["strategy_means"]
    ],
    [141, 110, 120, 120],
)
para(
    "Selective Patch is cheaper to update than Full Rewrite, but is tied with No Update at zero model tokens and zero API dollars. No Update also has zero measured update time, whereas Patch performs local diff and validation work. Zero API dollars does not imply zero computation or engineering cost."
)
table(
    ["Main-cohort cost component", "Known USD"],
    [
        ["Agent requests", f"{sum(c['agent']['known_usd'] for c in m['costs']):.9f}"],
        ["Judge requests", f"{sum(c['judge']['known_usd'] for c in m['costs']):.9f}"],
        ["Adaptation", f"{sum(c['update']['usd'] for c in m['costs']):.9f}"],
        ["Preflight", f"{m['preflight']['known_usd']:.9f}"],
        ["Known total (lower bound)", f"{m['known_total_usd']:.9f}"],
    ],
    [331, 160],
)
para(
    "<b>Unknown billing:</b> task283 Late Selective Patch had an APIConnectionError at agent round5 followed by the preconfigured retry. The failed request has no usage or fee data. Recorded aggregate tokens and complete USD therefore remain null for that agent execution; successful-response usage supplies a known lower bound only. The total above is not an exact invoice."
)
para(
    "Update token/API amounts were checked against raw updater response usage; update elapsed time comes from stored adaptation timer records. Agent and judge costs were recomputed from their response usage, including failed-request uncertainty. Local timings are not independent wall-clock measurements. Update costs are not multiplied by the five judge ratings."
)
para(
    "Historical development, diagnostics and confirmation runs are separate costs. Six retention diagnostics cost a recorded $0.0527461802; the main-cohort known total excludes them. Failed confirmation rounds and stopped connectivity diagnostics retain their own logs and incomplete bills in the historical archive set."
)
ev(
    "evidence/recomputed/metrics.json costs and unknown_billing; adaptation/updater-audit.json; raw trace request_retry event; history archive manifest."
)
page("7. Failure evidence: under-update and confounds")
para(
    "We classify a stated claim as <b>confirmed</b> (direct mechanism evidence), <b>suggestive</b> (plausible but confounded), <b>inconclusive</b> (insufficient evidence), or <b>contradicted</b> (inconsistent with stored knowledge/calls). Confirmation of a local failure does not establish a general strategy effect."
)
heading("U1 - Confirmed stale No Update call failure")
para(
    "Task133 Late: Early validate_syntax requires expression only; Late also requires allow_variables. No Update keeps the Early schema. Four initial validation calls omit allow_variables and are rejected; later calls add the parameter after reading errors. The agent completes with TF9.8/PE7.2 after38 calls. The stale-schema-to-rejection chain is direct, but it is a No Update observation, not a Selective Patch under-update example."
)
heading("U2 - Contradicted omission attribution for Patch")
para(
    "The main Selective Patch artifact contains the required field and its three validate_syntax calls explicitly pass allow_variables. It completes with TF10/PE7, four total calls and zero tool errors. Calling this a missed parameter update would contradict the actual records."
)
heading("B1 and P1 - Different failure mechanisms")
para(
    "Task133 Early Patch truncates in round2 with TF9/PE10, although every Early arm has identical K0. An update-caused explanation is contradicted. Task283 Late Patch reports review_workspace_health failing because listMemories is missing; it also has two empty-argument create_task errors, an API retry and round exhaustion. The tool error is observed directly, but its contribution to the terminal failure is not isolated. Neither should automatically be called under-update or over-update."
)
heading("Audit scope")
para(
    "We screened all317 accessible raw_trace.json files, with comparable old/updated/target metadata for298. The72 structural candidates comprise31 No Update stale snapshots,40 Full Rewrite cases with edits to metadata-unchanged tools, and one linked_notes case. Six stale-parameter mechanisms are confirmed, two cases are suggestive and64 remain inconclusive. Nine selected case studies receive deeper semantic review. The screen does not prove absence of all semantic usage-rule omissions;19 traces lack complete comparable metadata."
)
para(
    "<b>Controlled evidence:</b> removing the required allow_variables fact from a correct snapshot produces eight matching rejections, versus zero with the complete snapshot. This confirms the local injected mechanism. It does not show that the original updater naturally omitted the field. The brief does not impose a natural-occurrence condition. Whether this controlled trajectory satisfies the failure-analysis deliverable remains a TA question, not an automatic pass or fail. See Appendix E."
)
ev(
    "evidence/trajectory-inventory.csv; trajectory-screening.json; failure-cases.json; case-details/U1.json, U2.json, B1.json, P1.json. Each case includes exact old/updated/target fields and calls."
)
page("8. Failure evidence: over-update and negative results")
heading("O1 - Suggestive historical Full Rewrite regression")
para(
    "In the older task235 Late cohort, all28 chart records are unchanged across environments. Full Rewrite nevertheless regenerates every description. Its trajectory makes five map calls and omits map-unit metadata, with TF8.8/PE4.2 versus10/10 for the other arms. However, the rewritten description explicitly mentions dataValueUnit. The omission therefore cannot be explained as guidance simply disappearing. The regression is not itself proof that rewriting caused damage, and this is Full Rewrite rather than Selective Patch."
)
heading("O3 - Inconclusive causal attribution after negative diagnostics")
para(
    "Six existing controlled description-rollback executions, three per arm, all complete with TF/PE10 and three tool calls. They do not reproduce the historical damage. We retain this negative result and do not repeat it until a desired effect appears. It does not establish that harmful rewrites are impossible."
)
heading("O2 - Suggestive scope expansion in linked_notes")
para("A historical research variant adds this rule to metadata-unchanged math-mcp::evaluate:")
para(
    "<i>validate_syntax now accepts optional detailed and allow_variables flags; evaluate's validate_only remains a separate syntax-only path, so choose based on whether evaluation is also wanted.</i>"
)
para(
    "The task133 Middle trajectory performs two syntax checks and a security-prompt call, then three evaluate calls. It completes with TF10/PE5; original Patch in that cohort uses three calls and scores10/10. Four usage-rule records differ between these arms, so the note is not an isolated treatment. Also, evaluate is semantically related to the changed validator: metadata-unchanged does not necessarily mean unrelated. This is a suggestive research-variant case, not a confirmed failure of the main method."
)
heading("Judge limitation: correct scores are not corrected answers")
para(
    "A fresh factual review of the six diagnostic answers finds three claiming the monthly sales sum is24.4M: rewrite-r0, rewrite-r2 and rollback_descriptions-r0. The supplied12 numbers sum to25.4M. All three retain their original TF/PE10. Errors in both arms weaken any claim of rewrite-specific factual harm and demonstrate that high judge ratings can miss answer defects."
)
para(
    "<b>Unresolved over-update evidence:</b> a later one-rule retained/reverted comparison is suggestive, but the rule concerns a related validator and cannot be assumed unrelated. Thus neither that pair nor the negative chart rollback establishes the full unrelated-change-to-damage chain required by the definition. See Appendix E. Lack of natural occurrence is not the acceptance criterion."
)
ev(
    "case-details/O1.json and O2.json contain exact descriptions/rules; diagnostic-review.json identifies all six trajectories; raw answers and five ratings remain unchanged."
)
page("9. Interpretation and limits")
heading("Supported observations")
para(
    "Selective Patch updates tool knowledge without model calls and prevents the specific initial missing-parameter errors seen in No Update task133 Late. In this cohort it retains task235 TF and has the highest mean PE. Full Rewrite leads the mean TF and ECS comparisons; both baselines have more normally completed runs. These outcomes can coexist and do not require a composite winner."
)
heading("What the data do not establish")
para(
    "One execution per cell on three tasks is not enough to estimate robust strategy-level uncertainty, frequency of rare failures or generalization to the full benchmark. Temperature0 does not make provider execution deterministic. Five judge ratings characterize one saved trajectory, not run-to-run agent variance. No inferential significance claim is made for the27-run main cohort."
)
para(
    "TF is near the scale ceiling, and incomplete trajectories can receive high TF. Early differences under identical K0 affect cross-version scores. The same model family acts as agent and judge. Rubric interpretation of distinct security checks and redundant calls is imperfect; manual factual findings are reported separately, never silently substituted for ratings."
)
para(
    "The subset lacks required tool removal/renaming, uses optional tool additions, and is not an unseen-family holdout. The runner uses native stdio and common local adaptation plumbing, rather than an exact recreation of every paper infrastructure choice. Full Rewrite and Patch differ in both update scope and generation mechanism. Public MCP package defects are kept common across arms."
)
heading("Reuse of prior work")
para(
    "The completed108-trajectory research confirmation contains81 executions of the original three methods with three repeats each. It can serve as a separate robustness appendix, alongside its fourth candidate and negative promotion result. Its frozen Full Rewrite artifacts and shared-build protocol differ from the main cohort, so results are not pooled. Sixty research development trajectories, old A/B cohorts, incomplete confirmations, generation rejections and negative diagnostics remain available as history."
)
para(
    "The historical PE+0.5 and statistical-promotion thresholds are not course completion requirements. Netlify/task223 is an optional custom deployment demonstration; it is not required to complete the fixed27-cell experiment and is not run here. VPN involvement is possible in past connection failures, but not established as their cause."
)
heading("Stopping rule")
para(
    "Stop strategy optimization and further execution. Review the evidence with the group and seek TA clarification on controlled cases and the implemented Full Rewrite scope. The outstanding issue is strength and relevance of evidence, not whether failures arose naturally or whether Patch beats a baseline. No more diagnostics,81/108-cell matrices or deployment are authorized."
)
page("10. Reproducibility and delivery")
para(
    "The repository delivery contains this updated report, shared presentation and current notes, independent calculations, frozen source/configuration and raw archives. The original report and two ZIP bundles remain frozen historical snapshots. This revision supersedes their earlier strict-natural acceptance wording without changing any scores. HANDOVER.md tracks open items and the Git delivery receipt. No external deployment or TA message is sent."
)
heading("Offline recalculation - no credentials or dependencies")
code("python3 submission/handover-20261031/verify.py")
para(
    "From the repository root, run: python3 submission/handover-20261031/verify.py. It blocks networking, recomputes the main 27 cells and135 ratings, checks all target-record rewrites and actual changed-tool calls, reconstructs10,959 frozen files from committed archives in a temporary directory, replays the historical case audit and independently recalculates the four diagnostic cells. It requires only Python3.12+ standard library. Inputs remain read-only; the experimental pipeline is not executed."
)
heading("Optional future execution - authorization required")
code(
    "mkdir -p frozen-source\ntar -xzf submission/evidence/source-main-12d693c.tar.gz -C frozen-source\ncd frozen-source\nuv sync --frozen\n# Install pinned Node and released MCP environments per RUNBOOK.html.\n# Configure credentials locally; do not put them in the package.\n./experiment prepare --suite experiments/benchmark-v1.3.json \\\n  --repeats 1 --output results/raw/approved-new-run\n./experiment run --output results/raw/approved-new-run"
)
para(
    "These commands are documentation, not an instruction to rerun the completed experiment. A fresh execution may not reproduce identical numerical scores because the provider is stochastic. Reproduction of archived arithmetic is exact; fresh behavioral reproduction is a separate, billable activity requiring approval."
)
heading("Provenance")
para(
    "Main source commit:12d693c. Benchmark commit:888c779a0fe735f612ca62bdd1fdd7c9e6bf8701. Dataset revision:162e3ffbea1717ac8a20fe9b26465e29117229e4. Runtime recorded as macOS arm64, Python3.12.12, Node24.13.0; Python dependencies are locked in uv.lock. Full released environment archives require a separate large download; the raw arithmetic replay does not."
)
code("Main archive SHA-256:\ne95e15694abe9a12e37c813f81e6e0fb0b5ccd00c2003f2a25a36a092c8001c9")
heading("References")
para(
    "[1] PE6203 Group Project4: Tool Harness Adaptation under Environment Change, course brief, §§3-4. [2] Liu et al., MCPEvol-Bench: Benchmarking LLM Agent Performance Across Dynamic Evolutions of MCP Servers, arXiv:2607.14642v1,2026, §6.1 and AppendixD.1. https://arxiv.org/html/2607.14642v1 . [3] Frozen benchmark release and course implementation identified above. [4] Local immutable experiment and diagnostic records indexed in evidence/."
)
page("Appendix A. All 27 scored cells")
table(
    ["Task", "Stage", "Method", "TF", "PE", "Execution status"],
    [
        [
            x["task"],
            x["stage"],
            N[x["method"]],
            f"{x['TF']:g}",
            f"{x['PE']:g}",
            x["execution_status"],
        ]
        for x in m["cells"]
    ],
    [40, 60, 130, 45, 45, 171],
)
para(
    "Every row averages five valid ratings. Status is retained independently of the scores. Raw rating arrays, exact fractions, tool-call counts and per-cell usage are available in evidence/recomputed/metrics.json and cells.csv."
)
page("Appendix B. Completion checklist")
table(
    ["Required deliverable", "State", "Evidence / outstanding work"],
    [
        [
            "Selective method and two baselines",
            "Ready",
            "Frozen source, configs and 27 real trajectories.",
        ],
        [
            "TF/PE/ECS and execution status",
            "Verified",
            "Independent raw-archive recalculation; both ECS conventions.",
        ],
        [
            "Recovery and retention",
            "Verified, limited scope",
            "Two changed tasks and one unchanged task; no broad claim.",
        ],
        [
            "Update cost",
            "Verified with uncertainty",
            "Tokens/time/API separated; one main failed-request charge unknown.",
        ],
        [
            "Under-update failure trajectory",
            "TA acceptance pending",
            "Controlled omission confirms local rejection; original updater did not omit the field.",
        ],
        [
            "Over-update failure trajectory",
            "Evidence incomplete",
            "Related-rule contrast is suggestive; unrelated-change causal damage unproven.",
        ],
        [
            "Report and reproducibility",
            "Prepared for review",
            "This report, scripts, logs, source and manifests.",
        ],
        [
            "10-minute presentation + Q&A",
            "Prepared for review",
            "Editable deck, timed speaker notes and Q&A; group rehearsal outstanding.",
        ],
        [
            "Final submission",
            "Repository delivery prepared",
            "Git status in HANDOVER / delivery receipt; team course registration and TA clarification remain.",
        ],
    ],
    [141, 110, 240],
)
para(
    "The brief requires example trajectories with under-update and over-update analysis, but does not require natural occurrence. An injected omission is labelled as such; it is not automatically invalid or sufficient. Over-update still needs evidence that changed knowledge was unrelated and caused harm. Course acceptance and Full Rewrite interpretation need TA clarification. This report does not declare those unresolved items complete."
)
para(
    "The next permissible work is offline review and group preparation. Additional model calls, diagnostics, task/repeat expansion and Netlify deployment remain disallowed without explicit approval."
)
page("Appendix C. Full Rewrite scope audit")
para(
    "Brief §§2 and4.1 call for rewriting the complete tool-related knowledge. The implemented baseline rebuilds every record from target metadata and asks the fixed LLM to regenerate all target descriptions. This is full-catalog regeneration under a protected-structure interpretation, not free-form generation of every field. The archived implementation is unchanged."
)
table(
    ["Knowledge field", "Observed handling", "Evidence / limit"],
    [
        [
            "Tool membership, identity, name",
            "Rebuild the complete target list; additions included and obsolete identities removed",
            "All six updated snapshots cover exactly the target identities.",
        ],
        [
            "Input schema / parameters",
            "Copy target JSON Schema unchanged",
            "LLM is not permitted to change schema or constraints.",
        ],
        [
            "Description",
            "LLM regenerates every target description, including unchanged tools",
            "209/209 returned and textually different from target prose.",
        ],
        [
            "Usage rules",
            "Copy supplied target rules verbatim; absent becomes []",
            "Validator rejects invented or changed rules; does not regenerate independent rules.",
        ],
        [
            "Output schema",
            "Copy target field, including null when unavailable",
            "Same representation reaches agent across all methods.",
        ],
        [
            "Routing / server IDs",
            "Copy target routing; shared runner applies deterministic namespacing",
            "No LLM routing synthesis.",
        ],
        [
            "Early condition",
            "Reuse identical K0; no updater call",
            "Three Early controls are not counted as rewrites.",
        ],
    ],
    [110, 190, 191],
)
a = json.loads((R / "handover-20261031/audit.json").read_text())["main"]
table(
    ["Task", "Stage", "Target records", "Descriptions regenerated"],
    [
        [x["task"], x["stage"], x["target_tools"], x["generated_descriptions"]]
        for x in a["full_rewrite"]
    ],
    [55, 85, 160, 191],
)
para(
    "The updater receives only the target catalog and constraint checks, not old knowledge, task text, answers, scores or evolution labels. All three methods share the same model, decoding, task, execution budget and judge protocol. Their update algorithms intentionally differ: LLM description regeneration versus deterministic affected-record copying. Therefore results compare methods, not a controlled scope-only ablation. Schema preservation avoids inventing incompatible APIs but narrows the meaning of Full Rewrite. Ask the TA whether this operationalization meets the expected complete-knowledge baseline."
)
ev(
    "handover-20261031/audit.json full_rewrite; archived adaptation/updater-audit.json requests and responses; frozen integration/baselines.py and src/pe6203/baselines.py at 12d693c."
)
page("Appendix D. Change coverage and actual contact")
para(
    "Each transition below compares Early K0 with the stated target environment, matching how adaptation was executed. Counts are actual model tool calls in the main 27 trajectories, ordered No Update / Full Rewrite / Patch. A changed catalog entry, task relevance and executed contact are different evidence levels. Contact does not isolate the behavioral effect of one changed description."
)
table(
    ["Type / task / target", "Environment and task relevance", "Actual calls NU / FR / SP"],
    [
        [
            "PARAM /133 /Middle",
            "validate_syntax adds optional detailed and allow_variables; central to expression checking",
            "6 /12 /11",
        ],
        [
            "PARAM /133 /Late",
            "validate_syntax requires allow_variables; direct required-tool change",
            "13 /5 /3. Initial NU omissions rejected; Patch supplies parameter.",
        ],
        [
            "DESC + PARAM /283 /Middle, Late",
            "create_project adds metadata parameters and changes description; directly relevant project setup",
            "1 /1 /1 in each stage. Optional fields need not all be used.",
        ],
        [
            "TOOL /283 /Late",
            "review_workspace_health newly available; optional project-workspace inspection, not required by task",
            "0 /1 /1. FR succeeds with includeMemories=false; Patch errors with true.",
        ],
        [
            "TOOL /133 /Late",
            "batch_evaluate addition is relevant to multi-expression work, optional",
            "0 /0 /0 in main cohort. Used in controlled diagnostic only.",
        ],
        [
            "TOOL /283 /Middle, Late",
            "parallel-thinking / convergent-synthesis planning additions, optional",
            "0 /0 /0 for these new tools.",
        ],
        [
            "DESC (+ PARAM Late) /283",
            "sequentialthinking changes; relevant reasoning capability",
            "0 /0 /0 in Middle and Late.",
        ],
        [
            "Retention /235 /all stages",
            "All 28 chart records unchanged after removing version tags",
            "No TOOL / PARAM / DESC change; retention control.",
        ],
    ],
    [116, 230, 145],
)
para(
    "The observed review_workspace_health failure is Error: memoryStorage.listMemories is not a function. The differing includeMemories arguments expose a common upstream defect; they do not establish a patch-update error. No Update does not know this new tool. The tool is optional and task relevance is an analyst interpretation based on project/workspace planning, not a new required-tool label."
)
para(
    "Thus the subset contains all three change levels and includes executed contact for each. Coverage remains narrow: optional additions only, no required deletion/rename, and no isolated description-only causal test. Other server-catalog changes unrelated to the task are not counted as stronger task coverage. The complete 29 changed records, exact field differences, arguments and observations are retained in the audit JSON and coverage CSV."
)
ev(
    "handover-20261031/coverage.csv; audit.json coverage; main archive catalogs/{task}/{stage}.json and cells/task{task}-{stage}-{method}-r0/run/raw_trace.json."
)
page("Appendix E. Approved diagnostics and TA questions")
table(
    ["Controlled condition", "TF", "PE", "Calls / errors", "Terminal state"],
    [
        ["Under: omitted fact", 10, 5.8, "27 /9", "Truncated"],
        ["Under: complete fact", 10, 5.6, "5 /1", "Completed"],
        ["Over candidate: rule retained", 10, 7.8, "22 /2", "Truncated"],
        ["Over candidate: rule reverted", 9.8, 10, "4 /0", "Completed"],
    ],
    [160, 40, 45, 110, 136],
)
para(
    "<b>Under-update mechanism: confirmed fault injection.</b> Task133 Late removes only allow_variables from validator properties and required fields. Eight calls omit it and receive the exact missing-field rejection; the complete arm has zero such rejections. Both TF values remain10 and PE does not improve on correction. Another tool implementation error and four incorrect judge rationales affect the complete arm. This is a controlled knowledge omission, not evidence that the original adaptation algorithm missed the change."
)
para(
    "<b>Over-update candidate: suggestive, definition not established.</b> Task133 Middle uses a historical linked_notes snapshot. Only one evaluate usage rule differs between retained/reverted arms; the other three historical rules are held fixed. The rule discusses the changed validator and the distinction between validation and evaluation. Consequently metadata-unchanged evaluate is not demonstrably unrelated knowledge. More calls, lower PE and truncation coexist with the rule, but one stochastic execution per arm and a TF tradeoff prevent a strong causal claim. Earlier six chart rollback runs remain negative."
)
para(
    "All four runs were previously approved, used the main frozen model/budgets/judge and no updater calls, and cost $0.04600192 with no unknown charges. Recorded execution plus judging time is160.707 seconds. They are separate from the27-cell main means. This final audit adds zero model calls and does not replace any score."
)
heading("Draft clarification questions - not sent")
para(
    "1. May the explicitly injected missing-knowledge trajectory satisfy under-update analysis despite unchanged TF and no demonstrated original-updater omission? The brief contains no natural-occurrence requirement.\n2. May we present over-update candidates and negative controls as an unresolved finding, or is a stronger unrelated-change failure required?\n3. Does full-catalog rebuilding with all descriptions regenerated and schema/rules/routing copied from authoritative target metadata meet the Full Rewrite definition?\n4. Does the documented optional-addition coverage with actual contact meet the intended Tool-level scope, with deletion/rename untested?"
)
para(
    '<font color="#1250A0">TA clarification remains open. Later user authorization permits bounded local research; frozen scores are unchanged, and external submission or deployment is not authorized.</font>'
)
ev(
    "diagnostics-20261031/plan.json, exact-knowledge-diffs.json and audit.json; targeted-diagnostics archive; HANDOVER.md. This clarification supersedes earlier strict-natural wording; diagnostic facts remain unchanged."
)
page("2 November 2026. Scope and merge addendum", blue=True)
heading("Task selection and the 27-run baseline", blue=True)
blue_para(
    "The course brief permits a documented fixed subset of the 201 released tasks. Earlier team materials included task 223, retrieval of recent research papers for webpage publication. Before model scoring, the course matrix instead froze task 133 (mathematical-expression guidance), task 283 (project planning), and unchanged task 235 (chart behavior) because the original inputs and archived services were locally executable. Its 27 agent trajectories are three tasks × three stages × three methods × one execution, with five judge ratings per trajectory. They do not test the earlier paper-webpage scenario or a verified book task. The available written record does not show team sign-off for this task switch."
)
blue_para(
    "The task 223 original fetch and publication services were not verified for the frozen matrix. A later Netlify version changes the publication backend and must be identified as a separate environment; its three-stage tool catalogs do not by themselves demonstrate recovery after tool change. The 27-run scores remain valid for the stated 133/283/235 subset and are not relabeled as paper or book results."
)
heading("Which research evidence can be carried forward", blue=True)
blue_para(
    "A later registry snapshot listed 29 candidate names; 27 had actor evidence, two had generation or admission records only, and none had task 223 actor results. The registry later grew to 36 and then 43 names. These names include different mechanism versions and cohorts with original benchmark questions, fixed-fixture versions of original questions, and controlled synthetic extensions. The course 27 cells already include No Update, Full Rewrite and Selective Patch; they are not 27 candidate-versus-Patch comparisons. Mechanisms may be borrowed, but performance claims require matching task, fixture, tool, model, decoding, budget, product acceptance and a contemporaneous Patch control."
)
blue_para(
    "The offline 36-candidate audit reviewed 45 cohorts, 517 executed cells, 2555 valid judge slots and 445 existing product reviews. Six later rounds completed and one was interrupted; no candidate has met strict gains in normal completion and all required product properties together with TF and retention safeguards. This does not invalidate the course baseline or establish that an entire mechanism family is ineffective. Development and controlled synthetic results remain separate from the two independent validation batches required for the stronger research goal."
)
blue_para(
    "Some mechanisms remain research leads: sufficiency_feedback raised PE but completed 14/27 versus Patch 17/27; budget_feedback had local completion gains yet faulty code or numerical summaries; observed_contract completed 5/12 versus Patch 8/12 across two batches, with complete products at 0/12 in both arms. None is inserted into the frozen original Patch as a validated improvement."
)
blue_para(
    "Merge scope for this revision: the main branch's six offline CLI report tests were integrated; presentation scripts, slide-sync material and the dated speaking review were not imported. The old course scores, diagnostic outcomes and unknown charges remain unchanged. This report addendum and the research synthesis mark new or revised wording in blue. Sources: reports/course-research/plan-alignment-20261102.md; results/evaluation/current-branch-5b772ff-20261102/REPORT.md; main:d32e44b/submission/fanziyu-failure-review-20261031.md. No model calls or new benchmark runs were made for this merge."
)
sections.append("".join(current))
css = "body{font:16px/1.65 system-ui,sans-serif;color:#172333;background:#f4f6fa;margin:0}main{max-width:1060px;margin:auto;padding:35px;background:white}section{margin-bottom:44px}h1,h2{color:#102b46}h2{border-bottom:1px solid #cbd5e1;padding-bottom:12px}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:9px;border:1px solid #cbd5e1;text-align:left;vertical-align:top}th{background:#e8eef4}.scroll{overflow:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f7fa;padding:15px}p{overflow-wrap:anywhere}@media print{section{break-before:page}main{padding:0}}"
(R / "report-final.html").write_text(
    '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PE6203 Course Report</title><style>'
    + css
    + "</style><main>"
    + "".join(s + "</section>" for s in sections)
    + "</main></html>"
)


def footer(c, doc):
    c.setFont("Arial", 8)
    c.setFillColor(colors.HexColor("#56677c"))
    c.drawString(
        52, 28, "PE6203 Group Project 4 | Final offline audit | Historical scores retained"
    )
    c.drawRightString(543, 28, str(doc.page))


doc = SimpleDocTemplate(
    str(R / "PE6203-final-report.pdf"),
    pagesize=(595.28, 841.89),
    rightMargin=52,
    leftMargin=52,
    topMargin=48,
    bottomMargin=48,
    title="PE6203 Group Project4: Tool Harness Adaptation",
    author="PE6203 project group",
)
doc.build(flow, onFirstPage=footer, onLaterPages=footer)
print(R / "PE6203-final-report.pdf")

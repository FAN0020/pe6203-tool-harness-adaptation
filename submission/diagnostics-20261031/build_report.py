"""Render the independently verified diagnostic addendum offline."""

import html
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

D = Path(__file__).resolve().parent
a = json.loads((D / "audit.json").read_text())
for n, f in [("Arial", "Arial.ttf"), ("Arial-Bold", "Arial Bold.ttf")]:
    pdfmetrics.registerFont(TTFont(n, "/System/Library/Fonts/Supplemental/" + f))
pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold")
S = {
    k: ParagraphStyle(
        k,
        fontName=font,
        fontSize=size,
        leading=lead,
        spaceAfter=9,
        textColor=colors.HexColor("#172333"),
    )
    for k, font, size, lead in [
        ("body", "Arial", 10.5, 15),
        ("title", "Arial-Bold", 22, 27),
        ("h", "Arial-Bold", 13, 17),
        ("cell", "Arial", 9, 12),
    ]
}
flow = []
web = []


def p(s):
    flow.append(Paragraph(s, S["body"]))
    web.append("<p>" + s + "</p>")


def h(s):
    flow.append(Spacer(1, 6))
    flow.append(Paragraph(s, S["h"]))
    web.append("<h2>" + s + "</h2>")


def page(s):
    if flow:
        flow.append(PageBreak())
    flow.append(Paragraph(s, S["title"]))
    web.append("<h1>" + s + "</h1>")


def table(head, data, widths):
    vals = [[Paragraph(html.escape(str(c)), S["cell"]) for c in row] for row in [head] + data]
    t = Table(vals, colWidths=widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eff6")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c5d3e0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    flow.extend([t, Spacer(1, 10)])
    web.append(
        "<table><tr>"
        + "".join("<th>" + html.escape(str(c)) + "</th>" for c in head)
        + "</tr>"
        + "".join(
            "<tr>" + "".join("<td>" + html.escape(str(c)) + "</td>" for c in row) + "</tr>"
            for row in data
        )
        + "</table>"
    )


def ev(s):
    p('<font color="#53677D">Evidence: ' + html.escape(s) + "</font>")


page("Approved targeted diagnostics")
p("<b>PE6203 Group Project 4 | Addendum after explicit approval | 31 October 2026</b>")
p(
    "Four prespecified trajectories were executed once each, with five judge ratings per trajectory. This addendum supplements the frozen 27-cell benchmark without changing its scores or strategy ranking."
)
table(
    ["Condition", "Stage", "TF", "PE", "Calls / errors", "End status"],
    [
        ["U: missing fact", "Late", "10.0", "5.8", "27 / 9", "Output truncated"],
        ["U: complete fact", "Late", "10.0", "5.6", "5 / 1", "Completed"],
        ["O: rule reverted", "Middle", "9.8", "10.0", "4 / 0", "Completed"],
        ["O: rule retained", "Middle", "10.0", "7.8", "22 / 2", "Output truncated"],
    ],
    [111, 53, 44, 44, 95, 144],
)
h("Findings and their scope")
p(
    "<b>Under-update mechanism:</b> an injected omission produces eight calls without the newly required allow_variables parameter; all eight are rejected. The complete snapshot has zero such rejections. This confirms a local mechanism under controlled fault injection, not a natural failure of original Selective Patch."
)
p(
    "<b>Extra-rule comparison:</b> retaining one historical evaluate rule coincides with more calls, lower PE and truncation. The rollback also has slightly lower TF. With one stochastic execution per arm, this is suggestive evidence, not proof of general harm or a superior strategy."
)
h("Cost and stopping")
p(
    "Total recorded API cost: <b>$"
    + format(a["known_usd"], ".8f")
    + "</b>. There are no unknown request charges in this cohort. Execution and judging took <b>"
    + format(a["elapsed_execution_seconds"], ".3f")
    + " seconds (2.68 minutes)</b>, excluding preparation, analysis and packaging. No updater-model calls were made."
)
p(
    "All four approved trajectories are terminal. No repetitions, new candidates, Netlify deployment or larger matrix were started. ECS is not defined for this single-stage two-condition diagnostic."
)
ev("audit.json; plan.json; raw/cells/{condition}/run/{raw_trace.json,EVAL/133.json,result.json}")

page("U: missing parameter knowledge")
h("Exact intervention")
p(
    "Task 133, Late. The control uses the exact archived main Selective Patch snapshot. The injected arm removes only parameters.properties.allow_variables and its entry in parameters.required for math-mcp::validate_syntax. All other knowledge and the live tool schema stay identical. This deliberately bypasses the original updater's correct output."
)
h("Observed failure and recovery")
p(
    "The first injected validation call uses <b>2 + 3 * (4 - 1) / 2</b> without allow_variables. The server returns: <i>validate_syntax requires allow_variables to be explicitly provided as a boolean</i>. All eight validation calls in rounds 1-3 omit the field and receive this rejection. The agent later switches to evaluate, makes 17 evaluation calls in total, and reaches the output limit."
)
p(
    "The control supplies the field in both validation calls. Its five calls include a separate batch_evaluate call that returns an upstream implementation error: <i>this.toolHandlers.handleBatchEvaluate is not a function</i>. Its agent loop finishes normally."
)
table(
    ["Measure", "Injected omission", "Complete snapshot"],
    [
        ["Missing-field rejections", "8", "0"],
        ["Calls / agent rounds", "27 / 7", "5 / 3"],
        ["PE ratings", "5, 6, 6, 5, 7", "5, 5, 5, 5, 8"],
        ["Mean TF / PE", "10.0 / 5.8", "10.0 / 5.6"],
    ],
    [183, 154, 154],
)
h("Judge error and causal limit")
p(
    "Four control judge rationales incorrectly say batch_evaluate is outside the available tools. It appears in the knowledge, live metadata and model-facing tool list. The implementation does fail. Whether distinct validation/evaluation checks are redundant is also debatable. Every original rating remains unchanged."
)
p(
    "<b>Confirmed:</b> absent arguments directly cause the eight local rejections. <b>Not established:</b> a natural Patch under-update, prevalence, or a PE benefit from the correction. PE is 0.2 lower in the control despite fewer errors and normal completion."
)
ev(
    "exact-knowledge-diffs.json; under_omitted/run/events.jsonl; under_complete/run/{knowledge.json,environment-metadata.json,raw_trace.json,judge-attempts/}"
)

page("O: one-rule rollback and limits")
h("Exact rule under test")
p(
    "Task 133, Middle. One arm replays the historical linked_notes snapshot. The rollback changes only math-mcp::evaluate.usage_rules to []. Three other archived guideline-rule changes remain identical."
)
p(
    "<i>validate_syntax now accepts optional detailed and allow_variables flags; evaluate's validate_only remains a separate syntax-only path, so choose based on whether evaluation is also wanted.</i>"
)
table(
    ["Measure", "Rule retained", "Rule reverted"],
    [
        ["All calls / tool errors", "22 / 2", "4 / 0"],
        ["validate_syntax / evaluate", "9 / 11", "2 / 1"],
        ["evaluate in later rounds than first validation", "10", "0"],
        ["Mean TF / PE", "10.0 / 7.8", "9.8 / 10.0"],
        ["End status", "Output truncated", "Completed"],
    ],
    [231, 130, 130],
)
p(
    "The retained-rule run adds distinct security, arithmetic and numerical probes; not every extra call is necessarily redundant. Its two evaluation errors concern unsupported lambda syntax and undefined variables. The rollback performs four calls in its first round and then answers."
)
p(
    "<b>Suggestive:</b> a single-field comparison is stronger than the historical four-field comparison, but one execution per arm and no provider seed leave stochastic variation unresolved. evaluate is related to the validator, so unchanged metadata does not establish unrelated knowledge. This is a historical variant, not the main method."
)
h("Fairness, preservation and course status")
p(
    "Archived runtime hashes match the main run: Python 3.12.12, Node v24.13.0 and unchanged Middle/Late catalogs. Settings remain DeepSeek v4.1 Flash through OpenRouter, temperature 0, 4096 tokens, 12 rounds, 900 seconds, and the same retry and five-slot judge protocol. All 20 ratings were independently recalculated."
)
p(
    "All 10,959 previously packaged evidence files retain their hashes. The six negative description-rollback diagnostics and main PE 9.1111 remain intact. The strict gap for natural original-Patch under-update and genuinely unrelated over-update failures remains. Course acceptance of a controlled fault case needs justification; no more experiments are proposed automatically."
)
ev(
    "driver.py; audit.py; plan.json; exact-knowledge-diffs.json; audit.json; package-verification.json"
)


def footer(c, d):
    c.setFont("Arial", 8)
    c.setFillColor(colors.HexColor("#53677D"))
    c.drawString(52, 28, "PE6203 | Controlled diagnostics | Main benchmark unchanged")
    c.drawRightString(543, 28, str(d.page))


SimpleDocTemplate(
    str(D / "PE6203-diagnostic-addendum.pdf"),
    pagesize=(595, 842),
    leftMargin=52,
    rightMargin=52,
    topMargin=48,
    bottomMargin=46,
).build(flow, onFirstPage=footer, onLaterPages=footer)
style = "body{max-width:1050px;margin:32px auto;padding:24px;font:17px/1.65 system-ui;color:#172333}h1,h2{color:#245071}h1{margin-top:40px}table{width:100%;border-collapse:collapse}td,th{border:1px solid #c5d3e0;padding:9px;text-align:left;vertical-align:top}th{background:#e8eff6}a{color:#15568c}"
links = '<p><a href="PE6203-diagnostic-addendum.pdf">PDF addendum</a> | <a href="audit.json">Independent audit</a> | <a href="exact-knowledge-diffs.json">Exact differences</a> | <a href="../PE6203-diagnostics-20261031.zip">Reproducibility supplement</a> | <a href="../index.html">Frozen main report</a></p>'
(D / "index.html").write_text(
    '<!doctype html><html lang="en"><meta charset="utf-8"><title>PE6203 approved diagnostics</title><style>'
    + style
    + "</style>"
    + links
    + "".join(web)
    + "</html>"
)
print("Created diagnostic addendum PDF and HTML.")

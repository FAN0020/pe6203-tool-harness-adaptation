"""Recompute chart payload facts; preserve explicit post-hoc human claim judgments."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = (
    ROOT
    / "results/evidence/unified-reaudit-20261102/historical-products/selective-search-confirmation-r1-20261031"
)
NOTES = {
    "early-selective_patch-r0": (
        "pass",
        "Source figures and totals match; qualitative close/top-market wording is imprecise, not used as a numeric failure.",
    ),
    "early-selective_patch-r1": (
        "fail",
        "Claims steady month-on-month growth after February, omitting July2.3 to August2.2 decline.",
    ),
    "early-selective_patch-r2": (
        "pass",
        "Reported figures and gaps correct; fabricated zeroes classified separately as chart failure.",
    ),
    "early-sufficiency_feedback-r0": (
        "fail",
        "Claims February only dip, but August also declines.",
    ),
    "early-sufficiency_feedback-r1": (
        "fail",
        "Claims steady climb after February despite August decline.",
    ),
    "early-sufficiency_feedback-r2": (
        "pass",
        "Both dips, source values, gaps and units correctly described.",
    ),
    "middle-selective_patch-r0": (
        "fail",
        "Calls Jan-to-Dec change year-over-year; no prior-year comparison supplied.",
    ),
    "middle-selective_patch-r1": ("fail", "Labels2.5,2.7,3.0,3.5 Q4;2.5 is September outside Q4."),
    "middle-selective_patch-r2": ("pass", "Concise source-consistent trend and category summary."),
    "middle-sufficiency_feedback-r0": (
        "pass",
        "Source values and category gaps correct; fabricated zeroes recorded separately.",
    ),
    "middle-sufficiency_feedback-r1": (
        "pass",
        "Converted values and gaps correct; plateau loosely describes disclosed2.3 to2.2 softspot. Seasonal cause unverified, not certified.",
    ),
    "middle-sufficiency_feedback-r2": (
        "pass",
        "Values,category totals,ratios match; seasonal explanation explicitly speculative.",
    ),
    "late-selective_patch-r0": (
        "pass",
        "Q4total9.2 and category gaps correct; speculative competition explanations not certified.",
    ),
    "late-selective_patch-r1": ("pass", "Source figures and both dips correctly described."),
    "late-selective_patch-r2": (
        "fail",
        "Annual23.4 vs25.4;category total24.3 vs28.1;widest gap Clothing1.5 not Electronics1.4.",
    ),
    "late-sufficiency_feedback-r0": (
        "fail",
        "Claims map labeled millions but returned map has no unit label.",
    ),
    "late-sufficiency_feedback-r1": (
        "fail",
        "Q4 sequence includes September2.5;Q4 starts October2.7.",
    ),
    "late-sufficiency_feedback-r2": (
        "pass",
        "Source values and comparisons correct; map unit omission is chart failure.",
    ),
}


def main():
    for f in sorted(P.glob("task235-*.json")):
        d = json.loads(f.read_text())
        last = {}
        for c in d["calls"]:
            if c["tool"].startswith("generate_") and not c["result"].get("isError"):
                last[c["tool"].split("__")[0]] = c
        assert set(last) == {
            "generate_district_map",
            "generate_area_chart",
            "generate_column_chart",
        }
        specs = {k: c["result"]["meta"]["spec"] for k, c in last.items()}
        assert all(s["data"] == json.loads(last[k]["arguments"])["data"] for k, s in specs.items())
        m = specs["generate_district_map"]
        vals = m["data"]["subdistricts"]
        assert [float(t["dataValue"]) for t in vals[:5]] in [
            [15.8, 12.3, 9.7, 8.4, 7.2],
            [1580, 1230, 970, 840, 720],
        ]
        assert [t["name"] for t in vals[:5]] == ["广东省", "江苏省", "浙江省", "山东省", "北京市"]
        defects = []
        if len(vals) != 5:
            defects.append("Unreported provinces assigned fabricated zero values.")
        if not (m["data"].get("dataValueUnit") or m.get("dataValueUnit")):
            defects.append("Returned map has no monetary unit label.")
        for kind, expected in [
            ("generate_area_chart", [1.2, 1.1, 1.4, 1.6, 1.8, 2.1, 2.3, 2.2, 2.5, 2.7, 3, 3.5]),
            ("generate_column_chart", [6.2, 4.8, 4.5, 3.9, 5.1, 3.6]),
        ]:
            a = specs[kind]
            scale = 1 if "百万元" in a["axisYTitle"] else 100 if "万元" in a["axisYTitle"] else None
            assert scale and [round(v["value"] / scale, 6) for v in a["data"]] == expected
        summary, note = NOTES[f.stem.removeprefix("task235-")]
        props = {"charts": "fail" if defects else "pass", "summary": summary}
        r = {
            "cell_id": f.stem,
            "task_id": 235,
            "input_sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
            "trace_sha256": d["trace_sha256"],
            "properties": props,
            "core_pass": all(v == "pass" for v in props.values()),
            "evidence": {
                "charts": defects
                or ["All3 returned types,data,ordering,labels,units and mappings match."],
                "summary": note,
            },
            "review_phase": "supplemental_posthoc_scores_exposed",
            "limitations": [
                "Rendering unverified,not a required property.",
                "Same coordinator;old labels/scores exposed.",
                "Final corrected artifact assessed;all earlier calls retained.",
            ],
            "review_source": "scripts/review_confirmation_charts.py;manual final claim judgments plus deterministic data checks",
        }
        (P / "reviews" / f.name).write_text(json.dumps(r, ensure_ascii=False, indent=2) + "\n")
    print("18 chart reviews recomputed")


if __name__ == "__main__":
    main()

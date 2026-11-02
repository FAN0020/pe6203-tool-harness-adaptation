"""Supplement missing historical chart checks; no re-execution or old-label edits."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "results/evidence/unified-reaudit-20261102/historical-products"
CASES = {
    "selective-search-confirmation-r2-20261031": {
        "task235-early-budget_feedback-r0": (
            "pass",
            "Source figures,53.4total,37.8top3,Q4 and category gaps correct; both dips named.",
        ),
        "task235-middle-selective_patch-r0": (
            "fail",
            "Annual23.4 should be25.4; February-only dip omits August; Q4 percentage therefore wrong; unreported provinces treated as zero.",
        ),
    },
    "selective-search-confirmation-r3-20261031": {
        "task235-early-budget_feedback-r0": (
            "pass",
            "Reported values,trends and category gaps match.",
        ),
        "task235-middle-selective_patch-r0": (
            "pass",
            "Source-consistent figures and category ordering; seasonal explanation marked as suggestion.",
        ),
    },
    "selective-search-v2.1-development-20261031": {
        "task235-late-selective_patch-r0": (
            "pass",
            "Source values, both dips and category gaps correct.",
        ),
        "task235-late-sufficiency_feedback-r0": (
            "pass",
            "Source values,both dips and category ordering correct.",
        ),
        "task235-middle-selective_patch-r0": (
            "pass",
            "Source values,both dips and category ordering correct; speculative seasonal explanation not certified.",
        ),
        "task235-middle-sufficiency_feedback-r0": (
            "fail",
            "Annual24.4 should be25.4; steady climb ignores August; year-over-year unsupported by one-year data.",
        ),
    },
}


def main():
    for cohort, notes in CASES.items():
        for cell, (summary, note) in notes.items():
            f = P / cohort / (cell + ".json")
            d = json.loads(f.read_text())
            calls = {
                c["tool"].split("__")[0]: c
                for c in d["calls"]
                if c["tool"].startswith("generate_") and not c["result"].get("isError")
            }
            assert set(calls) == {
                "generate_district_map",
                "generate_area_chart",
                "generate_column_chart",
            }
            specs = {k: c["result"]["meta"]["spec"] for k, c in calls.items()}
            assert all(
                v["data"] == json.loads(calls[k]["arguments"])["data"] for k, v in specs.items()
            )
            m = specs["generate_district_map"]
            values = m["data"]["subdistricts"]
            defects = []
            assert [float(v["dataValue"]) for v in values[:5]] == [15.8, 12.3, 9.7, 8.4, 7.2]
            assert [v["name"] for v in values[:5]] == [
                "广东省",
                "江苏省",
                "浙江省",
                "山东省",
                "北京市",
            ]
            if len(values) != 5:
                defects.append("Unreported provinces assigned fabricated zeroes.")
            if not (m["data"].get("dataValueUnit") or m.get("dataValueUnit")):
                defects.append("Map monetary unit absent.")
            for kind, expected in [
                ("generate_area_chart", [1.2, 1.1, 1.4, 1.6, 1.8, 2.1, 2.3, 2.2, 2.5, 2.7, 3, 3.5]),
                ("generate_column_chart", [6.2, 4.8, 4.5, 3.9, 5.1, 3.6]),
            ]:
                s = specs[kind]
                assert [v["value"] for v in s["data"]] == expected and "百万元" in s["axisYTitle"]
            assert [x["time"] for x in specs["generate_area_chart"]["data"]] == [
                str(i) + "月" for i in range(1, 13)
            ]
            assert [
                x["group"].removesuffix("省") for x in specs["generate_column_chart"]["data"]
            ] == ["广东", "江苏"] * 3
            cats = [x["category"] for x in specs["generate_column_chart"]["data"]]
            assert cats in [
                ["电子产品"] * 2 + ["家用电器"] * 2 + ["服装"] * 2,
                ["电子数码"] * 2 + ["家用电器"] * 2 + ["服装"] * 2,
            ]
            props = {"charts": "fail" if defects else "pass", "summary": summary}
            r = {
                "cell_id": cell,
                "task_id": 235,
                "input_sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
                "trace_sha256": d["trace_sha256"],
                "properties": props,
                "core_pass": all(x == "pass" for x in props.values()),
                "evidence": {
                    "charts": defects
                    or ["All three returned data,type,labels,units and ordering match."],
                    "summary": note,
                },
                "review_phase": "supplemental_posthoc_scores_exposed",
                "review_source": "scripts/review_reaudit_gap_charts.py",
                "limitations": [
                    "Same coordinator; original scores exposed.",
                    "Rendering unverified and not required.",
                    "Old conclusions unchanged; not independent validation.",
                ],
            }
            (f.parent / "reviews" / f.name).write_text(
                json.dumps(r, ensure_ascii=False, indent=2) + "\n"
            )
    print("8 supplemental chart reviews")


if __name__ == "__main__":
    main()

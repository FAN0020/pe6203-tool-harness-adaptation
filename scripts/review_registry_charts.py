"""Post-hoc product checks for remaining registry chart runs; no model calls."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "results/evidence/unified-reaudit-20261102/historical-products"
CASES = {
    "selective-search-v1.1-development-20261031": {
        "task235-late-delta_notes-r0": ("fail", "OnlyFebruarydip contradictsJuly2.3→August2.2."),
        "task235-late-feedback_notes-r0": (
            "pass",
            "Bothdips,categoryvalues and relativeclothing42percentgapcorrect;renderingnotverified.",
        ),
        "task235-late-linked_notes-r0": (
            "pass",
            "Values,bothdips andcategorycomparisons match;missingmapunit capturedseparately.",
        ),
        "task235-late-selective_patch-r0": (
            "fail",
            "Widestgap claimedElectronics1.4, butClothing1.5 islarger.",
        ),
        "task235-middle-delta_notes-r0": (
            "fail",
            "HomeappliancescalledJiangsu weakestrelative segment;it isclosesttoGuangdong,clothingisweakestrelative.OnlyAugustdip excludesFebruary despiteearlierminimummention.",
        ),
        "task235-middle-feedback_notes-r0": (
            "fail",
            "ClaimsElectronicshaslargestgap;Clothing1.5>Electronics1.4.",
        ),
        "task235-middle-linked_notes-r0": (
            "fail",
            "Claimsmapunitmillions butreturnedmaphasnounit;numericvaluesotherwise match.",
        ),
        "task235-middle-selective_patch-r0": (
            "fail",
            "Claimsmapunitmillions butreturnedmaphasnounit;comparisonsandbothdipsotherwise match.",
        ),
    },
    "selective-search-v2.1-development-20261031": {
        "task235-late-sufficiency_notes-r0": (
            "fail",
            "SteadyclimbafterFebruaryignoresAugustdecline.",
        ),
        "task235-middle-sufficiency_notes-r0": (
            "fail",
            "SteadygrowththroughtheyearignoresAugustdecline.",
        ),
    },
    "registry-development": {
        "cell-002": (
            "fail",
            "OnlyFebruarydip contradictsAugustdecline,thoughAugustcalledplateau.53.4/37.8totalsandcategorysums otherwise match.",
        ),
        "cell-003": (
            "fail",
            "Annualmonthlytotal23.4 should25.4;HomeAppliancesnotlaggardinJiangsu(3.9>Clothing3.6).",
        ),
    },
}


def main():
    for cohort, cases in CASES.items():
        for cell, (summary, note) in cases.items():
            p = P / cohort / (cell + ".json")
            d = json.loads(p.read_text())
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
                s["data"] == json.loads(calls[k]["arguments"])["data"] for k, s in specs.items()
            )
            m = specs["generate_district_map"]["data"]
            unit = m.get("dataValueUnit")
            scale = 100 if unit == "万元" else 1
            vals = m["subdistricts"]
            defects = []
            assert [round(float(v["dataValue"]) / scale, 6) for v in vals[:5]] == [
                15.8,
                12.3,
                9.7,
                8.4,
                7.2,
            ]
            assert [v["name"] for v in vals[:5]] == [
                "广东省",
                "江苏省",
                "浙江省",
                "山东省",
                "北京市",
            ]
            if len(vals) != 5:
                defects.append("Unreportedprovinces assigned inventedvalues.")
            if not unit:
                defects.append("Returnedmap lacks monetaryunit.")
            a = specs["generate_area_chart"]
            c = specs["generate_column_chart"]
            assert [v["value"] for v in a["data"]] == [
                1.2,
                1.1,
                1.4,
                1.6,
                1.8,
                2.1,
                2.3,
                2.2,
                2.5,
                2.7,
                3,
                3.5,
            ]
            assert [v["time"] for v in a["data"]] in [
                [f"{i}月" for i in range(1, 13)],
                [
                    "Jan",
                    "Feb",
                    "Mar",
                    "Apr",
                    "May",
                    "Jun",
                    "Jul",
                    "Aug",
                    "Sep",
                    "Oct",
                    "Nov",
                    "Dec",
                ],
            ]
            assert [v["value"] for v in c["data"]] == [6.2, 4.8, 4.5, 3.9, 5.1, 3.6]
            assert "百万元" in a["axisYTitle"] and "百万元" in c["axisYTitle"]
            categories = [v["category"] for v in c["data"]]
            assert categories in [
                ["电子产品"] * 2 + ["家用电器"] * 2 + ["服装"] * 2,
                ["Electronics"] * 2 + ["Home Appliances"] * 2 + ["Clothing"] * 2,
            ]
            assert [v["group"].removesuffix("省") for v in c["data"]] in [
                ["广东", "江苏"] * 3,
                ["Guangdong", "Jiangsu"] * 3,
            ]
            props = {"charts": "fail" if defects else "pass", "summary": summary}
            r = {
                "cell_id": cell,
                "cohort": d["cohort"],
                "task_id": 235,
                "input_sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                "trace_sha256": d["trace_sha256"],
                "properties": props,
                "core_pass": all(v == "pass" for v in props.values()),
                "evidence": {
                    "charts": defects
                    or ["All3returnedtypes,data,ordering,units andcategory/provincemappingsmatch."],
                    "summary": note,
                },
                "review_phase": "supplemental_posthoc_scores_exposed",
                "review_source": "scripts/review_registry_charts.py",
                "limitations": [
                    "Posthoc samecoordinator,not independentvalidation.",
                    "Rendering unverified,not required.",
                    "Originalscoresandconclusionspreserved.",
                ],
            }
            (p.parent / "reviews" / p.name).write_text(
                json.dumps(r, ensure_ascii=False, indent=2) + "\n"
            )
    print("12 remaining registry/SP chart reviews completed")


if __name__ == "__main__":
    main()

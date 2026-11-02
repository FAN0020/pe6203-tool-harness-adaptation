"""Offline factual product checks; no actor feedback, execution or API calls.

Implements the data/source criteria frozen before generation. These checks do
not replace the official rubric and do not certify safety or rendered visuals.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from collections import Counter
from pathlib import Path

from pe6203.benchmark import read_json, write_json


def text_objects(result):
    for item in result.get("content", []):
        if item.get("type") == "text":
            try:
                yield json.loads(item["text"])
            except (ValueError, KeyError):
                pass


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def named(text, aliases):
    text = str(text).lower()
    return next((key for key, terms in aliases.items() if any(t in text for t in terms)), None)


def numeric_scale(actual, expected):
    if len(actual) != len(expected):
        return None
    for scale in (1, 100, 1000000):
        if all(abs(float(a) / scale - e) < 1e-7 for a, e in zip(actual, expected, strict=True)):
            return scale
    return None


def chart_check(calls):
    provinces = {
        "gd": ["广东", "guangdong"],
        "js": ["江苏", "jiangsu"],
        "zj": ["浙江", "zhejiang"],
        "sd": ["山东", "shandong"],
        "bj": ["北京", "beijing"],
    }
    categories = {
        "e": ["电子", "electronics"],
        "h": ["家用电器", "家电", "home appliances", "home appliance"],
        "c": ["服装", "clothing"],
    }
    expected_map = {"gd": 15.8, "js": 12.3, "zj": 9.7, "sd": 8.4, "bj": 7.2}
    expected_columns = {
        ("gd", "e"): 6.2,
        ("js", "e"): 4.8,
        ("gd", "h"): 4.5,
        ("js", "h"): 3.9,
        ("gd", "c"): 5.1,
        ("js", "c"): 3.6,
    }
    result = {}
    for call in calls:
        if call["error"]:
            continue
        args = call["arguments"]
        name = call["name"]
        try:
            if name == "generate_district_map":
                items = args["data"]["subdistricts"]
                actual = {named(d["name"], provinces): float(d["dataValue"]) for d in items}
                scale = (
                    numeric_scale([actual[k] for k in expected_map], list(expected_map.values()))
                    if set(actual) == set(expected_map)
                    else None
                )
                result["map"] = {
                    "province_values_match": scale is not None,
                    "scale": scale,
                    "unit": args["data"].get("dataValueUnit"),
                }
            elif name == "generate_area_chart":
                items = args["data"]
                scale = numeric_scale(
                    [d["value"] for d in items],
                    [1.2, 1.1, 1.4, 1.6, 1.8, 2.1, 2.3, 2.2, 2.5, 2.7, 3, 3.5],
                )
                result["area"] = {
                    "ordered_12_values_match": scale is not None,
                    "scale": scale,
                    "month_labels": [d.get("time") for d in items],
                    "axis_unit": args.get("axisYTitle"),
                }
            elif name == "generate_column_chart":
                items = args["data"]
                actual = {
                    (
                        named(d.get("group", ""), provinces),
                        named(d.get("category", ""), categories),
                    ): float(d["value"])
                    for d in items
                }
                scale = (
                    numeric_scale(
                        [actual[k] for k in expected_columns], list(expected_columns.values())
                    )
                    if set(actual) == set(expected_columns)
                    else None
                )
                result["column"] = {
                    "region_category_values_match": scale is not None,
                    "scale": scale,
                    "axis_unit": args.get("axisYTitle"),
                }
        except (KeyError, TypeError, ValueError) as exc:
            result[name] = {"check": "unable_to_parse", "error_type": type(exc).__name__}
    result["three_chart_data_checks_match"] = all(
        result.get(k, {}).get(field, False)
        for k, field in [
            ("map", "province_values_match"),
            ("area", "ordered_12_values_match"),
            ("column", "region_category_values_match"),
        ]
    )
    result["rendering"] = (
        "not tested; tool-returned specifications are not rendered dashboard proof"
    )
    return result


def card_check(calls, answer):
    images = []
    daily = []
    cards = []
    for call in calls:
        if call["error"]:
            continue
        if call["name"] == "get_card_image":
            for item in call["result"].get("content", []):
                if item.get("type") == "image":
                    try:
                        data = base64.b64decode(item["data"], validate=True)
                        images.append(
                            {
                                "bytes": len(data),
                                "sha256": hashlib.sha256(data).hexdigest(),
                                "mime": item.get("mimeType"),
                            }
                        )
                    except (ValueError, KeyError):
                        pass
        for obj in text_objects(call["result"]):
            if call["name"] in ("search_cards", "get_card_by_id"):
                cards += [node for node in walk(obj) if str(node.get("id")) == "89631139"]
            if "daily" in call["name"] or call["arguments"].get("daily") is True:
                dates = [n["date"] for n in walk(obj) if "date" in n]
                questions = [n for n in walk(obj) if "questionFrontendId" in n and "title" in n]
                for q in questions:
                    daily.append(
                        {
                            "id": q["questionFrontendId"],
                            "title": q["title"],
                            "dates": list(dict.fromkeys(dates)),
                            "id_in_answer": str(q["questionFrontendId"]) in answer,
                            "title_in_answer": q["title"].lower() in answer.lower(),
                        }
                    )
    return {
        "blue_eyes_card_retrieved": bool(cards),
        "image_bytes_retrieved": images,
        "daily_challenge_observations": daily,
        "daily_answer_matches_observed_id_title": any(
            d["id_in_answer"] and d["title_in_answer"] for d in daily
        ),
        "scope": "Image retrieval bytes and answer/source consistency; not browser rendering or full answer verification",
    }


def main(root, out):
    plan = read_json(root / "plan.json")
    rows = []
    for cell in plan["cell_order"]:
        p = root / "runs" / cell["id"]
        if not (p / "result.json").exists():
            continue
        result = read_json(p / "result.json")
        trace = read_json(p / "raw_trace.json")
        calls = []
        for event in trace["events"]:
            if event.get("type") != "tool_result":
                continue
            route = result["model_tool_routes"].get(event["call"]["function"]["name"], {})
            try:
                args = json.loads(event["call"]["function"]["arguments"])
            except ValueError:
                args = {}
            calls.append(
                {
                    "name": route.get("tool_name"),
                    "arguments": args,
                    "result": event["result"],
                    "error": bool(event["result"].get("isError")),
                }
            )
        if cell["task_id"] == 235:
            rows.append({"cell": cell["id"], "task_id": 235, "checks": chart_check(calls)})
        elif cell["task_id"] == 90:
            rows.append(
                {"cell": cell["id"], "task_id": 90, "checks": card_check(calls, trace["answer"])}
            )
    write_json(
        out,
        {
            "scope": "Post-generation offline implementation of frozen source/data criteria; no new success metric or actor feedback",
            "results": rows,
        },
    )
    print(
        json.dumps(
            {
                "rows": len(rows),
                "tasks": dict(Counter(r["task_id"] for r in rows)),
                "chart_numeric_matches": sum(
                    r["checks"].get("three_chart_data_checks_match", False) for r in rows
                ),
                "daily_source_matches": sum(
                    r["checks"].get("daily_answer_matches_observed_id_title", False) for r in rows
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.input, args.output)

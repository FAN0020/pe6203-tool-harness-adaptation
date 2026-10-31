"""Extract observable card, image and daily facts from raw traces; no model/judge calls."""

import base64
import json
from pathlib import Path

from raw_cell_verifier import archive_files, sha

HERE = Path(__file__).resolve().parent


def main():
    files, manifest = archive_files(HERE)
    prefix = manifest["prefix"] + "/"

    def read(name):
        return json.loads(files[prefix + name])

    rows = []
    for cell in read("plan.json")["cells"]:
        trace = read(f"cells/{cell['id']}/run/raw_trace.json")
        events = [e for e in trace["events"] if e["type"] == "tool_result"]
        answer = trace.get("answer") or ""
        cards, daily, images, errors, calls = [], [], [], [], []
        for event in events:
            fn = event["call"]["function"]
            name = fn["name"].rsplit("__", 1)[0]
            args = json.loads(fn["arguments"])
            payload = event["result"]
            calls.append({"round": event["round"], "tool": name, "arguments": args})
            if payload.get("isError"):
                errors.append(
                    {"round": event["round"], "tool": name, "result": payload}
                )
            for content in payload.get("content", []):
                if content.get("type") == "image":
                    raw = base64.b64decode(content["data"], validate=True)
                    images.append(
                        {
                            "round": event["round"],
                            "tool": name,
                            "requested_id": str(args.get("id", "")),
                            "mime_type": content.get("mimeType"),
                            "bytes": len(raw),
                            "sha256": sha(raw),
                            "jpeg_markers_valid": raw[:2] == b"\xff\xd8"
                            and raw[-2:] == b"\xff\xd9",
                        }
                    )
                if content.get("type") != "text":
                    continue
                try:
                    obj = json.loads(content["text"])
                except (ValueError, TypeError):
                    continue
                if not isinstance(obj, dict):
                    continue
                if name in ("search_cards", "get_card_by_id"):
                    for card in obj.get("result", []):
                        if not isinstance(card, dict):
                            continue
                        if "青眼白龙" in (
                            card.get("cn_name"), card.get("sc_name"), card.get("md_name")
                        ) or card.get("en_name") == "Blue-Eyes White Dragon":
                            cards.append(
                                {
                                    "round": event["round"],
                                    "tool": name,
                                    "id": str(card.get("id")),
                                    "names": {
                                        k: card.get(k)
                                        for k in ("cn_name", "sc_name", "jp_name", "en_name")
                                    },
                                    "data": card.get("data"),
                                    "text": card.get("text"),
                                }
                            )
                if name in ("get_daily_challenge", "get_problem") and "date" in obj:
                    problem = obj.get("problem", {})
                    question = problem.get("question", {})
                    if not question:
                        continue
                    daily.append(
                        {
                            "round": event["round"],
                            "tool": name,
                            "outer_date": obj["date"],
                            "service_date": problem.get("date"),
                            "title": question.get("title"),
                            "frontend_id": question.get("questionFrontendId"),
                            "slug": question.get("titleSlug"),
                            "link": problem.get("link"),
                            "title_in_final_answer": question.get("title", "") in answer,
                            "id_in_final_answer": str(question.get("questionFrontendId"))
                            in answer,
                            "service_date_in_final_answer": str(problem.get("date")) in answer,
                        }
                    )
        target_ids = {c["id"] for c in cards}
        for img in images:
            img["id_matches_requested_card_record"] = img["requested_id"] in target_ids
        rows.append(
            {
                "cell_id": cell["id"],
                "stage": cell["version"],
                "strategy": cell["strategy"],
                "calls": calls,
                "errors": errors,
                "card_records": cards,
                "images": images,
                "daily_observations": daily,
                "final_answer": answer,
                "caution": "String matches and JPEG markers are observable facts, not a complete semantic or rendering evaluation.",
            }
        )
    print(
        json.dumps(
            {
                "new_model_calls": 0,
                "historical_scores_changed": False,
                "archive_sha256": manifest["archive_sha256"],
                "cells": rows,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

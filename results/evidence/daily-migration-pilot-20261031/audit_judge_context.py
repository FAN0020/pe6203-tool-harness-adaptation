"""Audit what the unchanged upstream 1000-character truncation actually sent to judges."""

import json
from pathlib import Path

from raw_cell_verifier import archive_files, sha

HERE = Path(__file__).resolve().parent


def observations(files, prefix, cell_id):
    trace = json.loads(files[prefix + f"cells/{cell_id}/run/raw_trace.json"])
    prompt = files[prefix + f"cells/{cell_id}/run/judge-original-prompt-1.txt"].decode()
    rows = []
    for event in trace["events"]:
        if event["type"] != "tool_result":
            continue
        raw = json.dumps(event["result"], ensure_ascii=False)
        visible = raw[:1000] + "..." if len(raw) > 1000 else raw
        assert visible in prompt, "Reconstructed tool observation differs from saved judge prompt"
        rows.append(
            {
                "round": event["round"],
                "tool": event["call"]["function"]["name"].rsplit("__", 1)[0],
                "raw_characters": len(raw),
                "judge_characters": len(visible),
                "truncated": len(raw) > 1000,
                "visible_sha256": sha(visible.encode()),
                "raw": raw,
                "visible": visible,
            }
        )
    return rows


def main():
    files, manifest = archive_files(HERE)
    prefix = manifest["prefix"] + "/"
    cells = []
    for n in range(1, 13):
        cell = f"cell-{n:03d}"
        rows = observations(files, prefix, cell)
        selected = []
        for row in rows:
            if row["tool"] not in ("get_problem", "get_daily_challenge"):
                continue
            selected.append(
                {
                    "round": row["round"],
                    "tool": row["tool"],
                    "fields": {
                        marker: {
                            "in_raw_observation": marker in row["raw"],
                            "in_judge_observation": marker in row["visible"],
                        }
                        for marker in ("questionFrontendId", "difficulty", "totalAcceptedRaw", "hints")
                    },
                }
            )
        cells.append(
            {
                "cell_id": cell,
                "observations": [
                    {k: v for k, v in row.items() if k not in ("raw", "visible")}
                    for row in rows
                ],
                "daily_field_visibility": selected,
            }
        )
    old = HERE.parent / "routing-fault-check-20261031"
    old_files, old_manifest = archive_files(old)
    old_rows = observations(old_files, old_manifest["prefix"] + "/", "cell-001")
    routing = []
    for row in old_rows:
        if row["round"] not in (2, 4) or row["tool"] != "get_symbols_batch":
            continue
        routing.append(
            {
                "round": row["round"],
                "tool": row["tool"],
                "raw_characters": row["raw_characters"],
                "judge_characters": row["judge_characters"],
                "markers": {
                    marker: {"in_raw": marker in row["raw"], "in_judge": marker in row["visible"]}
                    for marker in ("Form", "Section", "Picker", "Slider", "NavigationStack", "onDelete")
                },
            }
        )
    assert len(routing) == 2
    print(json.dumps({
        "new_model_calls": 0,
        "historical_scores_changed": False,
        "protocol": "Pinned upstream truncate_tool_content preserves first1000 characters of each tool message and appends...; intermediate assistant content is removed. Both facts describe the unchanged benchmark formatter.",
        "proof": "Every reconstructed visible tool observation occurs verbatim in saved original judge prompt1, for all12 current cells and the prior routing-fault cell.",
        "cells": cells,
        "prior_routing_case": routing,
        "interpretation": "A fact present in raw tool data but cut from the judge's observation is a protocol evidence-visibility limitation. Do not describe that alone as the judge overlooking evidence it was actually shown. Retry-count mistakes remain separately checkable because tool calls are preserved.",
        "prior_report_erratum": "The prior routing report's missing-material criticisms should be qualified by these visibility checks. Original scores and raw records remain unchanged; this is an explicit interpretation addendum, not retroactive rescoring.",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

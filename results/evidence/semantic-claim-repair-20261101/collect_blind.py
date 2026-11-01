"""Project current raw outputs without method or judge labels; never updater input."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
RAW = ROOT / "results/raw/semantic-claim-repair-pilot-20261101-exec"
state = json.loads((RAW / "experiment.json").read_text())
mapping = json.loads((HERE / "blind-map.json").read_text())
(HERE / "blind-inputs").mkdir(exist_ok=True)
for rid, cid in mapping.items():
    if state["cells"].get(cid, {}).get("status") != "evaluated":
        continue
    trace = json.loads((RAW / "cells" / cid / "run/raw_trace.json").read_text())
    calls = []
    for event in trace["events"]:
        if event["type"] != "tool_result":
            continue
        call = event["call"]["function"]
        name = call["name"]
        row = {"tool": name, "arguments": call["arguments"]}
        if name.startswith("math_") or "validate_syntax" in name or "evaluate" in name:
            row["result"] = event["result"]
        else:
            row["result_outer_isError"] = (
                event["result"].get("isError") if isinstance(event["result"], dict) else None
            )
            row["result_chars"] = len(json.dumps(event["result"], ensure_ascii=False))
        calls.append(row)
    packet = {
        "id": rid,
        "question": trace["question"],
        "answer": trace.get("answer"),
        "calls": calls,
    }
    dest = HERE / "blind-inputs" / (rid + ".json")
    if dest.exists():
        assert json.loads(dest.read_text()) == packet
    else:
        dest.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n")
print(
    json.dumps(
        {
            "ready": sorted(p.stem for p in (HERE / "blind-inputs").glob("*.json")),
            "evaluated": sum(x["status"] == "evaluated" for x in state["cells"].values()),
            "scheduled": 6,
        }
    )
)

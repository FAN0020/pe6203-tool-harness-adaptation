"""Freeze output and actual saved memory while hiding method and original scores."""

import hashlib
import json
import shutil
from pathlib import Path

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[2]
RAW = ROOT / "results/raw/discovery-contract-pilot-20261101"


def main():
    mapping = json.loads((FOLDER / "blind-map.json").read_text())
    state = json.loads((RAW / "experiment.json").read_text())
    dest = FOLDER / "blind-inputs"
    dest.mkdir(exist_ok=True)
    created = []
    for review_id, cell_id in mapping.items():
        if state["cells"].get(cell_id, {}).get("status") != "evaluated":
            continue
        cell = RAW / "cells" / cell_id
        trace = json.loads((cell / "run/raw_trace.json").read_text())
        calls = [{"arguments": e["call"]["function"]["arguments"],
                  "tool": e["call"]["function"]["name"], "result": e["result"]}
                 for e in trace["events"] if e["type"] == "tool_result"]
        artifacts = []
        memory = cell / "run/workspace/memory.jsonl"
        if memory.is_file():
            saved = FOLDER / "blind-artifacts" / review_id / "memory.jsonl"
            saved.parent.mkdir(parents=True, exist_ok=True)
            if saved.exists():
                assert saved.read_bytes() == memory.read_bytes()
            else:
                shutil.copyfile(memory, saved)
            artifacts.append({"path": "memory.jsonl",
                              "sha256": hashlib.sha256(memory.read_bytes()).hexdigest()})
        packet = {"review_id": review_id, "question": trace["question"],
                  "answer": trace.get("answer"), "calls": calls, "artifacts": artifacts}
        packet = json.loads(json.dumps(packet, ensure_ascii=False).replace(
            str(cell.resolve()), "RUN").replace(cell_id, "CELL"))
        path = dest / (review_id + ".json")
        if path.exists():
            assert json.loads(path.read_text()) == packet
        else:
            path.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n")
            created.append(review_id)
    ready = sorted(p.stem for p in dest.glob("*.json"))
    reviewed = {p.stem for p in (FOLDER / "blind-reviews").glob("*.json")}
    print(json.dumps({"new_packets": created, "ready": len(ready), "reviewed": len(reviewed),
                      "pending": [r for r in ready if r not in reviewed]}))


if __name__ == "__main__":
    main()

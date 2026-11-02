"""Freeze completed pilot output projections without showing methods or scores."""
import hashlib
import json
import shutil
from pathlib import Path

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[2]
RAW = ROOT / "results/raw/capability-consolidation-pilot-20261102"


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
        calls = [
            {"arguments": event["call"]["function"]["arguments"],
             "tool": event["call"]["function"]["name"], "result": event["result"]}
            for event in trace["events"] if event["type"] == "tool_result"
        ]
        artifacts = []
        for path in sorted((cell / "run/workspace").rglob("*")):
            if path.name not in ("tasks.json",) or not path.is_file():
                continue
            name = path.relative_to(cell / "run/workspace")
            copied = FOLDER / "blind-artifacts" / review_id / name
            copied.parent.mkdir(parents=True, exist_ok=True)
            if copied.exists():
                assert copied.read_bytes() == path.read_bytes()
            else:
                shutil.copyfile(path, copied)
            artifacts.append({"path": str(name), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        packet = {"review_id": review_id, "question": trace["question"],
                  "answer": trace.get("answer"), "calls": calls, "artifacts": artifacts}
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

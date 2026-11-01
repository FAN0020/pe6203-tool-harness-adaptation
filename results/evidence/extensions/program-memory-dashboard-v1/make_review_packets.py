"""Project only final answers and task-relevant native evidence; hide scores/method."""

import hashlib
import json
import random
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RAW = ROOT / "results/raw/extensions/program-memory-dashboard-v1/development"
BASE = ROOT / "experiments/extensions/program-memory-dashboard-v1"


def main():
    plan = json.loads((RAW / "plan.json").read_text())
    cells = list(plan["cells"])
    for cell in cells:
        result = json.loads((RAW / "cells" / cell["id"] / "run/result.json").read_text())
        assert result["status"] == "evaluated", "All cells must be terminal before review"
    random.Random(491861).shuffle(cells)
    out = HERE / "blind-review"
    out.mkdir(exist_ok=False)
    mapping = {}
    for index, cell in enumerate(cells, 1):
        label = f"R{index:02}"
        mapping[label] = cell["id"]
        folder = RAW / "cells" / cell["id"] / "run"
        result = json.loads((folder / "result.json").read_text())
        trace = json.loads((folder / "raw_trace.json").read_text())
        tools = []
        for event in trace["events"]:
            if event["type"] == "tool_result":
                # Category retrieval contents identify intervention, so omit those from
                # semantic review. Actual run-code / chart results are the deliverables.
                call = event["call"]["function"]
                if (
                    "run-code" in call["name"] or "run_code" in call["name"]
                ) or "generate_" in call["name"]:
                    tools.append({"call": call, "result": event["result"]})
        question = next(t["question"] for t in plan["tasks"] if t["idx"] == cell["task_id"])
        packet = {
            "label": label,
            "task_id": cell["task_id"],
            "question": question,
            "answer": trace.get("answer"),
            "tool_evidence": tools,
            "limitation": "Coordinator saw schedule earlier; randomized labels and scores hidden, but artifacts may suggest strategy. Not independent review.",
        }
        if cell["task_id"] >= 900000:
            workspace = folder / "workspace"
            dest = out / (label + "-workspace")
            shutil.copytree(workspace, dest, ignore=shutil.ignore_patterns(".home", "tmp.js"))
            manifest = json.loads((BASE / "datasets/development/manifest.json").read_text())
            packet["input_hashes_match"] = all(
                (workspace / name).is_file()
                and hashlib.sha256((workspace / name).read_bytes()).hexdigest() == wanted
                for name, wanted in manifest["input_files"].items()
            )
            packet["workspace_files"] = sorted(
                str(p.relative_to(dest)) for p in dest.rglob("*") if p.is_file()
            )
        (out / (label + "-packet.json")).write_text(
            json.dumps(packet, ensure_ascii=False, indent=2) + "\n"
        )
    (HERE / "review-map.json").write_text(json.dumps(mapping, indent=2) + "\n")
    print("Four relabeled packets written; mapping and scores withheld.")


if __name__ == "__main__":
    main()

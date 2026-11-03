"""Export only visible output from remaining registry/SP historical product reviews."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/evidence/unified-reaudit-20261102"
COHORTS = {
    "selective-search-v1-development-20261031",
    "selective-search-v1.1-development-20261031",
    "selective-search-v2-development-20261031",
    "selective-search-v2.1-development-20261031",
    "development",
}
STRATEGIES = {
    "selective_patch",
    "delta_notes",
    "linked_notes",
    "feedback_notes",
    "sufficiency_notes",
    "native_argument_routing",
}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    made = []
    for row in json.loads((OUT / "cells.json").read_text()):
        folder = ROOT / row["cohort"]
        if (
            folder.name not in COHORTS
            or row["strategy"] not in STRATEGIES
            or row.get("review_source")
            or row["status"] == "not_started"
        ):
            continue
        run = folder / "cells" / row["cell_id"] / "run"
        trace = run / "raw_trace.json"
        if not trace.exists():
            made.append({"cell": row["cell_id"], "cohort": folder.name, "missing": "raw_trace"})
            continue
        d = json.loads(trace.read_text())
        artifacts = []
        for f in sorted((run / "workspace").rglob("tasks.json")):
            artifacts.append({"path": str(f.relative_to(run / "workspace")), "sha256": sha(f)})
        packet = {
            "cell_id": row["cell_id"],
            "cohort": row["cohort"],
            "task_id": row["task_id"],
            "trace_sha256": sha(trace),
            "question": d["question"],
            "answer": d.get("answer"),
            "calls": [
                {
                    "tool": e["call"]["function"]["name"],
                    "arguments": e["call"]["function"]["arguments"],
                    "result": e["result"],
                }
                for e in d["events"]
                if e["type"] == "tool_result"
            ],
            "artifacts": artifacts,
        }
        dest = (
            OUT
            / "historical-products"
            / ("registry-" + folder.name if folder.name == "development" else folder.name)
        )
        (dest / "reviews").mkdir(parents=True, exist_ok=True)
        p = dest / (row["cell_id"] + ".json")
        if p.exists():
            assert json.loads(p.read_text()) == packet
        else:
            p.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n")
        made.append(
            {
                "cohort": folder.name,
                "cell": row["cell_id"],
                "task": row["task_id"],
                "answer_chars": len(packet["answer"] or ""),
                "calls": len(packet["calls"]),
            }
        )
    print(json.dumps(made, indent=2))


if __name__ == "__main__":
    main()

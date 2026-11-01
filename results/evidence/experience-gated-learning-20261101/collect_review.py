"""Collect current fixed training outputs without exposing official ratings."""
import hashlib
import json
import shutil
from pathlib import Path

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[2]
RAW = ROOT / "results/raw/extensions/experience-brief-training-v1"


def main():
    plan = json.loads((RAW / "plan.json").read_text())
    state = json.loads((RAW / "experiment.json").read_text())
    for i, cell in enumerate(plan["cells"], 1):
        ident = f"E{i:02}"
        dest = FOLDER / "review-inputs" / (ident + ".json")
        if dest.exists() or state["cells"].get(cell["id"], {}).get("status") != "evaluated":
            continue
        directory = RAW / "cells" / cell["id"] / "run"
        trace = json.loads((directory / "raw_trace.json").read_text())
        result = json.loads((directory / "result.json").read_text())
        artifacts = []
        for path in sorted((directory / "workspace").rglob("*")):
            if not path.is_file() or path.name not in ("slides.md", "theme.css"):
                continue
            relative = path.relative_to(directory / "workspace")
            target = FOLDER / "review-artifacts" / ident / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            artifacts.append({"path": str(relative), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        packet = {"episode": ident, "task_id": cell["task_id"], "execution_status": result["execution_status"],
                  "question": trace["question"], "answer": trace.get("answer"), "artifacts": artifacts,
                  "calls": [{"native_tool": result["model_tool_routes"].get(e["call"]["function"]["name"], {}).get("tool_name"),
                             "argument_characters": len(e["call"]["function"]["arguments"]),
                             "isError": bool(e["result"].get("isError"))}
                            for e in trace["events"] if e["type"] == "tool_result"]}
        encoded = json.dumps(packet, ensure_ascii=False, indent=2).replace(str(directory / "workspace"), "<workspace>")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(encoded + "\n")
    print(json.dumps({"review_packets": len(list((FOLDER / "review-inputs").glob("*.json"))), "ratings_exposed": False}))


if __name__ == "__main__":
    main()

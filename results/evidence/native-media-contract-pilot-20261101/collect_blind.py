"""Freeze completed pilot output projections without showing methods or scores."""
import hashlib
import json
import re
import shutil
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[2]
RAW = ROOT / "results/raw/native-media-contract-pilot-20261101"


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
            if path.suffix.lower() not in (".png", ".svg") or not path.is_file():
                continue
            name = path.relative_to(cell / "run/workspace")
            copied = FOLDER / "blind-artifacts" / review_id / name
            copied.parent.mkdir(parents=True, exist_ok=True)
            if copied.exists():
                assert copied.read_bytes() == path.read_bytes()
            else:
                shutil.copyfile(path, copied)
            artifacts.append({"path": str(name), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        # Fetch each distinct returned image URL once, preserving failed retrievals.
        urls = sorted(set(re.findall(
            r"https://(?:www\.)?plantuml\.com/plantuml/(?:png|svg)/[A-Za-z0-9_~\-]+",
            json.dumps(calls, ensure_ascii=False))))
        cache = FOLDER / "image-retrievals"
        cache.mkdir(exist_ok=True)
        for url in urls:
            key = hashlib.sha256(url.encode()).hexdigest()
            record_path = cache / (key + ".json")
            suffix = ".png" if "/png/" in url else ".svg"
            target = cache / (key + suffix)
            if not record_path.exists():
                record = {"url": url, "started_utc": datetime.now(UTC).isoformat()}
                try:
                    with urllib.request.urlopen(url, timeout=30) as response:
                        data = response.read()
                        record.update(status=response.status, mime=response.headers.get("Content-Type"))
                    target.write_bytes(data)
                    record["sha256"] = hashlib.sha256(data).hexdigest()
                except Exception as error:
                    record["error"] = {"type": type(error).__name__, "message": str(error)}
                record_path.write_text(json.dumps(record, indent=2) + "\n")
            record = json.loads(record_path.read_text())
            name = "retrieved/" + key + suffix
            if target.exists():
                copied = FOLDER / "blind-artifacts" / review_id / name
                copied.parent.mkdir(parents=True, exist_ok=True)
                if copied.exists():
                    assert copied.read_bytes() == target.read_bytes()
                else:
                    shutil.copyfile(target, copied)
                artifacts.append({"path": name, "sha256": record["sha256"], "source_url": url})
            if "error" in record:
                name = "retrieved/" + key + ".json"
                copied = FOLDER / "blind-artifacts" / review_id / name
                copied.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(record_path, copied)
                artifacts.append({"path": name, "sha256": hashlib.sha256(record_path.read_bytes()).hexdigest(), "source_url": url})
        packet = {"review_id": review_id, "question": trace["question"],
                  "answer": trace.get("answer"), "calls": calls, "artifacts": artifacts}
        packet = json.loads(json.dumps(packet, ensure_ascii=False).replace(str(cell.resolve()), "RUN").replace(cell_id, "CELL"))
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

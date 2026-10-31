"""Check evidence integrity and review completeness without revealing conditions."""
import argparse
import hashlib
import json
from pathlib import Path

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    protocol = ROOT / "experiments/weather-provenance-v1.json"
    spec = json.loads(protocol.read_text())
    expected = {c["task_id"]: {p["id"] for p in c["properties"]} for c in spec["quality_cases"]}
    reviews = sorted((FOLDER / "blind-reviews").glob("*.json"))
    inputs = sorted((FOLDER / "blind-inputs").glob("*.json"))
    if args.require_complete:
        assert len(reviews) == len(inputs) == 6
    assert len(reviews) <= len(inputs) <= 6
    hashes = {}
    for path in reviews:
        row = json.loads(path.read_text())
        packet_path = FOLDER / "blind-inputs" / path.name
        packet = json.loads(packet_path.read_text())
        assert set(packet) == {"review_id", "question", "answer", "calls", "artifacts"}
        assert row["review_id"] == packet["review_id"] == path.stem
        assert row["input_sha256"] == hashlib.sha256(packet_path.read_bytes()).hexdigest()
        assert set(row["properties"]) == expected[row["task_id"]]
        assert set(row["properties"].values()) <= {"pass", "fail", "unknown"}
        assert row["core_pass"] == all(v == "pass" for v in row["properties"].values())
        assert row["artifact_content_modified"] is False
        assert row["method_and_scores_revealed"] is False
        assert not {"strategy", "TF", "PE"} & set(row)
        for artifact in packet["artifacts"]:
            saved = FOLDER / "blind-artifacts" / path.stem / artifact["path"]
            assert hashlib.sha256(saved.read_bytes()).hexdigest() == artifact["sha256"]
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    print(json.dumps({"verified": True, "complete": len(reviews) == 6,
                      "input_count": len(inputs), "review_count": len(reviews),
                      "protocol_sha256": hashlib.sha256(protocol.read_bytes()).hexdigest(),
                      "review_sha256": hashes,
                      "limits": "Integrity/completeness only, not proof of semantic judgment or independent reviewer."}, indent=2))


if __name__ == "__main__":
    main()

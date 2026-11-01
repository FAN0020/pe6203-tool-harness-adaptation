"""Seal all opaque product reviews before reading the method map or scores."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent

def main():
    reviews = sorted((HERE / "blind-reviews").glob("R*.json"))
    packets = sorted((HERE / "blind-inputs").glob("R*.json"))
    assert len(reviews) == len(packets) == 10
    assert {p.stem for p in reviews} == {p.stem for p in packets}
    for path in reviews:
        review = json.loads(path.read_text())
        packet = HERE / "blind-inputs" / path.name
        assert review["input_sha256"] == hashlib.sha256(packet.read_bytes()).hexdigest()
        assert not review["official_scores_seen_before_review"]
        assert review["core_pass"] == all(v == "pass" for v in review["properties"].values())
    paths = reviews + packets
    paths += sorted(p for p in (HERE / "blind-artifacts").rglob("*") if p.is_file())
    paths += sorted(HERE.glob("R*-graph-audit.json"))
    paths += [HERE / n for n in ("review-sensitivity.json", "static-product-audit.json", "audit_products.py", "audit_static_products.py")]
    output = {
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "all_reviews_before_scores": True,
        "reviewer": "Same coordinator; opaque method IDs and scores withheld, not independent human review. Task behavior can reveal strategies.",
        "reviews": len(reviews),
        "files": {str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
    }
    target = HERE / "review-freeze.json"
    assert not target.exists()
    target.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"reviews": len(reviews), "frozen_files": len(paths)}))

if __name__ == "__main__":
    main()

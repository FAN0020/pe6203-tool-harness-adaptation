"""Deterministic controlled extension; no benchmark files or answers are consumed."""

import argparse
import hashlib
import json
import random
from datetime import date, timedelta
from pathlib import Path


def generate(destination, seed):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    fixture = destination / "input"
    logs = fixture / "logs"
    logs.mkdir(parents=True)
    rng = random.Random(seed)
    records = []
    counts = {}
    for day_index in range(7):
        day = str(date(2026, 2, 2) + timedelta(days=day_index))
        counts[day] = 0
        for event in range(rng.randint(28, 46)):
            level = rng.choice(["INFO", "INFO", "WARN", "ERROR", "ERROR", "DEBUG"])
            if day_index == 3 and level == "ERROR":
                level = "INFO"
            counts[day] += level == "ERROR"
            stamp = (
                f"{day}T{rng.randrange(24):02}:{rng.randrange(60):02}:{rng.randrange(60):02}.000Z"
            )
            message = rng.choice(
                [
                    "Device scan finished",
                    "Buffer deadline exceeded",
                    "Plugin state loaded",
                    "Audio engine restarted",
                    "Error counter inspection completed",
                ]
            )
            header = f"[{stamp}] [{level}] [audio-{rng.randrange(3)}] event={day_index}-{event} {message}"
            continuation = (
                "\n    Error: processing callback\n        at engine.render (audio.js:42:7)"
                if level == "ERROR" and event % 3 == 0
                else ""
            )
            records.append(header + continuation + "\n")
    rng.shuffle(records)
    # Rotation files deliberately contain multiple dates. Count event timestamps, not filenames.
    for part in range(4):
        (logs / f"studio-engine-part-{part + 1}.log").write_text("".join(records[part::4]))
    oracle = {
        "daily": [{"date": day, "errors": count} for day, count in sorted(counts.items())],
        "total_errors": sum(counts.values()),
        "days_covered": len(counts),
        "busiest_day": min(counts, key=lambda day: (-counts[day], day)),
    }
    # Private to assessment: never copied into an agent workspace or knowledge update.
    (destination / "oracle.json").write_text(json.dumps(oracle, indent=2) + "\n")
    manifest = {
        "seed": seed,
        "dataset_kind": "controlled_synthetic_extension",
        "input_files": {
            str(p.relative_to(fixture)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(logs.glob("*.log"))
        },
        "oracle_sha256": hashlib.sha256((destination / "oracle.json").read_bytes()).hexdigest(),
    }
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()
    print(json.dumps(generate(args.destination, args.seed)))

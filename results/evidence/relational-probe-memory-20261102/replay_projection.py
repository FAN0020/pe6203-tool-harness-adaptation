"""Apply the frozen incidental-clock recovery to identical whole observations."""

import hashlib
import json
from pathlib import Path

from pe6203.benchmark import write_json
from pe6203.relational_probe_memory import observation_note

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main():
    freeze = json.loads((HERE / "projection-recovery-freeze.json").read_text())
    for path, digest in freeze["files"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
    assert not (HERE / "recovered-projection.json").exists()
    inputs = json.loads((HERE / "updater-inputs.json").read_text())
    records = []
    for job in inputs["jobs"]:
        proposal = json.loads((HERE / f"{job['id']}-proposal.json").read_text())
        rows = json.loads((HERE / f"{job['id']}-observations.json").read_text())
        note = observation_note(job["data"], proposal, rows)
        original = json.loads((HERE / f"{job['id']}-candidate.json").read_text())["note"]
        import re

        expected = re.sub(
            r"\d{1,2}/\d{1,2}/\d{4},\s+\d{1,2}:\d{2}:\d{2}\s+[AP]M", "<timestamp>", original
        )
        assert note == expected, "Recovery must change only incidental native clock text"
        records.append(
            {
                "job": job["id"],
                "note": note,
                "old_sha256": hashlib.sha256(original.encode()).hexdigest(),
                "new_sha256": hashlib.sha256(note.encode()).hexdigest(),
            }
        )
    write_json(
        HERE / "recovered-projection.json",
        {
            "code_fix_commit": "b086c4d",
            "records": records,
            "all_original_inputs_preserved": True,
            "new_model_calls": 0,
            "new_native_calls": 0,
        },
    )
    print(json.dumps({"recovered_jobs": len(records), "semantic_changes": 0, "new_calls": 0}))


if __name__ == "__main__":
    main()

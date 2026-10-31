"""Verify the data-only rule proposal against the previous immutable archive."""

import hashlib
import json
import tarfile
from copy import deepcopy
from pathlib import Path

folder = Path(__file__).resolve().parent
proposal = json.loads((folder / "proposal.json").read_text())
audit = json.loads((folder / "preview-audit.json").read_text())
archive = folder.parent / "completion-quality-20261031/raw-trial.tar.gz"
assert hashlib.sha256(archive.read_bytes()).hexdigest() == audit["source_archive_sha256"]
assert proposal["authorization"]["approved"] is False
assert proposal["authorization"]["model_calls_permitted"] == 0
count = 0
k0 = 0
previews_path = folder / "knowledge-preview.tar.gz"
assert hashlib.sha256(previews_path.read_bytes()).hexdigest() == audit["preview_archive_sha256"]
with tarfile.open(archive) as tar, tarfile.open(previews_path) as previews:
    for row in audit["conditions"]:
        raw = tar.extractfile(row["source_member"]).read()
        assert hashlib.sha256(raw).hexdigest() == row["before_sha256"]
        before = json.loads(raw)
        content = previews.extractfile(row["preview_member"]).read()
        assert hashlib.sha256(content).hexdigest() == row["after_sha256"]
        expected = deepcopy(before)
        changed = []
        for tool in expected["tools"]:
            if proposal["candidate"]["before"] in tool["usage_rules"]:
                changed.append(tool["tool_id"])
            tool["usage_rules"] = [
                proposal["candidate"]["after"] if x == proposal["candidate"]["before"] else x
                for x in tool["usage_rules"]
            ]
        assert json.loads(content) == expected
        assert changed == row["changed_records"]
        count += len(changed)
        if row["stage"] == "early" or row["task_id"] == 235:
            assert before == expected
            k0 += 1
        else:
            name = f"completion-quality-v1-20261031/diffs/{row['task_id']}/{row['stage']}.json"
            diff = json.load(tar.extractfile(name))
            allowed = {x["tool_id"] for x in diff["changed"] + diff["added"]}
            assert set(changed) <= allowed
assert count == 29 and k0 == 5 and len(audit["conditions"]) == 9
print(
    json.dumps(
        {
            "preview_conditions": 9,
            "replacement_occurrences": count,
            "exact_K0_conditions": k0,
            "protected_fields_preserved": True,
            "new_model_calls": 0,
            "behavior_improvement": "UNVERIFIED",
        }
    )
)

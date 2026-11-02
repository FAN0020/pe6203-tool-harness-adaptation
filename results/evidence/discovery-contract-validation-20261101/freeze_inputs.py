"""Once-only pre-model snapshot and pilot-equivalence audit; no model calls."""
import copy
import hashlib
import json
import random
import subprocess
import tarfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[2]
RAW = ROOT / "results/raw/discovery-contract-validation-20261101"
PILOT = ROOT / "results/evidence/discovery-contract-pilot-20261101"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def save(name, data):
    path = FOLDER / name
    assert not path.exists(), path
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def main():
    assert not (RAW / "experiment.json").exists()
    assert not (FOLDER / "source-manifest.json").exists()
    spec = read(ROOT / "experiments/discovery-contract-validation-v1.json")
    pilot_spec = read(ROOT / "experiments/discovery-contract-v1.json")
    for key in ("mechanism", "quality_cases", "evaluation"):
        assert spec[key] == pilot_spec[key]
    config = read(ROOT / spec["model_config"])
    pilot_config = read(ROOT / pilot_spec["model_config"])
    normalized = copy.deepcopy(config)
    normalized["spend_guard"]["ledger"] = pilot_config["spend_guard"]["ledger"]
    assert normalized == pilot_config
    plan = read(RAW / "plan.json")
    assert len(plan["cells"]) == 36
    for seed in range(6):
        cells = [c for c in plan["cells"] if c["seed"] == seed]
        assert len(cells) == 6
        assert {(c["task_id"], c["version"], c["strategy"]) for c in cells} == {
            (t, s, a) for t, s in [(87, "middle"), (87, "late"), (235, "late")]
            for a in ("selective_patch", "discovery_contract")}
    for path, expected in plan["files"].items():
        assert digest(ROOT / path) == expected, path
    for path, expected in read(RAW / "knowledge-lock.json")["files"].items():
        assert digest(RAW / path) == expected, path
    checks = []
    for task, stage in [(87, "middle"), (87, "late"), (235, "late")]:
        condition = f"{task}-{stage}"
        base_path = RAW / f"adaptations/{condition}-selective_patch/knowledge.json"
        candidate_path = RAW / f"adaptations/{condition}-discovery_contract/knowledge.json"
        assert digest(base_path) == spec["control_knowledge_sha256"][condition]
        assert digest(candidate_path) == spec["candidate_knowledge_sha256"][condition]
        expected = read(base_path)
        count = 0
        if task == 87:
            for tool in expected["tools"]:
                annotation = spec["mechanism"]["annotations"][stage].get(tool["tool_id"])
                if annotation:
                    assert tool["description"] == annotation["before"]
                    tool["description"] = annotation["after"]
                    count += 1
            assert count == 2
        else:
            assert expected == read(RAW / "catalogs/235/early.json")
        assert expected == read(candidate_path)
        checks.append({"condition": condition, "description_fields_changed": count,
                       "all_other_fields_equal_sp": True, "exact_pilot_bytes": True,
                       "candidate_sha256": digest(candidate_path), "sp_sha256": digest(base_path)})
    save("knowledge-audit.json", {"checks": checks, "model_calls_at_freeze": 0,
                                 "plan_inputs_verified": len(plan["files"]),
                                 "quality_and_mechanism_equal_pilot": True,
                                 "config_only_difference": "spend ledger destination"})
    fixture = next((ROOT / config["fixture_dir"]).rglob("*.pdf"))
    url = config["task_context"].splitlines()[-1]
    with urllib.request.urlopen(url, timeout=10) as response:
        body = response.read()
        status = response.status
    assert status == 200 and hashlib.sha256(body).hexdigest() == digest(fixture)
    save("environment-check.json", {"checked_at": datetime.now(timezone.utc).isoformat(),
                                   "http_session_id": 27070, "url": url, "status": status,
                                   "fixture_sha256": digest(fixture), "bytes": len(body),
                                   "native_source_changed": False, "model_calls": 0})
    ids = [c["id"] for c in plan["cells"]]
    random.SystemRandom().shuffle(ids)
    save("blind-map.json", {f"V{i:02}": cell for i, cell in enumerate(ids, 1)})
    old_manifest = read(PILOT / "source-manifest.json")
    paths = set()
    for name, expected in old_manifest["files"].items():
        if "discovery-contract-pilot-20261101" in name:
            continue
        assert digest(ROOT / name) == expected, name
        paths.add(name)
    paths.update(plan["files"])
    paths.update(str(p.relative_to(ROOT)) for p in RAW.rglob("*") if p.is_file() and p.name != ".writer.lock")
    paths.update(str(p.relative_to(ROOT)) for p in FOLDER.iterdir() if p.suffix in (".json", ".py"))
    paths.update(["experiments/discovery-contract-validation-v1.json", "configs/discovery-contract-validation-v1.json"])
    hashes = {name: digest(ROOT / name) for name in sorted(paths)}
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    save("pre-execution-freeze.json", {"implementation_commit": "6615652b35a5f64817778ef96c96a92371ff4875",
                                      "registration_commit": commit, "stage": "all_inputs_locked_before_first_model_request",
                                      "files": hashes, "model_calls_at_freeze": 0})
    freeze_name = str((FOLDER / "pre-execution-freeze.json").relative_to(ROOT))
    hashes[freeze_name] = digest(ROOT / freeze_name)
    archive = FOLDER / "source-validation.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for name in sorted(hashes):
            tar.add(ROOT / name, arcname=name, recursive=False)
    save("source-manifest.json", {"commit": commit, "files": hashes, "archive_sha256": digest(archive)})
    print(json.dumps({"frozen": True, "knowledge_conditions": len(checks), "cells": len(ids),
                      "source_files": len(hashes), "archive_bytes": archive.stat().st_size,
                      "model_calls": 0}))


if __name__ == "__main__":
    main()

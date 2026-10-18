import hashlib
import json
import subprocess
from pathlib import Path


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def source(root):
    root = Path(root).resolve()
    lock = read_json(root / "configs/benchmark.lock.json")
    upstream = root / ".cache/mcpevol/upstream"
    sha = subprocess.check_output(
        ["git", "-C", str(upstream), "rev-parse", "HEAD"], text=True
    ).strip()
    if sha != lock["commit"]:
        raise ValueError(f"Upstream commit mismatch: {sha}")
    if subprocess.check_output(["git", "-C", str(upstream), "status", "--porcelain"], text=True):
        raise ValueError("Upstream checkout is modified; restore a clean pinned checkout")
    return lock, upstream


def load_task(upstream, task_id):
    data = Path(upstream) / "src/custom/data/test_cases"
    selected = {x["idx"] for x in read_json(data / "chosen_idx.json")["samples"]}
    if task_id not in selected:
        raise ValueError(f"Task {task_id} is not in the official selected 201 tasks")
    matches = [t for t in read_json(data / "test_cases.json") if t["idx"] == task_id]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one task {task_id}, found {len(matches)}")
    # Never expose the published reference answer, reference trace or scores to the agent.
    return {key: matches[0][key] for key in ("idx", "question", "servers")}

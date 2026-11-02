"""Exercise the public updater and model-tool projection with recorded catalogs only."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from pe6203.baselines import adapt
from pe6203.runner import prepare_tools

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[2]


def read(path):
    return json.loads(path.read_text())


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_directory", type=Path)
    output = parser.parse_args().output_directory.resolve()
    output.mkdir(parents=True, exist_ok=False)
    catalogs = read(ROOT / "tests/fixtures/native-argument-routing-catalogs.json")
    feedback = read(ROOT / "experiments/native-argument-routing-feedback-v1.json")["observations"]
    cases = [(f"magicui-{stage}", catalogs["early"], catalogs[stage])
             for stage in ("early", "middle", "late")]
    cases.append(("retention-235", read(FOLDER / "retention-early.json"),
                  read(FOLDER / "retention-late.json")))
    results = []
    for name, old, target in cases:
        row = {"name": name}
        for strategy in ("selective_patch", "native_argument_routing"):
            knowledge, changes, cost = adapt(old, target, strategy, {"feedback": feedback})
            tools, routes = prepare_tools(knowledge["tools"], strategy, "namespaced")
            row[strategy] = {"knowledge": knowledge, "changes": changes, "cost": cost,
                             "model_tools": tools, "model_routes": routes}
            save(output / f"{name}-{strategy}-knowledge.json", knowledge)
        results.append(row)
    save(output / "results.json", results)
    source_paths = [
        "src/pe6203/native_argument_routing.py", "src/pe6203/native_argument_routing_spec.py",
        "src/pe6203/patch_variants.py", "src/pe6203/baselines.py", "src/pe6203/selective.py",
        "src/pe6203/runner.py", "tests/test_native_argument_routing.py",
        "tests/fixtures/native-argument-routing-catalogs.json",
        "experiments/native-argument-routing-updater-v1.json",
        "experiments/native-argument-routing-feedback-v1.json",
        str(Path(__file__).resolve().relative_to(ROOT)),
    ]
    save(output / "execution.json", {
        "implementation_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "case_count": len(cases), "adaptations": len(cases) * 2,
        "agent_calls": 0, "judge_calls": 0, "native_calls": 0,
        "source": [{"path": p, "sha256": hashlib.sha256((ROOT / p).read_bytes()).hexdigest()}
                   for p in source_paths],
    })
    print(json.dumps({"cases": len(cases), "adaptations": len(cases) * 2,
                      "agent_calls": 0, "judge_calls": 0, "native_calls": 0}))


if __name__ == "__main__":
    main()
